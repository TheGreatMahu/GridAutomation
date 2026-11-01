-- supabase/schema.sql
-- Run this once in the Supabase SQL Editor to create the target table.

CREATE TABLE IF NOT EXISTS hourly_generation (
    -- Timestamp of the generation reading (PRIMARY KEY – ensures idempotent upserts)
    datetime         TIMESTAMPTZ    NOT NULL PRIMARY KEY,

    -- Total grid generation in MW
    "Generation(MW)" NUMERIC,

    -- Fuel-type breakdowns (all in MW)
    "Gas"            NUMERIC,
    "Liquid Fuel"    NUMERIC,
    "Coal"           NUMERIC,
    "Hydro"          NUMERIC,
    "Solar"          NUMERIC,
    "Wind"           NUMERIC,

    -- Cross-border imports
    "India"          NUMERIC,
    "Nepal"          NUMERIC,
    "Adani"          NUMERIC,   -- Adani power import (added to PGCB portal)

    -- Free-text remarks (optional)
    "Remarks"        TEXT,

    -- Metadata
    inserted_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- Ensure the Adani column exists if the table was created previously
ALTER TABLE hourly_generation ADD COLUMN IF NOT EXISTS "Adani" NUMERIC;

-- Index for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_hourly_generation_datetime
    ON hourly_generation (datetime DESC);

-- Optional: enable Row Level Security (RLS) – read-only for anon users
ALTER TABLE hourly_generation ENABLE ROW LEVEL SECURITY;

-- Allow anyone to SELECT (public dashboard use case)
CREATE POLICY "Allow public read"
    ON hourly_generation
    FOR SELECT
    USING (true);

-- Only service_role (our automation) can INSERT / UPDATE
-- (No extra policy needed: service_role bypasses RLS by default)

