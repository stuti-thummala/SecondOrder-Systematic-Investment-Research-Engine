"""Command-line entry point for the research pipeline."""

import argparse
import logging
import os
from datetime import date
from pathlib import Path

import yaml

from capex_engine.ingestion import (
    FredCsvSource,
    SecCompanyFactsSource,
    YahooChartSource,
)
from capex_engine.processing import build_quarterly_panel

LOGGER = logging.getLogger("capex_engine")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(prog="capex_engine")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="fetch configured raw datasets")
    ingest.add_argument("--start-date")
    ingest.add_argument("--end-date", default=date.today().isoformat())
    ingest.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/raw")
    features = commands.add_parser(
        "features", help="build point-in-time quarterly research panel"
    )
    features.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "data/raw")
    features.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "data/processed"
    )
    features.add_argument("--start-date")
    features.add_argument("--end-date", default=date.today().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "ingest":
        _ingest(args.start_date, args.end_date, args.output_dir)
    elif args.command == "features":
        _features(
            args.start_date,
            args.end_date,
            args.input_dir,
            args.output_dir,
        )


def _ingest(start_date: str | None, end_date: str, output_dir: Path) -> None:
    research_config = _read_yaml(PROJECT_ROOT / "config/research.yaml")
    source_config = _read_yaml(PROJECT_ROOT / "config/sources.yaml")
    company_config = _read_yaml(PROJECT_ROOT / "config/companies.yaml")
    start_date = start_date or research_config["start_date"]

    sec_config = source_config["fundamentals"]["sec_company_facts"]
    sec_user_agent = os.environ.get("SEC_USER_AGENT", "")
    if not sec_user_agent.strip():
        raise RuntimeError(
            "Set SEC_USER_AGENT to a descriptive contact string before SEC ingestion"
        )

    sec_source = SecCompanyFactsSource()
    for ticker, company in company_config["core_companies"].items():
        sec_data = sec_source.fetch(
            start_date,
            end_date,
            ticker=ticker,
            cik=company["cik"],
            user_agent=sec_user_agent,
            fact_mapping=sec_config["facts"],
            fact_units=sec_config.get("fact_units"),
            non_additive_series=set(sec_config.get("non_additive_series", [])),
            instant_series=set(sec_config.get("instant_series", [])),
        )
        sec_path = output_dir / "fundamentals" / f"{ticker.lower()}_fundamentals.csv"
        sec_source.save_raw(sec_data, sec_path)
        LOGGER.info(
            "ingested dataset=%s_fundamentals rows=%d path=%s",
            ticker.lower(),
            len(sec_data),
            sec_path,
        )

    for ticker, company in company_config["capex_drivers"].items():
        capex_data = sec_source.fetch(
            start_date,
            end_date,
            ticker=ticker,
            cik=company["cik"],
            user_agent=sec_user_agent,
            fact_mapping={"capital_expenditure": sec_config["capex_fact"]},
        )
        capex_path = output_dir / "fundamentals" / f"{ticker.lower()}_capex.csv"
        sec_source.save_raw(capex_data, capex_path)
        LOGGER.info(
            "ingested dataset=%s_capex rows=%d path=%s",
            ticker.lower(),
            len(capex_data),
            capex_path,
        )

    fred_source = FredCsvSource()
    for category in ("macro", "industry"):
        fred_config = source_config[category]["fred_csv"]
        for series_name, series in fred_config["series"].items():
            fred_data = fred_source.fetch(
                start_date,
                end_date,
                series_id=series["series_id"],
                series_name=series_name,
                availability_lag_days=series["availability_lag_days"],
            )
            fred_path = output_dir / category / f"{series_name.lower()}.csv"
            fred_source.save_raw(fred_data, fred_path)
            LOGGER.info(
                "ingested dataset=%s rows=%d path=%s",
                series_name.lower(),
                len(fred_data),
                fred_path,
            )

    market_config = source_config["market"]["yahoo_chart"]
    market_source = YahooChartSource()
    tickers = dict.fromkeys(
        research_config["core_universe"] + [research_config["benchmark"]]
    )
    for ticker in tickers:
        market_data = market_source.fetch(
            start_date,
            end_date,
            ticker=ticker,
            availability_lag_days=market_config["availability_lag_days"],
        )
        market_path = output_dir / "market" / f"{ticker.lower()}_prices.csv"
        market_source.save_raw(market_data, market_path)
        LOGGER.info(
            "ingested dataset=%s_prices rows=%d path=%s",
            ticker.lower(),
            len(market_data),
            market_path,
        )


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _features(
    start_date: str | None,
    end_date: str,
    input_dir: Path,
    output_dir: Path,
) -> None:
    research_config = _read_yaml(PROJECT_ROOT / "config/research.yaml")
    source_config = _read_yaml(PROJECT_ROOT / "config/sources.yaml")
    company_config = _read_yaml(PROJECT_ROOT / "config/companies.yaml")
    start_date = start_date or research_config["start_date"]

    expected_datasets = {}
    sec_series = list(source_config["fundamentals"]["sec_company_facts"]["facts"])
    for ticker in company_config["core_companies"]:
        expected_datasets[f"{ticker.lower()}_fundamentals"] = (
            Path("fundamentals") / f"{ticker.lower()}_fundamentals.csv",
            sec_series,
        )
    for ticker in company_config["capex_drivers"]:
        expected_datasets[f"{ticker.lower()}_capex"] = (
            Path("fundamentals") / f"{ticker.lower()}_capex.csv",
            ["capital_expenditure"],
        )

    for category in ("macro", "industry"):
        for series_name in source_config[category]["fred_csv"]["series"]:
            expected_datasets[series_name.lower()] = (
                Path(category) / f"{series_name.lower()}.csv",
                [series_name],
            )

    tickers = dict.fromkeys(
        research_config["core_universe"] + [research_config["benchmark"]]
    )
    for ticker in tickers:
        expected_datasets[f"{ticker.lower()}_market"] = (
            Path("market") / f"{ticker.lower()}_prices.csv",
            [f"{ticker.lower()}_adjusted_close", f"{ticker.lower()}_volume"],
        )

    panel_path = output_dir / "quarterly_panel.csv"
    report_path = output_dir / "missing_data_report.csv"
    panel, report = build_quarterly_panel(
        input_dir,
        expected_datasets,
        panel_path,
        report_path,
        start_date,
        end_date,
    )
    LOGGER.info(
        "built quarterly_panel rows=%d series=%d path=%s",
        len(panel),
        report["series_id"].nunique(),
        panel_path,
    )
    LOGGER.info(
        "wrote missing_data_report rows=%d path=%s",
        len(report),
        report_path,
    )
    missing_files = int((~report["file_exists"]).sum())
    missing_quarters = int(report["missing_quarters"].sum())
    if missing_files or missing_quarters:
        LOGGER.warning(
            "incomplete data coverage missing_files=%d missing_series_quarters=%d "
            "report=%s",
            missing_files,
            missing_quarters,
            report_path,
        )
