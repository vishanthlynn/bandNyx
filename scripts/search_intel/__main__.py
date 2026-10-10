"""Command-line interface for NYX Search Intelligence."""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sys

from .audit import format_report, run_audit, write_report
from .config import load_settings
from .generator import propose_pages, sync_artifacts
from .gsc import GSCConfigurationError, collect
from .registry import RegistryError, read_serp_imports, validate_registries
from .report import write_markdown_report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m scripts.search_intel")
    commands = root.add_subparsers(dest="command", required=True)

    audit = commands.add_parser("audit", help="Run the static technical SEO audit")
    audit.add_argument("--json-output", type=Path)
    audit.add_argument("--no-fail", action="store_true")

    commands.add_parser("validate-data", help="Validate SEO registries and SERP imports")

    sync = commands.add_parser("sync", help="Synchronize sitemap, query map, and llms.txt")
    sync.add_argument("--write", action="store_true")

    commands.add_parser("propose-pages", help="Generate proposals from verified gig data")

    collect_parser = commands.add_parser("collect", help="Collect private Search Console data")
    collect_parser.add_argument("--raw-output", type=Path, default=Path("seo-private/gsc-raw.json"))
    collect_parser.add_argument("--cache", type=Path, default=Path("seo-private/inspection-cache.json"))
    collect_parser.add_argument("--sitemap-state", type=Path, default=Path("seo-private/sitemap-state.json"))

    report = commands.add_parser("report", help="Create a human-readable aggregate report")
    report.add_argument("--output", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = load_settings()
    if args.command == "audit":
        result = run_audit(settings, base_ref=os.environ.get("SEO_BASE_REF") or None)
        print(format_report(result))
        if args.json_output:
            write_report(result, args.json_output)
        return 0 if args.no_fail or not result.errors else 1
    if args.command == "validate-data":
        errors = validate_registries(settings)
        try:
            rows = read_serp_imports(settings)
        except RegistryError as exc:
            errors.append(str(exc))
            rows = []
        if errors:
            print("\n".join(f"ERROR {error}" for error in errors))
            return 1
        print(f"Registries valid; {len(rows)} permitted SERP observations loaded")
        return 0
    if args.command == "sync":
        changed = sync_artifacts(settings, write=args.write)
        if changed:
            verb = "Updated" if args.write else "Out of date"
            print(f"{verb}: {', '.join(changed)}")
            return 0 if args.write else 1
        print("Generated SEO artifacts are current")
        return 0
    if args.command == "propose-pages":
        written, blocked = propose_pages(settings)
        for path in written:
            print(f"PROPOSED {path}")
        for reason in blocked:
            print(f"BLOCKED {reason}")
        return 0
    if args.command == "collect":
        try:
            summary = collect(
                settings,
                settings.root / args.raw_output,
                settings.seo_dir / "reports" / "summary.json",
                settings.root / args.cache,
                settings.root / args.sitemap_state,
            )
        except GSCConfigurationError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 2
        print(f"Collected Search Console data through {summary['period']['end']}")
        return 0
    if args.command == "report":
        output = args.output or settings.seo_dir / "reports" / f"{date.today().isoformat()}.md"
        write_markdown_report(settings, settings.root / output if not output.is_absolute() else output)
        print(f"Wrote {output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
