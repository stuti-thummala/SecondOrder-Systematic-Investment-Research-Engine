from datetime import date

import pytest

from capex_engine.ingestion import COMMON_COLUMNS, YahooChartSource


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_yahoo_source_maps_adjusted_close_and_volume_to_common_schema(monkeypatch):
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1704153600, 1704240000],
                    "indicators": {
                        "adjclose": [{"adjclose": [48.5, None]}],
                        "quote": [{"volume": [1000, 1200]}],
                    },
                }
            ],
            "error": None,
        }
    }
    monkeypatch.setattr(
        "capex_engine.ingestion.market.requests.get",
        lambda *args, **kwargs: _Response(payload),
    )

    observations = YahooChartSource().fetch(
        "2024-01-02", "2024-01-03", ticker="NVDA"
    )

    assert set(observations["series_id"]) == {
        "nvda_adjusted_close",
        "nvda_volume",
    }
    price = observations.loc[
        observations["series_id"] == "nvda_adjusted_close"
    ].iloc[0]
    assert price["value"] == 48.5
    assert price["available_date"] == date(2024, 1, 3)
    assert observations["entity"].tolist() == ["NVDA", "NVDA", "NVDA"]
    assert list(observations.columns) == list(COMMON_COLUMNS)


def test_yahoo_source_rejects_same_day_market_availability():
    with pytest.raises(ValueError, match="at least one day"):
        YahooChartSource().fetch(
            "2024-01-02",
            "2024-01-03",
            ticker="NVDA",
            availability_lag_days=0,
        )
