"""Yahoo chart API adapter for daily adjusted prices and trading volume."""

from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
import requests

from capex_engine.ingestion.base import COMMON_COLUMNS, DataSource

_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


class YahooChartSource(DataSource):
    """Fetch adjusted close and volume as point-in-time long-form observations."""

    def fetch(
        self,
        start_date,
        end_date,
        *,
        ticker: str,
        availability_lag_days: int = 1,
    ) -> pd.DataFrame:
        start = _as_date(start_date)
        end = _as_date(end_date)
        if start > end:
            raise ValueError("start_date must not be after end_date")
        if availability_lag_days < 1:
            raise ValueError(
                "availability_lag_days must be at least one day to reflect closing prices"
            )

        response = requests.get(
            _YAHOO_CHART_URL.format(ticker=ticker.upper()),
            params={
                "period1": _midnight_epoch(start),
                "period2": _midnight_epoch(end + timedelta(days=1)),
                "interval": "1d",
                "events": "div,splits",
            },
            headers={"User-Agent": "Mozilla/5.0 CapEx Transmission Engine research"},
            timeout=30,
        )
        response.raise_for_status()
        chart = response.json()["chart"]
        if chart.get("error"):
            raise ValueError(f"Yahoo chart error for {ticker}: {chart['error']}")
        result = chart["result"][0]
        timestamps = result.get("timestamp", [])
        indicators = result["indicators"]
        adjusted_close = indicators.get("adjclose", [{}])[0].get("adjclose")
        volume = indicators["quote"][0].get("volume")
        if adjusted_close is None or volume is None:
            raise ValueError(
                f"Yahoo chart response for {ticker} omitted adjusted close or volume"
            )
        if not (len(timestamps) == len(adjusted_close) == len(volume)):
            raise ValueError(f"Yahoo chart arrays have inconsistent lengths for {ticker}")

        retrieved_at = pd.Timestamp.now(tz="UTC")
        rows = []
        for timestamp, price, shares in zip(timestamps, adjusted_close, volume):
            observed = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            if not start <= observed <= end:
                continue
            available = observed + timedelta(days=availability_lag_days)
            for series_id, value, unit in (
                (f"{ticker.upper()}_adjusted_close", price, "USD"),
                (f"{ticker.upper()}_volume", shares, "shares"),
            ):
                if value is None:
                    continue
                rows.append(
                    {
                        "series_id": series_id.lower(),
                        "entity": ticker.upper(),
                        "observation_date": observed,
                        "period_end_date": observed,
                        "available_date": available,
                        "value": value,
                        "unit": unit,
                        "frequency": "daily",
                        "source": f"Yahoo Finance chart:{ticker.upper()}",
                        "retrieved_at": retrieved_at,
                    }
                )

        data = pd.DataFrame(rows, columns=COMMON_COLUMNS)
        self.validate(data)
        return data


def _as_date(value) -> date:
    return pd.Timestamp(value).date()


def _midnight_epoch(value: date) -> int:
    return int(datetime.combine(value, time.min, tzinfo=timezone.utc).timestamp())
