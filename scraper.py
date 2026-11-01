"""
scraper.py
~~~~~~~~~~
Scrapes hourly generation data from PGCB ERP portal and returns a
raw pandas DataFrame (or saves to CSV for standalone use).

URL: https://erp.powergrid.gov.bd/w/generations/view_generations
"""

import time
import warnings
import pandas as pd
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup

# The PGCB government portal uses a self-signed / unverified SSL cert.
# We disable SSL verification only for this specific host and suppress the warning.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

BASE_URL = "https://erp.powergrid.gov.bd/w/generations/view_generations"

BANGLA_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Expected columns from the site (fallback if <th> tags are absent)
FALLBACK_COLS = [
    "Date", "Time", "Generation(MW)", "Gas", "Liquid Fuel",
    "Coal", "Hydro", "Solar", "Wind", "India", "Nepal", "Adani", "Remarks",
]


def _parse_table(soup: BeautifulSoup) -> list[list[str]]:
    """Extract all data rows from the first <table> on the page."""
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")
    data = []
    for row in rows[1:]:  # skip header row
        cols = [
            td.get_text(strip=True).translate(BANGLA_TO_ASCII)
            for td in row.find_all("td")
        ]
        if cols:
            data.append(cols)
    return data


def _get_column_names(soup: BeautifulSoup) -> list[str]:
    """Grab <th> text for column names, falling back to FALLBACK_COLS."""
    table = soup.find("table")
    if not table:
        return FALLBACK_COLS
    ths = [th.get_text(strip=True) for th in table.find_all("th")]
    return ths if ths else FALLBACK_COLS


def scrape(max_pages: int = 5, delay: float = 1.0) -> pd.DataFrame:
    """
    Scrape up to *max_pages* pages from the PGCB generations view.

    Parameters
    ----------
    max_pages : int
        Maximum number of pages to fetch (default: 5 ≈ ~125 rows).
        Set to a large number (e.g. 9999) to scrape everything.
    delay : float
        Seconds to wait between page requests (be polite to the server).

    Returns
    -------
    pd.DataFrame  with raw string columns (Date, Time, generation figures).
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    all_rows: list[list[str]] = []
    col_names: list[str] = []

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}?page={page}"
        print(f"[scraper] Fetching page {page}: {url}")

        try:
            resp = session.get(url, timeout=30, verify=False)
        except requests.RequestException as exc:
            print(f"[scraper] Request failed on page {page}: {exc}")
            break

        if resp.status_code != 200:
            print(f"[scraper] HTTP {resp.status_code} on page {page}. Stopping.")
            break

        soup = BeautifulSoup(resp.text, "lxml")

        if not col_names:
            col_names = _get_column_names(soup)

        rows = _parse_table(soup)
        if not rows:
            print(f"[scraper] No data rows on page {page}. Pagination ended.")
            break

        all_rows.extend(rows)
        time.sleep(delay)

    if not all_rows:
        print("[scraper] No data scraped.")
        return pd.DataFrame(columns=col_names or FALLBACK_COLS)

    # Align columns: trim or pad each row to match header length
    n_cols = len(col_names)
    aligned = [
        (row + [""] * n_cols)[:n_cols]
        for row in all_rows
    ]

    df = pd.DataFrame(aligned, columns=col_names, dtype=str)
    print(f"[scraper] Scraped {len(df)} raw rows across {page} page(s).")
    return df


# ── Standalone usage ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    out   = sys.argv[2] if len(sys.argv) > 2 else "pgcb_hourly_generation_full.csv"

    df = scrape(max_pages=pages)
    df.to_csv(out, index=False)
    print(f"[scraper] Saved raw data to {out}")

