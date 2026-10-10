"""Validation for claims, gigs, query ownership, WhatsApp codes, and SERP imports."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

from .config import Settings
from .crawl import crawl, load_redirects, normalize_route


class RegistryError(ValueError):
    """Raised when public SEO data fails an evidence or consistency rule."""


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validated_gigs(settings: Settings) -> tuple[list[dict], list[str]]:
    raw = read_json(settings.seo_dir / "gigs.json")
    valid: list[dict] = []
    blocked: list[str] = []
    for gig in raw.get("gigs", []):
        errors: list[str] = []
        if gig.get("status") != "verified":
            errors.append(f"status is {gig.get('status', 'missing')}")
        try:
            date.fromisoformat(gig.get("date") or "")
        except ValueError:
            errors.append("date is not an exact ISO calendar day")
        for field in ("slug", "name", "venue", "city", "event_type", "recap"):
            if not gig.get(field):
                errors.append(f"{field} is missing")
        evidence = gig.get("evidence_urls") or []
        if not evidence:
            errors.append("independent evidence URL is missing")
        for url in evidence:
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.netloc == urlparse(settings.canonical_origin).netloc:
                errors.append(f"evidence must be an independent HTTPS URL: {url}")
        if errors:
            blocked.append(f"{gig.get('slug', 'unnamed')}: " + "; ".join(errors))
        else:
            valid.append(gig)
    return valid, blocked


def validate_registries(settings: Settings) -> list[str]:
    errors: list[str] = []
    pages = crawl(settings)
    redirects = load_redirects(settings)

    claims = read_json(settings.seo_dir / "claims.json").get("claims", [])
    claim_ids = [claim.get("id") for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("claims.json contains duplicate claim IDs")
    for claim in claims:
        if claim.get("status") == "verified" and not claim.get("sources"):
            errors.append(f"verified claim {claim.get('id')} has no source")

    query_rows = read_json(settings.seo_dir / "query-map.json").get("queries", [])
    query_names = [str(row.get("query", "")).casefold() for row in query_rows]
    if len(query_names) != len(set(query_names)):
        errors.append("query-map.json assigns the same query more than once")
    for row in query_rows:
        route = normalize_route(row.get("route", ""))
        if route in redirects:
            errors.append(f"query {row.get('query')} points to redirect source {route}")
        elif route not in pages or not pages[route].indexable:
            errors.append(f"query {row.get('query')} points to a missing or noindex page {route}")

    wa = read_json(settings.seo_dir / "wa-codes.json")
    codes = [row.get("code") for row in wa.get("codes", [])]
    if len(codes) != len(set(codes)):
        errors.append("wa-codes.json contains duplicate codes")
    if str(wa.get("number")) != settings.whatsapp_number:
        errors.append("wa-codes.json number differs from config.json")
    for row in wa.get("codes", []):
        route = normalize_route(row.get("route", ""))
        if route in redirects or route not in pages or not pages[route].indexable:
            errors.append(f"WhatsApp code {row.get('code')} points to a non-canonical page")
        if row.get("code") not in row.get("message", ""):
            errors.append(f"WhatsApp message for {row.get('code')} does not contain its code")
        if route in pages:
            source = pages[route].path.read_text(encoding="utf-8")
            if f'data-ref="{row.get("code")}"' not in source:
                errors.append(f"WhatsApp code {row.get('code')} is not present on {route}")
            if f"wa.me/{settings.whatsapp_number}" not in source:
                errors.append(f"WhatsApp number is missing from {route}")

    return errors


SERP_COLUMNS = {
    "observed_on", "query", "locale", "device", "position",
    "result_url", "result_title", "observer", "source_note",
}


def read_serp_imports(settings: Settings) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((settings.seo_dir / "imports" / "serp").glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if set(reader.fieldnames or []) != SERP_COLUMNS:
                raise RegistryError(f"{path.name} has an invalid header")
            for row in reader:
                if not any(row.values()):
                    continue
                try:
                    date.fromisoformat(row["observed_on"])
                    position = int(row["position"])
                except (ValueError, TypeError) as exc:
                    raise RegistryError(f"{path.name} contains an invalid date or position") from exc
                if not 1 <= position <= 20:
                    raise RegistryError(f"{path.name} positions must be between 1 and 20")
                if not row["observer"].strip() or not row["source_note"].strip():
                    raise RegistryError(f"{path.name} requires observer and source_note")
                if urlparse(row["result_url"]).scheme not in {"http", "https"}:
                    raise RegistryError(f"{path.name} contains an invalid result URL")
                rows.append(row)
    counts = Counter((row["observed_on"], row["query"], row["locale"], row["device"]) for row in rows)
    if any(count > 20 for count in counts.values()):
        raise RegistryError("A SERP import contains more than 20 results for one query/day/device")
    return rows


def competitor_summary(rows: list[dict[str, str]], own_host: str) -> dict[str, object]:
    domains = Counter(urlparse(row["result_url"]).netloc for row in rows if urlparse(row["result_url"]).netloc != own_host)
    own_rows = [row for row in rows if urlparse(row["result_url"]).netloc == own_host]
    return {
        "observations": len(rows),
        "queries": len({row["query"] for row in rows}),
        "own_results": len(own_rows),
        "competitor_domains": [{"domain": domain, "appearances": count} for domain, count in domains.most_common()],
    }
