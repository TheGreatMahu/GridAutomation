"""
main.py
~~~~~~~
Full pipeline orchestrator:
    scrape → clean → upsert to Supabase

Usage
-----
    python main.py                  # scrape latest 5 pages (~125 rows)
    python main.py --pages 20       # scrape more pages
    python main.py --pages all      # scrape ALL pages (slow – use once for backfill)
"""

import argparse
import sys

from scraper  import scrape
from cleaner  import clean
from uploader import upload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PGCB Hourly Generation → Supabase pipeline"
    )
    parser.add_argument(
        "--pages",
        default="5",
        help=(
            "Number of pages to scrape (default: 5). "
            "Pass 'all' or a large number for a full backfill."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between page requests (default: 1.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    max_pages = 9_999 if args.pages.lower() == "all" else int(args.pages)

    print("=" * 60)
    print("  PGCB Grid Automation  –  Hourly Generation Pipeline")
    print("=" * 60)

    # ── Step 1: Scrape ────────────────────────────────────────────
    print("\n[STEP 1] Scraping …")
    raw_df = scrape(max_pages=max_pages, delay=args.delay)

    if raw_df.empty:
        print("[main] No data scraped. Exiting.")
        sys.exit(1)

    # ── Step 2: Clean ─────────────────────────────────────────────
    print("\n[STEP 2] Cleaning …")
    clean_df = clean(raw_df)

    if clean_df.empty:
        print("[main] No valid rows after cleaning. Exiting.")
        sys.exit(1)

    # ── Step 3: Upsert ────────────────────────────────────────────
    print("\n[STEP 3] Uploading to Supabase …")
    upload(clean_df)

    print("\n[main] Pipeline complete ✓")


if __name__ == "__main__":
    main()

