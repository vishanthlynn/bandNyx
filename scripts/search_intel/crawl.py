"""Static HTML crawler used by audits and artifact generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlparse

from .config import Settings


@dataclass
class Page:
    path: Path
    route: str
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots: str = ""
    headings: list[tuple[str, str]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    jsonld: list[object] = field(default_factory=list)
    visible_text: str = ""

    @property
    def indexable(self) -> bool:
        return "noindex" not in self.robots.lower()


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.headings: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.jsonld_blocks: list[str] = []
        self.text: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs_raw: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): value or "" for key, value in attrs_raw}
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._hidden_depth += 1
        if tag == "title":
            self._capture, self._buffer = "title", []
        elif tag in {"h1", "h2", "h3"}:
            self._capture, self._buffer = tag, []
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._capture, self._buffer = "jsonld", []
        elif tag == "meta":
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            if key == "description":
                self.description = attrs.get("content", "").strip()
            elif key == "robots":
                self.robots = attrs.get("content", "").strip()
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"].strip())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture == tag or (tag == "script" and self._capture == "jsonld"):
            value = " ".join(" ".join(self._buffer).split())
            if self._capture == "title":
                self.title = value
            elif self._capture == "jsonld":
                self.jsonld_blocks.append(value)
            else:
                self.headings.append((self._capture or "", value))
            self._capture, self._buffer = None, []
        if tag in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)
        if not self._hidden_depth and data.strip():
            self.text.append(data.strip())


def route_for(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "index.html":
        return "/"
    return "/" + relative.removesuffix(".html")


def parse_page(path: Path, root: Path) -> Page:
    parser = _PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    structured: list[object] = []
    for block in parser.jsonld_blocks:
        try:
            structured.append(json.loads(block))
        except json.JSONDecodeError:
            structured.append({"_invalid_jsonld": block})
    return Page(
        path=path,
        route=route_for(path, root),
        title=parser.title,
        description=parser.description,
        canonical=parser.canonical,
        robots=parser.robots,
        headings=parser.headings,
        links=parser.links,
        jsonld=structured,
        visible_text=" ".join(" ".join(parser.text).split()),
    )


def crawl(settings: Settings) -> dict[str, Page]:
    pages: dict[str, Page] = {}
    for path in sorted(settings.root.rglob("*.html")):
        relative = path.relative_to(settings.root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if relative.parts[:2] == ("seo", "proposals"):
            continue
        if path.name.startswith("google") and path.name.endswith(".html"):
            continue
        page = parse_page(path, settings.root)
        pages[page.route] = page
    return pages


def load_redirects(settings: Settings) -> dict[str, str]:
    raw = json.loads((settings.root / "vercel.json").read_text(encoding="utf-8"))
    redirects: dict[str, str] = {}
    for item in raw.get("redirects", []):
        source = normalize_route(item["source"])
        destination = normalize_route(item["destination"])
        redirects[source] = destination
    return redirects


def resolve_redirect(route: str, redirects: dict[str, str]) -> tuple[str, list[str]]:
    current = normalize_route(route)
    chain: list[str] = []
    while current in redirects:
        if current in chain:
            chain.append(current)
            break
        chain.append(current)
        current = redirects[current]
    return current, chain


def normalize_route(value: str) -> str:
    parsed = urlparse(value)
    route = unquote(parsed.path or "/")
    if route.endswith(".html"):
        route = route[:-5]
    if route == "/index":
        route = "/"
    if route != "/":
        route = route.rstrip("/")
    return route or "/"


def internal_route(href: str, page: Page, settings: Settings) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(settings.canonical_origin + page.route, href)
    parsed = urlparse(absolute)
    if parsed.netloc != urlparse(settings.canonical_origin).netloc:
        return None
    return normalize_route(parsed.path)


def normalized_tokens(text: str) -> set[str]:
    boilerplate = {
        "band", "nyx", "home", "booking", "book", "members", "music", "live",
        "phone", "instagram", "andhra", "pradesh", "official", "page",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in boilerplate
    }


def jaccard_similarity(left: str, right: str) -> float:
    a, b = normalized_tokens(left), normalized_tokens(right)
    return len(a & b) / len(a | b) if a or b else 1.0
