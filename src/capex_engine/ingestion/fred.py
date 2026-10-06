"""Public FRED CSV adapter for macroeconomic observations."""

from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import requests

from capex_engine.ingestion.base import COMMON_COLUMNS, DataSource

_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class FredCsvSource(DataSource):
    """Fetch a public FRED series and assign a documented availability lag."""

    def fetch(
        self,
        start_date,
        end_date,
        *,
        series_id: str,
        series_name: str,
        availability_lag_days: int,
    ) -> pd.DataFrame:
        start = _as_date(start_date)
        end = _as_date(end_date)
        if start > end:
            raise ValueError("start_date must not be after end_date")
        if availability_lag_days < 0:
            raise ValueError("availability_lag_days must be non-negative")

        response = requests.get(
            _FRED_CSV_URL,
            params={
                "id": series_id,
                "cosd": start.isoformat(),
                "coed": end.isoformat(),
            },
            timeout=30,
        )
        response.raise_for_status()
        source_data = pd.read_csv(BytesIO(response.content), na_values=["."])
        if not {"observation_date", series_id}.issubset(source_data.columns):
            raise ValueError(
                f"Unexpected FRED CSV columns for {series_id}: "
                f"{list(source_data.columns)}"
            )

        observation_dates = pd.to_datetime(
            source_data["observation_date"], errors="raise"
        ).dt.date
        values = pd.to_numeric(source_data[series_id], errors="coerce")
        valid = values.notna() & observation_dates.map(
            lambda observed: start <= observed <= end
        )
        observation_dates = observation_dates[valid]
        values = values[valid]
        retrieved_at = pd.Timestamp.now(tz="UTC")
        data = pd.DataFrame(
            {
                "series_id": series_name,
                "entity": series_name,
                "observation_date": observation_dates,
                "period_end_date": observation_dates,
                "available_date": observation_dates.map(
                    lambda observed: observed + timedelta(days=availability_lag_days)
                ),
                "value": values,
                "unit": "percent",
                "frequency": "daily",
                "source": f"FRED:{series_id}",
                "retrieved_at": retrieved_at,
            }
        ).reset_index(drop=True)
        data = data.loc[:, COMMON_COLUMNS]
        self.validate(data)
        return data


def _as_date(value) -> date:
    return pd.Timestamp(value).date()
