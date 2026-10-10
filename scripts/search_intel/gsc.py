"""Google Search Console collection with private raw output."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .config import Settings
from .crawl import crawl, load_redirects
from .registry import read_json

SCOPES = ["https://www.googleapis.com/auth/webmasters"]


class GSCConfigurationError(RuntimeError):
    """Raised when Search Console credentials or dependencies are unavailable."""


def _google_service(settings: Settings):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GSCConfigurationError(
            "Install requirements-seo.txt before collecting Search Console data"
        ) from exc
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise GSCConfigurationError("GSC_SERVICE_ACCOUNT_JSON is not set")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GSCConfigurationError("GSC_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)


def _search_rows(service, site_url: str, start: str, end: str, dimensions: list[str]) -> list[dict]:
    rows: list[dict] = []
    start_row = 0
    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": dimensions,
            "dataState": "final",
            "rowLimit": 25000,
            "startRow": start_row,
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        batch = response.get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000:
            break
        start_row += len(batch)
    return rows


def _inspection_urls(settings: Settings) -> list[str]:
    pages = crawl(settings)
    redirects = load_redirects(settings)
    return [
        settings.canonical_origin + ("/" if route == "/" else route)
        for route, page in sorted(pages.items())
        if page.indexable and route not in redirects
    ]


def _load_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _inspect(service, settings: Settings, cache_path: Path) -> dict[str, dict]:
    cache = _load_cache(cache_path)
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.inspection_cache_days)
    inspected = 0
    for url in _inspection_urls(settings):
        previous = cache.get(url, {})
        try:
            previous_at = datetime.fromisoformat(previous.get("inspected_at", ""))
        except ValueError:
            previous_at = datetime.min.replace(tzinfo=timezone.utc)
        if previous_at >= cutoff:
            continue
        if inspected >= settings.inspection_batch_size:
            break
        response = (
            service.urlInspection()
            .index()
            .inspect(body={"inspectionUrl": url, "siteUrl": settings.gsc_site_url})
            .execute()
        )
        cache[url] = {
            "inspected_at": datetime.now(timezone.utc).isoformat(),
            "result": response.get("inspectionResult", {}),
        }
        inspected += 1
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    return cache


def _submit_sitemap_if_changed(service, settings: Settings, state_path: Path) -> dict[str, object]:
    sitemap_path = settings.root / "sitemap.xml"
    digest = hashlib.sha256(sitemap_path.read_bytes()).hexdigest()
    previous = _load_cache(state_path)
    changed = previous.get("sha256") != digest
    sitemap_url = f"{settings.canonical_origin}/sitemap.xml"
    if changed:
        service.sitemaps().submit(siteUrl=settings.gsc_site_url, feedpath=sitemap_url).execute()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "sha256": digest,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "url": sitemap_url,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return {"url": sitemap_url, "submitted": changed, "sha256": digest}


def build_summary(settings: Settings, raw: dict) -> dict:
    page_rows = raw["page_rows"]
    query_page_rows = raw["query_page_rows"]
    page_clicks = sum(float(row.get("clicks", 0)) for row in page_rows)
    page_impressions = sum(float(row.get("impressions", 0)) for row in page_rows)
    mapped = read_json(settings.seo_dir / "query-map.json")["queries"]
    seen_queries = {
        str(row.get("keys", ["", ""])[1]).casefold()
        for row in query_page_rows
        if len(row.get("keys", [])) > 1
    }
    opportunities = []
    for row in page_rows:
        impressions = float(row.get("impressions", 0))
        ctr = float(row.get("ctr", 0))
        if impressions >= 20 and ctr < 0.03:
            opportunities.append(
                {
                    "page": row.get("keys", [""])[0],
                    "impressions": impressions,
                    "clicks": float(row.get("clicks", 0)),
                    "ctr": ctr,
                    "position": float(row.get("position", 0)),
                }
            )
    opportunities.sort(key=lambda row: row["impressions"], reverse=True)
    verdicts: dict[str, int] = {}
    for item in raw["inspection"].values():
        verdict = (
            item.get("result", {})
            .get("indexStatusResult", {})
            .get("verdict", "UNKNOWN")
        )
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return {
        "status": "collected",
        "site": settings.gsc_site_url,
        "last_collected": raw["collected_at"],
        "period": raw["period"],
        "privacy": "Raw query rows are retained only in private workflow artifacts.",
        "totals": {
            "clicks": page_clicks,
            "impressions": page_impressions,
            "ctr": page_clicks / page_impressions if page_impressions else 0,
            "note": "Page totals are authoritative; query totals can omit anonymized queries.",
        },
        "top_pages": sorted(
            (
                {
                    "page": row.get("keys", [""])[0],
                    "clicks": float(row.get("clicks", 0)),
                    "impressions": float(row.get("impressions", 0)),
                    "ctr": float(row.get("ctr", 0)),
                    "position": float(row.get("position", 0)),
                }
                for row in page_rows
            ),
            key=lambda row: row["clicks"],
            reverse=True,
        )[:10],
        "page_opportunities": opportunities[:10],
        "mapped_queries_without_rows": [
            row["query"] for row in mapped if row["query"].casefold() not in seen_queries
        ],
        "sitemap": {
            "submission": raw.get("sitemap_submission", {}),
            "status": raw["sitemaps"],
        },
        "inspection": verdicts,
        "whatsapp_attribution": {
            "status": "reference-codes-active",
            "automatic_click_counts": False,
            "reason": "Awaiting an approved GA4 measurement ID or Vercel event store.",
        },
    }


def collect(
    settings: Settings,
    raw_path: Path,
    summary_path: Path,
    cache_path: Path,
    sitemap_state_path: Path,
) -> dict:
    service = _google_service(settings)
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=27)
    page_rows = _search_rows(service, settings.gsc_site_url, start.isoformat(), end.isoformat(), ["page"])
    query_page_rows = _search_rows(
        service, settings.gsc_site_url, start.isoformat(), end.isoformat(), ["page", "query"]
    )
    sitemap_submission = _submit_sitemap_if_changed(service, settings, sitemap_state_path)
    sitemaps = service.sitemaps().list(siteUrl=settings.gsc_site_url).execute()
    inspection = _inspect(service, settings, cache_path)
    raw = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": start.isoformat(), "end": end.isoformat(), "data_state": "final"},
        "page_rows": page_rows,
        "query_page_rows": query_page_rows,
        "sitemaps": sitemaps,
        "sitemap_submission": sitemap_submission,
        "inspection": inspection,
    }
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    summary = build_summary(settings, raw)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
