# CapEx Transmission Engine

An interpretable, point-in-time research system for studying how hyperscaler
capital expenditure passes through AI infrastructure supply chains and into
company fundamentals.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Use Python 3.12 or newer. The current Day 1 implementation includes SEC
Company Facts and FRED CSV ingestion adapters. The adapters make HTTP requests
only when the `ingest` command is run; tests use local fixtures and do not
require network access. Before SEC ingestion, set `SEC_USER_AGENT` to a
descriptive name and contact address, as required by SEC fair-access guidance:

```bash
export SEC_USER_AGENT="Researcher Name researcher@example.org"
```

```bash
python -m capex_engine ingest --start-date 2016-01-01 --end-date 2026-10-06
```

The SEC adapter currently retrieves NVDA quarterly revenue facts. The FRED
adapter retrieves the 10-year Treasury yield (`DGS10`). Raw ingested CSV files
are written under `data/raw/` and are excluded from version control. SEC
availability is conservatively set to the day after filing; the FRED source
configuration documents its one-calendar-day availability lag. These
date-level policies do not claim intraday release precision.

Project scope and detailed requirements are in [SPEC.md](./SPEC.md); the
original supplied file, [spec.md](./spec.md), is retained unchanged.
