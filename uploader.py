"""
uploader.py
~~~~~~~~~~~
Upserts a cleaned PGCB generations DataFrame into Supabase Postgres.

Environment variables required
-------------------------------
SUPABASE_URL              – Project URL  (e.g. https://xxxx.supabase.co)
SUPABASE_SERVICE_ROLE_KEY – service_role API key  (bypasses RLS)

Table targeted: ``hourly_generation``
Primary key / upsert conflict column: ``datetime``
"""

import os
import math
import pandas as pd
from supabase import create_client, Client

TABLE_NAME   = "hourly_generation"
BATCH_SIZE   = 500          # rows per upsert call (Supabase REST limit ~1 000)
CONFLICT_COL = "datetime"   # unique PK – no double-inserts on re-runs


def _get_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        raise EnvironmentError(
            "Missing env vars: SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY"
        )
    return create_client(url, key)


def _get_table_columns(client: Client, url: str, key: str) -> set[str]:
    """
    Fetch column names that actually exist in the target table.
    Tries the PostgREST OpenAPI schema first (works even when the table is empty),
    then falls back to inspecting a sample row.
    """
    import requests
    # 1. Try OpenAPI schema from PostgREST
    try:
        resp = requests.get(
            f"{url}/rest/v1/",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            schema = resp.json()
            # Swagger 2.0 (PostgREST default)
            props = schema.get("definitions", {}).get(TABLE_NAME, {}).get("properties")
            if not props:
                # OpenAPI 3.0
                props = schema.get("components", {}).get("schemas", {}).get(TABLE_NAME, {}).get("properties")
            if props:
                return set(props.keys())
    except Exception as exc:
        print(f"[uploader] Note: Could not fetch schema via OpenAPI: {exc}")

    # 2. Fall back to querying existing row
    try:
        resp = client.table(TABLE_NAME).select("*").limit(1).execute()
        if resp.data:
            return set(resp.data[0].keys())
    except Exception:
        pass

    return set()


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows to JSON-serialisable dicts (NaN → None)."""
    records = df.to_dict(orient="records")
    cleaned = []
    for rec in records:
        cleaned.append(
            {
                k: (None if (isinstance(v, float) and math.isnan(v)) else v)
                for k, v in rec.items()
            }
        )
    return cleaned


def _filter_known_columns(records: list[dict], known_cols: set[str]) -> list[dict]:
    """Drop any keys that don't exist as columns in the Supabase table."""
    if not known_cols:
        return records
    filtered = []
    for rec in records:
        filtered.append({k: v for k, v in rec.items() if k in known_cols})
    return filtered


def upload(df: pd.DataFrame) -> int:
    """
    Upsert *df* into the ``hourly_generation`` Supabase table.

    Returns the total number of rows upserted.
    """
    if df.empty:
        print("[uploader] DataFrame is empty – nothing to upload.")
        return 0

    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    client = _get_client()
    records = _df_to_records(df)

    # ── Filter out columns the table doesn't know about ──────────────────────
    known_cols = _get_table_columns(client, url, key)
    if known_cols:
        before = len(next(iter(records), {}).keys()) if records else 0
        records = _filter_known_columns(records, known_cols)
        after  = len(next(iter(records), {}).keys()) if records else 0
        dropped = before - after
        if dropped:
            missing = set(df.columns) - known_cols
            print(f"[uploader] Dropped {dropped} column(s) not in Supabase schema: {missing}")
    # ─────────────────────────────────────────────────────────────────────────

    total   = len(records)
    batches = math.ceil(total / BATCH_SIZE)
    upserted = 0

    print(f"[uploader] Upserting {total} rows in {batches} batch(es) …")

    for i in range(batches):
        batch = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        resp  = (
            client.table(TABLE_NAME)
            .upsert(batch, on_conflict=CONFLICT_COL)
            .execute()
        )
        upserted += len(resp.data)
        print(f"[uploader] Batch {i + 1}/{batches}: {len(resp.data)} rows OK")

    print(f"[uploader] Done. Total upserted: {upserted}")
    return upserted


# ── Standalone usage ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "BengalGrid_data.csv"
    df = pd.read_csv(csv_path)
    upload(df)

