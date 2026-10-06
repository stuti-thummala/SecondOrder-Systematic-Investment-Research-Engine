"""Command-line entry point for the research pipeline."""

import argparse
import logging
import os
from datetime import date
from pathlib import Path

import yaml

from capex_engine.ingestion import FredCsvSource, SecCompanyFactsSource

LOGGER = logging.getLogger("capex_engine")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(prog="capex_engine")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="fetch configured raw datasets")
    ingest.add_argument("--start-date")
    ingest.add_argument("--end-date", default=date.today().isoformat())
    ingest.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/raw")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "ingest":
        _ingest(args.start_date, args.end_date, args.output_dir)


def _ingest(start_date: str | None, end_date: str, output_dir: Path) -> None:
    research_config = _read_yaml(PROJECT_ROOT / "config/research.yaml")
    source_config = _read_yaml(PROJECT_ROOT / "config/sources.yaml")
    start_date = start_date or research_config["start_date"]

    sec_config = source_config["fundamentals"]["sec_company_facts"]
    sec_user_agent = os.environ.get("SEC_USER_AGENT", sec_config.get("user_agent", ""))
    if not sec_user_agent.strip():
        raise RuntimeError(
            "Set SEC_USER_AGENT to a descriptive contact string before SEC ingestion"
        )

    sec_data = SecCompanyFactsSource().fetch(
        start_date,
        end_date,
        ticker=sec_config["ticker"],
        cik=sec_config["cik"],
        user_agent=sec_user_agent,
        fact_mapping=sec_config["facts"],
    )
    sec_path = output_dir / "fundamentals" / "nvda_revenue.csv"
    SecCompanyFactsSource().save_raw(sec_data, sec_path)
    LOGGER.info("ingested dataset=nvda_revenue rows=%d path=%s", len(sec_data), sec_path)

    fred_config = source_config["macro"]["fred_csv"]
    fred_data = FredCsvSource().fetch(
        start_date,
        end_date,
        series_id=fred_config["series_id"],
        series_name=fred_config["series_name"],
        availability_lag_days=fred_config["availability_lag_days"],
    )
    fred_path = output_dir / "macro" / "us_10y.csv"
    FredCsvSource().save_raw(fred_data, fred_path)
    LOGGER.info("ingested dataset=us_10y rows=%d path=%s", len(fred_data), fred_path)


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)
