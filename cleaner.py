"""
cleaner.py
~~~~~~~~~~
Cleans a raw PGCB generations DataFrame (or CSV) into a well-typed
pandas DataFrame ready for database upsert.

This is the refactored version of the original automation.py,
now usable both as a module and as a standalone CLI script.
"""

import sys
import pandas as pd

BANGLA_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
VALID_YEARS = range(2015, 2031)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a raw PGCB generations DataFrame.

    Steps
    -----
    1. Translate Bangla digits → ASCII in Date & Time columns.
    2. Combine Date + Time → a single ``datetime`` column (ISO-8601).
    3. Drop rows with unparseable or out-of-range dates.
    4. Deduplicate on ``datetime`` (keep last).
    5. Cast all numeric columns to float.
    6. Sort by ``datetime`` ascending.

    Parameters
    ----------
    df : pd.DataFrame
        Raw string DataFrame as returned by ``scraper.scrape()``.

    Returns
    -------
    pd.DataFrame  with a ``datetime`` string column (YYYY-MM-DDTHH:MM:SS)
                  followed by numeric generation columns.
    """
    df = df.copy().astype(str)

    n_raw = len(df)
    print(f"[cleaner] Input rows: {n_raw}")

    # Normalise Date & Time columns
    for col in ["Date", "Time"]:
        if col in df.columns:
            df[col] = df[col].str.translate(BANGLA_TO_ASCII).str.strip()

    # Ensure HH:MM:SS format
    time_full = df["Time"].where(
        df["Time"].str.count(":") == 2,
        df["Time"] + ":00",
    )

    # Build datetime column
    df.insert(
        0,
        "datetime",
        pd.to_datetime(
            df["Date"] + " " + time_full,
            format="%d-%m-%Y %H:%M:%S",
            errors="coerce",
        ),
    )

    df = df.drop(columns=["Date", "Time"], errors="ignore")

    n_invalid = df["datetime"].isna().sum()
    df = df.dropna(subset=["datetime"])

    valid_year = df["datetime"].dt.year.isin(VALID_YEARS)
    n_invalid_year = (~valid_year).sum()
    df = df[valid_year]

    n_before = len(df)
    df = df.drop_duplicates(subset="datetime", keep="last")
    n_duplicates = n_before - len(df)

    # Cast numeric columns
    num_cols = [c for c in df.columns if c not in ("datetime", "Remarks")]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("datetime").reset_index(drop=True)

    # Serialise datetime for JSON / CSV compatibility
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"[cleaner] Invalid dates: {n_invalid}")
    print(f"[cleaner] Invalid years: {n_invalid_year}")
    print(f"[cleaner] Duplicates removed: {n_duplicates}")
    print(f"[cleaner] Final rows: {len(df)}")
    if not df.empty:
        print(f"[cleaner] Range: {df['datetime'].iloc[0]}  →  {df['datetime'].iloc[-1]}")

    return df


# ── Standalone usage ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    INPUT  = sys.argv[1] if len(sys.argv) > 1 else "pgcb_hourly_generation_full.csv"
    OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "BengalGrid_data.csv"

    raw = pd.read_csv(INPUT, dtype=str)
    cleaned = clean(raw)
    cleaned.to_csv(OUTPUT, index=False)
    print(f"[cleaner] Saved cleaned data to {OUTPUT}")

