# GridAutomation

Automated hourly scraper for [PGCB ERP Generation Data](https://erp.powergrid.gov.bd/w/generations/view_generations) → Supabase PostgreSQL.

## Architecture

```
GitHub Actions (cron: every hour)
        │
        ▼
  scraper.py   ── fetches paginated HTML tables from PGCB ERP
        │
        ▼
  cleaner.py   ── translates Bangla digits, parses datetime,
                   deduplicates, casts numeric columns
        │
        ▼
  uploader.py  ── upserts rows into Supabase `hourly_generation` table
```

## Project Structure

```
GridAutomation/
├── main.py                        # Pipeline orchestrator
├── scraper.py                     # PGCB website scraper
├── cleaner.py                     # Data cleaner (refactored from automation.py)
├── uploader.py                    # Supabase upsert client
├── automation.py                  # Original standalone cleaner (kept for reference)
├── requirements.txt
├── supabase/
│   └── schema.sql                 # Run once in Supabase SQL Editor
└── .github/
    └── workflows/
        └── cron.yml               # Hourly GitHub Actions workflow
```

## Setup

See the **Setup Guide** section below.

### 1. Supabase – Create the table

1. Open your Supabase project → **SQL Editor**
2. Paste and run the contents of [`supabase/schema.sql`](supabase/schema.sql)

### 2. GitHub – Add Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → `service_role` key |

### 3. Push & Enable Actions

```bash
git add .
git commit -m "feat: PGCB hourly generation automation"
git push origin main
```

Then go to **Actions** tab → enable workflows if prompted.

### 4. Manual backfill (first run)

Trigger the workflow manually from the Actions tab and set `pages = all`
to load the full historical dataset into Supabase.

## Local Development

```bash
pip install -r requirements.txt

# Set env vars
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Run full pipeline (5 pages ≈ latest ~125 rows)
python main.py

# Or scrape everything (backfill)
python main.py --pages all
```

