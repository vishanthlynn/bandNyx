#!/usr/bin/env python3
"""Compatibility wrapper for the safe, evidence-gated proposal generator.

This script intentionally never writes public pages into the site root. Add a
verified gig to seo/gigs.json, run this command, review seo/proposals/, and
publish a proposal manually only after its evidence has been checked.
"""

from search_intel.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main(["propose-pages"]))
