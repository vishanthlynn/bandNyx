"""Safe artifact synchronization and evidence-gated page proposals."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from urllib.parse import quote

from .config import Settings
from .crawl import crawl, load_redirects
from .registry import read_json, validated_gigs


def _priority(route: str) -> str:
    if route == "/":
        return "1.0"
    if route in {"/band-nyx-vijayawada", "/booking"}:
        return "0.9"
    return "0.6"


def render_sitemap(settings: Settings) -> str:
    pages = crawl(settings)
    redirects = load_redirects(settings)
    routes = sorted(
        (route for route, page in pages.items() if page.indexable and route not in redirects),
        key=lambda route: (route != "/", route),
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for route in routes:
        url = settings.canonical_origin + ("/" if route == "/" else route)
        lines.append(
            f"  <url><loc>{url}</loc><lastmod>{settings.artifact_lastmod}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>{_priority(route)}</priority></url>"
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_public_query_map(settings: Settings) -> str:
    source = read_json(settings.seo_dir / "query-map.json")
    rows = [
        {
            "query": row["query"],
            "url": settings.canonical_origin + ("/" if row["route"] == "/" else row["route"]),
        }
        for row in source["queries"]
    ]
    payload = {
        "canonical_site": settings.canonical_origin,
        "generated_from": "seo/query-map.json",
        "queries": rows,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_llms(settings: Settings) -> str:
    claims = read_json(settings.seo_dir / "claims.json")["claims"]
    query_map = read_json(settings.seo_dir / "query-map.json")["queries"]
    pages = crawl(settings)
    redirects = load_redirects(settings)
    routes = sorted(
        (route for route, page in pages.items() if page.indexable and route not in redirects),
        key=lambda route: (route != "/", route),
    )
    lines = [
        "# Band Nyx — canonical entity information",
        "",
        f"Canonical website: {settings.canonical_origin}/",
        "This file is generated from verified repository data. Do not infer claims beyond these sources.",
        "",
        "## Verified claims",
        "",
    ]
    for claim in claims:
        if claim.get("status") == "verified":
            lines.append(f"- {claim['text']}")
            lines.extend(f"  Source: {url}" for url in claim.get("sources", []))
    lines.extend(["", "## Canonical public pages", ""])
    for route in routes:
        page = pages[route]
        url = settings.canonical_origin + ("/" if route == "/" else route)
        lines.append(f"- {page.title}: {url}")
    lines.extend(["", "## Search intent ownership", ""])
    for row in query_map:
        url = settings.canonical_origin + ("/" if row["route"] == "/" else row["route"])
        lines.append(f"- {row['query']} → {url}")
    lines.extend(
        [
            "",
            "## Booking",
            "",
            "- Phone: +91 79950 22614",
            "- Instagram: https://www.instagram.com/band.nyx/",
            f"- Booking page: {settings.canonical_origin}/booking",
            "",
        ]
    )
    return "\n".join(lines)


def sync_artifacts(settings: Settings, write: bool) -> list[str]:
    expected = {
        settings.root / "sitemap.xml": render_sitemap(settings),
        settings.root / "seo-query-map.json": render_public_query_map(settings),
        settings.root / "llms.txt": render_llms(settings),
    }
    changed: list[str] = []
    for path, content in expected.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            changed.append(str(path.relative_to(settings.root)))
            if write:
                path.write_text(content, encoding="utf-8")
    return changed


def _event_page(settings: Settings, gig: dict) -> str:
    canonical = f"{settings.canonical_origin}/events/{gig['slug']}"
    payload = {
        "@context": "https://schema.org",
        "@type": "Event",
        "@id": canonical + "#event",
        "name": gig["name"],
        "url": canonical,
        "startDate": gig["date"],
        "eventStatus": "https://schema.org/EventCompleted",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "Place",
            "name": gig["venue"],
            "address": {
                "@type": "PostalAddress",
                "addressLocality": gig["city"],
                "addressRegion": gig.get("region", ""),
                "addressCountry": gig.get("country", "IN"),
            },
        },
        "performer": {"@id": f"{settings.canonical_origin}/#band-nyx"},
        "sameAs": gig["evidence_urls"],
    }
    evidence = "\n".join(
        f'        <li><a href="{escape(url, quote=True)}" rel="noopener noreferrer">{escape(url)}</a></li>'
        for url in gig["evidence_urls"]
    )
    return f"""<!DOCTYPE html>
<html lang="en-IN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="index,follow" />
  <meta name="description" content="{escape(gig['recap'], quote=True)}" />
  <title>{escape(gig['name'])} | Band Nyx</title>
  <link rel="canonical" href="{canonical}" />
  <link rel="stylesheet" href="/styles.css" />
  <script type="application/ld+json">{json.dumps(payload, ensure_ascii=False)}</script>
</head>
<body class="seo-crawl-page">
  <main class="seo-page-main">
    <article class="container page-content seo-prose">
      <p class="eyebrow">Verified Band Nyx performance</p>
      <h1>{escape(gig['name'])}</h1>
      <p><strong>Date:</strong> {escape(gig['date'])}</p>
      <p><strong>Venue:</strong> {escape(gig['venue'])}, {escape(gig['city'])}</p>
      <p>{escape(gig['recap'])}</p>
      <h2>Independent evidence</h2>
      <ul>
{evidence}
      </ul>
      <p><a href="/live">More live performances</a> · <a href="/booking">Book Band Nyx</a></p>
    </article>
  </main>
</body>
</html>
"""


def propose_pages(settings: Settings) -> tuple[list[str], list[str]]:
    valid, blocked = validated_gigs(settings)
    proposal_dir = settings.seo_dir / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for gig in valid[: settings.max_new_indexable_pages]:
        path = proposal_dir / f"{gig['slug']}.html"
        path.write_text(_event_page(settings, gig), encoding="utf-8")
        written.append(str(path.relative_to(settings.root)))
    return written, blocked


def whatsapp_url(number: str, message: str) -> str:
    return f"https://wa.me/{number}?text={quote(message)}"
