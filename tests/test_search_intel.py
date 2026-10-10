from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from scripts.search_intel.audit import read_sitemap, run_audit
from scripts.search_intel.config import load_settings
from scripts.search_intel.crawl import (
    crawl,
    jaccard_similarity,
    load_redirects,
    resolve_redirect,
)
from scripts.search_intel.generator import propose_pages, sync_artifacts, whatsapp_url
from scripts.search_intel.gsc import _inspect, _search_rows, build_summary
from scripts.search_intel.registry import (
    read_serp_imports,
    validate_registries,
    validated_gigs,
)


class SearchIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = load_settings(Path(__file__).resolve().parents[1])

    def test_current_site_passes_strict_audit(self) -> None:
        result = run_audit(self.settings)
        self.assertEqual([], result.errors)

    def test_redirect_sources_are_not_in_sitemap(self) -> None:
        redirects = load_redirects(self.settings)
        sitemap = read_sitemap(self.settings)
        self.assertFalse(set(redirects) & sitemap)
        for source in redirects:
            destination, chain = resolve_redirect(source, redirects)
            self.assertNotEqual(source, destination)
            self.assertEqual(1, len(chain))

    def test_registries_are_consistent_with_public_pages(self) -> None:
        self.assertEqual([], validate_registries(self.settings))
        self.assertEqual([], read_serp_imports(self.settings))

    def test_unverified_gigs_cannot_generate_pages(self) -> None:
        valid, blocked = validated_gigs(self.settings)
        self.assertEqual([], valid)
        self.assertEqual(4, len(blocked))
        written, proposal_blocks = propose_pages(self.settings)
        self.assertEqual([], written)
        self.assertEqual(blocked, proposal_blocks)

    def test_generated_artifacts_are_current(self) -> None:
        self.assertEqual([], sync_artifacts(self.settings, write=False))

    def test_whatsapp_references_are_unique_and_encoded(self) -> None:
        data = json.loads((self.settings.seo_dir / "wa-codes.json").read_text())
        codes = [row["code"] for row in data["codes"]]
        self.assertEqual(len(codes), len(set(codes)))
        for row in data["codes"]:
            url = whatsapp_url(data["number"], row["message"])
            self.assertIn("wa.me/917995022614", url)
            self.assertIn(row["code"], row["message"])

    def test_similarity_gate_detects_city_swaps(self) -> None:
        left = "Live music for weddings and college festivals in Vijayawada with six musicians"
        right = "Live music for weddings and college festivals in Hyderabad with six musicians"
        unique = "A dated performance recap with venue evidence, setlist details, photos and organizer credit"
        self.assertGreater(jaccard_similarity(left, right), 0.7)
        self.assertLess(jaccard_similarity(left, unique), 0.3)

    def test_event_archives_are_not_public_event_schema(self) -> None:
        pages = crawl(self.settings)
        event_pages = [page for route, page in pages.items() if route.startswith("/events/")]
        self.assertTrue(event_pages)
        for page in event_pages:
            self.assertFalse(page.indexable)
            self.assertNotIn('"@type": "Event"', page.path.read_text(encoding="utf-8"))

    def test_gsc_summary_uses_page_totals(self) -> None:
        raw = {
            "collected_at": "2026-10-11T00:00:00+00:00",
            "period": {"start": "2026-09-11", "end": "2026-10-08", "data_state": "final"},
            "page_rows": [
                {"keys": ["https://band-nyx.vercel.app/"], "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 3}
            ],
            "query_page_rows": [
                {"keys": ["https://band-nyx.vercel.app/", "band nyx"], "clicks": 8, "impressions": 80, "ctr": 0.1, "position": 2}
            ],
            "sitemaps": {"sitemap": []},
            "inspection": {
                "https://band-nyx.vercel.app/": {
                    "result": {"indexStatusResult": {"verdict": "PASS"}}
                }
            },
        }
        summary = build_summary(self.settings, raw)
        self.assertEqual(10, summary["totals"]["clicks"])
        self.assertIn("query totals", summary["totals"]["note"].lower())
        self.assertEqual({"PASS": 1}, summary["inspection"])

    def test_gsc_search_rows_paginates_with_final_data(self) -> None:
        class Request:
            def __init__(self, payload):
                self.payload = payload

            def execute(self):
                return self.payload

        class Analytics:
            def __init__(self):
                self.calls = []

            def query(self, siteUrl, body):
                self.calls.append((siteUrl, body))
                size = 25000 if body["startRow"] == 0 else 1
                return Request({"rows": [{"keys": ["/"]}] * size})

        class Service:
            def __init__(self):
                self.analytics = Analytics()

            def searchanalytics(self):
                return self.analytics

        service = Service()
        rows = _search_rows(
            service, self.settings.gsc_site_url, "2026-09-01", "2026-09-30", ["page"]
        )
        self.assertEqual(25001, len(rows))
        self.assertEqual("final", service.analytics.calls[0][1]["dataState"])
        self.assertEqual(25000, service.analytics.calls[0][1]["rowLimit"])
        self.assertEqual(25000, service.analytics.calls[1][1]["startRow"])

    def test_inspection_plan_respects_batch_limit_and_cache(self) -> None:
        class Request:
            def execute(self):
                return {"inspectionResult": {"indexStatusResult": {"verdict": "PASS"}}}

        class Index:
            def __init__(self, calls):
                self.calls = calls

            def inspect(self, body):
                self.calls.append(body)
                return Request()

        class URLInspection:
            def __init__(self, calls):
                self.calls = calls

            def index(self):
                return Index(self.calls)

        class Service:
            def __init__(self):
                self.calls = []

            def urlInspection(self):
                return URLInspection(self.calls)

        service = Service()
        settings = replace(self.settings, inspection_batch_size=2)
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "inspection.json"
            first = _inspect(service, settings, cache_path)
            self.assertEqual(2, len(service.calls))
            self.assertEqual(2, len(first))
            _inspect(service, settings, cache_path)
            self.assertEqual(4, len(service.calls))


if __name__ == "__main__":
    unittest.main()
