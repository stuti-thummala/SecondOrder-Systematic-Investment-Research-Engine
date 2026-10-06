import pandas as pd

from capex_engine.cli import _ingest
from capex_engine.ingestion import (
    COMMON_COLUMNS,
    FredCsvSource,
    SecCompanyFactsSource,
    YahooChartSource,
)


def test_ingest_fetches_all_configured_company_and_series_data(monkeypatch, tmp_path):
    sec_requests = []
    fred_requests = []
    market_requests = []

    def fake_sec_fetch(self, start_date, end_date, **kwargs):
        sec_requests.append((kwargs["ticker"], kwargs["fact_mapping"]))
        return pd.DataFrame(columns=COMMON_COLUMNS)

    def fake_fred_fetch(self, start_date, end_date, **kwargs):
        fred_requests.append(kwargs["series_name"])
        return pd.DataFrame(columns=COMMON_COLUMNS)

    def fake_market_fetch(self, start_date, end_date, **kwargs):
        market_requests.append(kwargs["ticker"])
        return pd.DataFrame(columns=COMMON_COLUMNS)

    monkeypatch.setenv("SEC_USER_AGENT", "Test Research test@example.org")
    monkeypatch.setattr(SecCompanyFactsSource, "fetch", fake_sec_fetch)
    monkeypatch.setattr(FredCsvSource, "fetch", fake_fred_fetch)
    monkeypatch.setattr(YahooChartSource, "fetch", fake_market_fetch)

    _ingest("2024-01-01", "2024-12-31", tmp_path)

    assert [ticker for ticker, _ in sec_requests] == [
        "NVDA",
        "MU",
        "VRT",
        "MSFT",
        "META",
        "GOOGL",
    ]
    assert len(fred_requests) == 9
    assert len(list((tmp_path / "fundamentals").glob("*.csv"))) == 6
    assert len(list((tmp_path / "macro").glob("*.csv"))) == 6
    assert len(list((tmp_path / "industry").glob("*.csv"))) == 3
    assert market_requests == ["NVDA", "MU", "VRT", "SPY"]
    assert len(list((tmp_path / "market").glob("*.csv"))) == 4
