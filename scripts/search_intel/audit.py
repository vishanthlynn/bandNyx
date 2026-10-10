"""Technical SEO and doorway-content audit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import subprocess
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .config import Settings
from .crawl import (
    Page,
    crawl,
    internal_route,
    jaccard_similarity,
    load_redirects,
    normalize_route,
    resolve_redirect,
)
from .registry import validated_gigs


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    route: str
    message: str


@dataclass
class AuditResult:
    pages: int
    indexable_pages: int
    redirects: int
    sitemap_urls: int
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    def as_dict(self) -> dict[str, object]:
        return {
            "pages": self.pages,
            "indexable_pages": self.indexable_pages,
            "redirects": self.redirects,
            "sitemap_urls": self.sitemap_urls,
            "error_count": len(self.errors),
            "warning_count": len(self.issues) - len(self.errors),
            "issues": [asdict(issue) for issue in self.issues],
        }


def _issue(issues: list[Issue], severity: str, code: str, route: str, message: str) -> None:
    issues.append(Issue(severity, code, route, message))


def read_sitemap(settings: Settings) -> set[str]:
    root = ET.parse(settings.root / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    routes: set[str] = set()
    for node in root.findall("s:url/s:loc", namespace):
        if node.text:
            routes.add(normalize_route(node.text))
    return routes


def _walk_json(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _new_indexable_routes(
    settings: Settings, pages: dict[str, Page], redirects: dict[str, str], base_ref: str | None
) -> list[str]:
    if not base_ref:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base_ref}...HEAD", "--", "*.html"],
        cwd=settings.root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return []
    added: list[str] = []
    for line in result.stdout.splitlines():
        status, _, name = line.partition("\t")
        if status != "A":
            continue
        route = normalize_route("/" + name)
        if route in pages and pages[route].indexable and route not in redirects:
            added.append(route)
    return added


def run_audit(settings: Settings, base_ref: str | None = None) -> AuditResult:
    pages = crawl(settings)
    redirects = load_redirects(settings)
    sitemap = read_sitemap(settings)
    issues: list[Issue] = []
    active = {
        route: page
        for route, page in pages.items()
        if page.indexable and route not in redirects
    }
    verified_event_routes = {
        f"/events/{gig['slug']}" for gig in validated_gigs(settings)[0]
    }
    new_routes = _new_indexable_routes(settings, pages, redirects, base_ref)
    if len(new_routes) > settings.max_new_indexable_pages:
        _issue(
            issues,
            "error",
            "scaled-page-addition",
            "/",
            f"{len(new_routes)} new indexable pages exceed the limit of "
            f"{settings.max_new_indexable_pages}: {', '.join(new_routes)}",
        )

    for source in redirects:
        _, chain = resolve_redirect(source, redirects)
        if len(chain) > 1:
            _issue(issues, "error", "redirect-chain", source, " -> ".join((*chain, resolve_redirect(source, redirects)[0])))

    for route, page in active.items():
        expected = settings.canonical_origin + ("/" if route == "/" else route)
        if not page.title:
            _issue(issues, "error", "missing-title", route, "Page has no title")
        elif not 20 <= len(page.title) <= 65:
            _issue(issues, "warning", "title-length", route, f"Title is {len(page.title)} characters")
        if not page.description:
            _issue(issues, "error", "missing-description", route, "Page has no meta description")
        elif not 70 <= len(page.description) <= 165:
            _issue(issues, "warning", "description-length", route, f"Description is {len(page.description)} characters")
        if page.canonical.rstrip("/") != expected.rstrip("/"):
            _issue(issues, "error", "canonical-mismatch", route, f"Expected {expected}, found {page.canonical or 'none'}")
        h1s = [text for level, text in page.headings if level == "h1"]
        if len(h1s) != 1:
            _issue(issues, "error", "h1-count", route, f"Expected one H1, found {len(h1s)}")
        if route not in sitemap:
            _issue(issues, "error", "missing-from-sitemap", route, "Indexable canonical page is absent from sitemap")
        if any("_invalid_jsonld" in node for block in page.jsonld for node in _walk_json(block)):
            _issue(issues, "error", "invalid-jsonld", route, "JSON-LD cannot be parsed")
        if not any(
            href.startswith(("tel:", "https://wa.me/"))
            or internal_route(href, page, settings) == "/booking"
            for href in page.links
        ):
            _issue(issues, "error", "conversion-gap", route, "Page has no booking, phone, or WhatsApp path")
        if re.search(r"\bbest\b", f"{page.title} {' '.join(h1s)}", re.I):
            _issue(issues, "error", "unsupported-best-claim", route, "Indexable page makes an unsupported 'best' claim")
        for block in page.jsonld:
            for node in _walk_json(block):
                kinds = node.get("@type", [])
                kinds = [kinds] if isinstance(kinds, str) else kinds
                if "Event" in kinds:
                    start = str(node.get("startDate", ""))
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", start):
                        _issue(issues, "error", "event-date", route, "Event JSON-LD must use a verified calendar date")
                    if route not in verified_event_routes:
                        _issue(issues, "error", "event-evidence", route, "Event page has no verified gig record")

    for route in sorted(sitemap):
        if route in redirects:
            _issue(issues, "error", "redirect-in-sitemap", route, "Sitemap URL redirects")
        elif route not in pages:
            _issue(issues, "error", "missing-file", route, "Sitemap URL has no source HTML file")
        elif not pages[route].indexable:
            _issue(issues, "error", "noindex-in-sitemap", route, "Noindex page appears in sitemap")

    incoming = {route: 0 for route in active}
    for page in active.values():
        for href in page.links:
            target = internal_route(href, page, settings)
            if target is None:
                continue
            if target in redirects:
                effective, _ = resolve_redirect(target, redirects)
                _issue(issues, "error", "link-to-redirect", page.route, f"{href} should link directly to {effective}")
                target = effective
            if target in incoming:
                incoming[target] += 1
            elif target not in pages and not target.startswith("/assets/"):
                _issue(issues, "warning", "broken-internal-link", page.route, f"Internal target does not exist: {href}")
    for route, count in incoming.items():
        if route != "/" and count == 0:
            _issue(issues, "error", "orphan-page", route, "No indexable page links to this URL")

    comparable = sorted(active.items())
    for index, (left_route, left) in enumerate(comparable):
        for right_route, right in comparable[index + 1 :]:
            score = jaccard_similarity(left.visible_text, right.visible_text)
            if score >= settings.similarity_threshold:
                _issue(
                    issues,
                    "error",
                    "doorway-similarity",
                    left_route,
                    f"{score:.0%} token overlap with {right_route}",
                )

    issues.sort(key=lambda item: (item.severity != "error", item.code, item.route))
    return AuditResult(
        pages=len(pages),
        indexable_pages=len(active),
        redirects=len(redirects),
        sitemap_urls=len(sitemap),
        issues=issues,
    )


def write_report(result: AuditResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")


def format_report(result: AuditResult) -> str:
    lines = [
        f"Pages: {result.pages} | Indexable: {result.indexable_pages} | "
        f"Redirects: {result.redirects} | Sitemap: {result.sitemap_urls}",
        f"Errors: {len(result.errors)} | Warnings: {len(result.issues) - len(result.errors)}",
    ]
    for issue in result.issues:
        lines.append(f"{issue.severity.upper():7} {issue.code:24} {issue.route} — {issue.message}")
    return "\n".join(lines)
