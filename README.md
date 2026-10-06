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
Company Facts, FRED CSV, and Yahoo chart ingestion adapters. The adapters make
HTTP requests only when the `ingest` command is run; tests use local fixtures
and do not require network access. Before SEC ingestion, set `SEC_USER_AGENT`
to a descriptive name and contact address, as required by SEC fair-access
guidance:

```bash
export SEC_USER_AGENT="Researcher Name researcher@example.org"
```

```bash
python -m capex_engine ingest --start-date 2016-01-01 --end-date 2026-10-06
```

Ingestion covers NVDA, MU, and VRT fundamentals; MSFT, META, and GOOGL
CapEx; daily adjusted close and volume for the core companies and SPY; the
configured macro series; and three documented industry proxies. Raw CSVs are
written under `data/raw/` and excluded from version control. SEC filing dates
are made available the following calendar day. FRED observations use
series-specific conservative calendar-day lags in `config/sources.yaml`.
These date-level policies do not claim intraday release precision or preserve
historical source vintages; vintage-sensitive research must account for this
limitation.

Project scope and detailed requirements are in [SPEC.md](./SPEC.md); the
original supplied file, [spec.md](./spec.md), is retained unchanged.
