from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from capex_engine.ingestion import (
    COMMON_COLUMNS,
    DataSource,
    DataValidationError,
    FredCsvSource,
    SecCompanyFactsSource,
)


class _Response:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_sec_source_maps_quarterly_fact_and_conservatively_dates_availability(
    monkeypatch,
):
    payload = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-29",
                                "end": "2024-04-28",
                                "filed": "2024-05-22",
                                "val": 26000000000,
                            },
                            {
                                "start": "2023-10-30",
                                "end": "2024-04-28",
                                "filed": "2024-05-22",
                                "val": 40000000000,
                            },
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(
        "capex_engine.ingestion.sec.requests.get",
        lambda *args, **kwargs: _Response(payload=payload),
    )

    observations = SecCompanyFactsSource().fetch(
        "2024-01-01",
        "2024-12-31",
        ticker="NVDA",
        cik="1045810",
        user_agent="Research contact@example.org",
        fact_mapping={
            "revenue": [
                "RevenueFromContractWithCustomerExcludingAssessedTax"
            ]
        },
    )

    assert len(observations) == 1
    observation = observations.iloc[0]
    assert observation["series_id"] == "revenue"
    assert observation["value"] == 26000000000
    assert observation["available_date"] == date(2024, 5, 23)
    assert list(observations.columns) == list(COMMON_COLUMNS)


def test_sec_source_derives_standalone_quarter_from_cumulative_cash_flow(
    monkeypatch,
):
    payload = {
        "facts": {
            "us-gaap": {
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "val": 100,
                            },
                            {
                                "start": "2024-01-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "val": 260,
                            },
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(
        "capex_engine.ingestion.sec.requests.get",
        lambda *args, **kwargs: _Response(payload=payload),
    )

    observations = SecCompanyFactsSource().fetch(
        "2024-01-01",
        "2024-12-31",
        ticker="NVDA",
        cik="1045810",
        user_agent="Research contact@example.org",
        fact_mapping={
            "capital_expenditure": [
                "PaymentsToAcquirePropertyPlantAndEquipment"
            ]
        },
    )

    assert observations["value"].tolist() == [100, 160]
    assert observations["observation_date"].tolist() == [
        date(2024, 3, 31),
        date(2024, 6, 30),
    ]
    assert observations["available_date"].tolist() == [
        date(2024, 5, 2),
        date(2024, 8, 2),
    ]


def test_sec_source_preserves_non_additive_units_without_subtracting_ytd_values(
    monkeypatch,
):
    payload = {
        "facts": {
            "us-gaap": {
                "WeightedAverageNumberOfDilutedSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "val": 1000,
                            },
                            {
                                "start": "2024-01-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "val": 2100,
                            },
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(
        "capex_engine.ingestion.sec.requests.get",
        lambda *args, **kwargs: _Response(payload=payload),
    )

    observations = SecCompanyFactsSource().fetch(
        "2024-01-01",
        "2024-12-31",
        ticker="NVDA",
        cik="1045810",
        user_agent="Research contact@example.org",
        fact_mapping={
            "diluted_shares": [
                "WeightedAverageNumberOfDilutedSharesOutstanding"
            ]
        },
        fact_units={"diluted_shares": "shares"},
        non_additive_series={"diluted_shares"},
    )

    assert observations["value"].tolist() == [1000]
    assert observations["unit"].tolist() == ["shares"]


def test_fred_source_normalizes_public_csv_and_applies_configured_availability_lag(
    monkeypatch,
):
    csv_content = (
        b"observation_date,DGS10\n"
        b"2024-01-02,3.95\n"
        b"2024-01-03,.\n"
        b"2024-01-04,4.00\n"
    )
    monkeypatch.setattr(
        "capex_engine.ingestion.fred.requests.get",
        lambda *args, **kwargs: _Response(content=csv_content),
    )

    observations = FredCsvSource().fetch(
        "2024-01-01",
        "2024-01-31",
        series_id="DGS10",
        series_name="US_10Y",
        availability_lag_days=1,
    )

    assert observations["value"].tolist() == [3.95, 4.0]
    assert observations["available_date"].tolist() == [
        date(2024, 1, 3),
        date(2024, 1, 5),
    ]
    assert set(observations["source"]) == {"FRED:DGS10"}


def test_common_validation_rejects_observations_not_yet_available():
    class _NoFetchSource(DataSource):
        def fetch(self, start_date, end_date, **kwargs):
            raise NotImplementedError

    row = {
        "series_id": "revenue",
        "entity": "NVDA",
        "observation_date": "2024-03-31",
        "period_end_date": "2024-03-31",
        "available_date": "2024-03-30",
        "value": 1,
        "unit": "USD",
        "frequency": "quarterly",
        "source": "test",
        "retrieved_at": "2024-05-01T00:00:00Z",
    }

    with pytest.raises(DataValidationError, match="available_date"):
        _NoFetchSource().validate(pd.DataFrame([row]))


def test_common_validation_rejects_non_monotonic_observation_dates():
    class _NoFetchSource(DataSource):
        def fetch(self, start_date, end_date, **kwargs):
            raise NotImplementedError

    rows = [
        {
            "series_id": "US_10Y",
            "entity": "US_10Y",
            "observation_date": observed,
            "period_end_date": observed,
            "available_date": available,
            "value": value,
            "unit": "percent",
            "frequency": "daily",
            "source": "test",
            "retrieved_at": "2024-01-05T00:00:00Z",
        }
        for observed, available, value in [
            ("2024-01-04", "2024-01-05", 4.0),
            ("2024-01-02", "2024-01-03", 3.9),
        ]
    ]

    with pytest.raises(DataValidationError, match="not monotonic"):
        _NoFetchSource().validate(pd.DataFrame(rows))


def test_raw_data_is_saved_without_changing_the_dataframe(tmp_path: Path):
    class _NoFetchSource(DataSource):
        def fetch(self, start_date, end_date, **kwargs):
            raise NotImplementedError

    observations = pd.DataFrame(
        [
            {
                "series_id": "US_10Y",
                "entity": "US_10Y",
                "observation_date": "2024-01-02",
                "period_end_date": "2024-01-02",
                "available_date": "2024-01-03",
                "value": 3.95,
                "unit": "percent",
                "frequency": "daily",
                "source": "FRED:DGS10",
                "retrieved_at": "2024-01-04T00:00:00Z",
            }
        ]
    )
    original = observations.copy(deep=True)
    destination = _NoFetchSource().save_raw(
        observations, tmp_path / "macro" / "us_10y.csv"
    )

    assert destination.exists()
    pd.testing.assert_frame_equal(observations, original)
    assert pd.read_csv(destination)["value"].tolist() == [3.95]
