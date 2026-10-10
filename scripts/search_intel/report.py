"""Human-readable intelligence reports."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

from .config import Settings
from .registry import competitor_summary, read_json, read_serp_imports, validated_gigs


def render_report(settings: Settings) -> str:
    summary = read_json(settings.seo_dir / "reports" / "summary.json")
    wa_codes = read_json(settings.seo_dir / "wa-codes.json")["codes"]
    serp_rows = read_serp_imports(settings)
    competitors = competitor_summary(serp_rows, urlparse(settings.canonical_origin).netloc)
    valid_gigs, blocked_gigs = validated_gigs(settings)
    lines = [
        f"# NYX Search Intelligence — {date.today().isoformat()}",
        "",
        f"Site: {settings.gsc_site_url}",
        "",
        "## Search Console",
        "",
    ]
    if summary.get("status") != "collected":
        lines.append("Search Console collection is waiting for service-account credentials.")
    else:
        totals = summary["totals"]
        lines.extend(
            [
                f"- Clicks: {totals['clicks']:.0f}",
                f"- Impressions: {totals['impressions']:.0f}",
                f"- CTR: {totals['ctr']:.2%}",
                f"- Period: {summary['period']['start']} to {summary['period']['end']}",
                f"- Note: {totals['note']}",
                "",
                "### Pages with impressions but low CTR",
                "",
            ]
        )
        for row in summary.get("page_opportunities", []):
            lines.append(
                f"- {row['page']}: {row['impressions']:.0f} impressions, "
                f"{row['ctr']:.2%} CTR, position {row['position']:.1f}"
            )
    lines.extend(
        [
            "",
            "## Competitor observations",
            "",
            f"- Imported observations: {competitors['observations']}",
            f"- Queries observed: {competitors['queries']}",
            f"- NYX appearances: {competitors['own_results']}",
        ]
    )
    for row in competitors["competitor_domains"]:
        lines.append(f"- {row['domain']}: {row['appearances']} appearances")
    lines.extend(["", "## Performance-page readiness", ""])
    lines.append(f"- Eligible verified gigs: {len(valid_gigs)}")
    for reason in blocked_gigs:
        lines.append(f"- Blocked: {reason}")
    lines.extend(
        [
            "",
            "## Authority outreach queue",
            "",
            "For each verified gig, ask the real venue or organizer to publish a performer credit "
            "linking to the canonical Band Nyx website. No automated link placement is used.",
        ]
    )
    for gig in valid_gigs:
        lines.append(f"- {gig['venue']} — {gig['name']} ({gig['date']})")
    lines.extend(
        [
            "",
            "## WhatsApp attribution",
            "",
            "Reference codes are included in prefilled enquiries. Automatic click counts remain "
            "disabled until an approved analytics destination is configured.",
        ]
    )
    for row in wa_codes:
        lines.append(f"- {row['code']}: {row['route']} ({row['placement']})")
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(settings: Settings, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(settings), encoding="utf-8")
