"""Configuration loading for the search intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    canonical_origin: str
    gsc_site_url: str
    whatsapp_number: str
    artifact_lastmod: str
    similarity_threshold: float
    max_new_indexable_pages: int
    inspection_cache_days: int
    inspection_batch_size: int

    @property
    def seo_dir(self) -> Path:
        return self.root / "seo"


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "vercel.json").exists() and (candidate / "index.html").exists():
            return candidate
    raise FileNotFoundError("Could not locate the Band Nyx repository root")


def load_settings(root: Path | None = None) -> Settings:
    repo = find_root(root)
    raw = json.loads((repo / "seo" / "config.json").read_text(encoding="utf-8"))
    return Settings(
        root=repo,
        canonical_origin=raw["canonical_origin"].rstrip("/"),
        gsc_site_url=raw["gsc_site_url"],
        whatsapp_number=str(raw["whatsapp_number"]),
        artifact_lastmod=raw["artifact_lastmod"],
        similarity_threshold=float(raw.get("similarity_threshold", 0.82)),
        max_new_indexable_pages=int(raw.get("max_new_indexable_pages", 2)),
        inspection_cache_days=int(raw.get("inspection_cache_days", 7)),
        inspection_batch_size=min(int(raw.get("inspection_batch_size", 100)), 2000),
    )
