"""Shared data-source contract and common observation validation."""

from abc import ABC, abstractmethod
from math import isfinite
from pathlib import Path

import pandas as pd

COMMON_COLUMNS = (
    "series_id",
    "entity",
    "observation_date",
    "period_end_date",
    "available_date",
    "value",
    "unit",
    "frequency",
    "source",
    "retrieved_at",
)

_DATE_COLUMNS = ("observation_date", "period_end_date", "available_date")
_PRIMARY_KEY = ("series_id", "entity", "observation_date", "available_date")


class DataValidationError(ValueError):
    """Raised when source observations violate the common data contract."""


class DataSource(ABC):
    """Interface shared by all external data adapters."""

    @abstractmethod
    def fetch(self, start_date, end_date, **kwargs) -> pd.DataFrame:
        """Fetch observations for an inclusive date range."""

    def validate(self, data: pd.DataFrame) -> None:
        """Validate common schema, keys, numeric values, and date ordering."""
        missing_columns = set(COMMON_COLUMNS).difference(data.columns)
        if missing_columns:
            raise DataValidationError(
                f"Missing required observation columns: {sorted(missing_columns)}"
            )

        if data.empty:
            return

        for column in _DATE_COLUMNS:
            dates = pd.to_datetime(data[column], errors="coerce")
            if dates.isna().any():
                raise DataValidationError(f"{column} contains missing or invalid dates")

        values = pd.to_numeric(data["value"], errors="coerce")
        if values.isna().any():
            raise DataValidationError("value contains missing or invalid numeric values")
        if not values.map(isfinite).all():
            raise DataValidationError("value contains non-finite numeric values")

        available = pd.to_datetime(data["available_date"])
        observed = pd.to_datetime(data["observation_date"])
        if (available < observed).any():
            raise DataValidationError(
                "available_date cannot be earlier than observation_date"
            )

        if data.duplicated(subset=_PRIMARY_KEY).any():
            raise DataValidationError(
                f"Duplicate observations for primary key {_PRIMARY_KEY}"
            )

        ordered = data.assign(_observation_date=observed)
        for _, group in ordered.groupby(["series_id", "entity"], sort=False):
            if not group["_observation_date"].is_monotonic_increasing:
                raise DataValidationError("observation_date values are not monotonic")

    def save_raw(self, data: pd.DataFrame, path: str | Path) -> Path:
        """Persist fetched observations as CSV without mutating the frame."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(destination, index=False)
        return destination
