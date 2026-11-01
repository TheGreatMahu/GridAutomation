
import sys
import pandas as pd

INPUT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "pgcb_hourly_generation_full.csv"
)
OUTPUT = (
    sys.argv[2]
    if len(sys.argv) > 2
    else "BengalGrid_data.csv"
)

BANGLA_TO_ASCII = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789"
)

df = pd.read_csv(INPUT, dtype=str)
n_raw = len(df)

for col in ["Date", "Time"]:
    df[col] = df[col].str.translate(
        BANGLA_TO_ASCII
    ).str.strip()

time_full = df["Time"].where(
    df["Time"].str.count(":") == 2,
    df["Time"] + ":00"
)

df.insert(
    0,
    "datetime",
    pd.to_datetime(
        df["Date"] + " " + time_full,
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce"
    )
)

df = df.drop(columns=["Date", "Time"])

n_invalid = df["datetime"].isna().sum()
df = df.dropna(subset=["datetime"])

# Preserve the original cleaning rule.
valid_year = df["datetime"].dt.year.between(2015, 2026)
n_invalid_year = (~valid_year).sum()
df = df[valid_year]

n_before = len(df)
df = df.drop_duplicates(
    subset="datetime",
    keep="last"
)
n_duplicates = n_before - len(df)

num_cols = [
    col for col in df.columns
    if col not in ("datetime", "Remarks")
]

df[num_cols] = df[num_cols].apply(
    pd.to_numeric,
    errors="coerce"
)

df = df.sort_values("datetime").reset_index(drop=True)
df["datetime"] = df["datetime"].dt.strftime(
    "%Y-%m-%dT%H:%M:%S"
)

df.to_csv(OUTPUT, index=False)

print(f"Input rows: {n_raw}")
print(f"Invalid dates: {n_invalid}")
print(f"Invalid years: {n_invalid_year}")
print(f"Duplicate timestamps removed: {n_duplicates}")
print(f"Final rows: {len(df)}")
print(f"Output file: {OUTPUT}")

if not df.empty:
    print(f"Start: {df['datetime'].iloc[0]}")
    print(f"End:   {df['datetime'].iloc[-1]}")