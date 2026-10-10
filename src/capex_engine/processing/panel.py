"""Quarterly panel construction, coverage reporting, and as-of filtering."""

from pathlib import Path

import pandas as pd

from capex_engine.ingestion.base import COMMON_COLUMNS, DataValidationError

REPORT_COLUMNS = (
    "dataset",
    "series_id",
    "path",
    "file_exists",
    "rows",
    "missing_values",
    "missing_available_date",
    "point_in_time_violations",
    "covered_quarters",
    "missing_quarters",
)
PANEL_COLUMNS = ("quarter", *COMMON_COLUMNS)


class PointInTimeError(DataValidationError):
    """Raised when processed observations are missing availability or look ahead."""


def filter_available_as_of(data: pd.DataFrame, as_of_date) -> pd.DataFrame:
    """Return a copy containing only observations known on the requested date."""
    if "available_date" not in data:
        raise PointInTimeError("available_date is required for point-in-time filtering")
    available = pd.to_datetime(data["available_date"], errors="coerce")
    if available.isna().any():
        raise PointInTimeError("available_date contains missing or invalid dates")
    return data.loc[available.dt.date <= pd.Timestamp(as_of_date).date()].copy()


def build_quarterly_panel(
    raw_root: str | Path,
    expected_datasets: dict[str, tuple[str | Path, list[str]]],
    panel_path: str | Path,
    report_path: str | Path,
    start_date,
    end_date,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a quarterly latest-observation panel and per-series coverage report."""
    raw_root = Path(raw_root)
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start > end:
        raise ValueError("start_date must not be after end_date")

    expected_quarters = set(
        pd.period_range(start=start, end=end, freq="Q-DEC").astype(str)
    )
    panel_frames = []
    report_rows = []
    has_point_in_time_errors = False

    for dataset, (relative_path, expected_series) in expected_datasets.items():
        source_path = raw_root / relative_path
        file_exists = source_path.is_file()
        data = (
            pd.read_csv(source_path)
            if file_exists
            else pd.DataFrame(columns=COMMON_COLUMNS)
        )
        missing_columns = set(COMMON_COLUMNS).difference(data.columns)
        if file_exists and not data.empty and missing_columns:
            raise DataValidationError(
                f"{source_path} is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        if data.empty:
            series_ids = set(expected_series)
        else:
            series_ids = set(expected_series).union(data["series_id"].dropna())
            data["_observation_date"] = pd.to_datetime(
                data["observation_date"], errors="coerce"
            )
            if data["_observation_date"].isna().any():
                raise DataValidationError(
                    f"{source_path} has missing or invalid observation dates"
                )
            data["_available_date"] = pd.to_datetime(
                data["available_date"], errors="coerce"
            )
            data["_value"] = pd.to_numeric(data["value"], errors="coerce")
            data["_quarter"] = data["_observation_date"].dt.to_period("Q-DEC")
            in_range = data["_observation_date"].between(start, end)
            data = data.loc[in_range].copy()
            report_data = data

            if not data.empty:
                panel_data = data.loc[
                    data["_available_date"].notna()
                    & (data["_available_date"] >= data["_observation_date"])
                    & data["_value"].notna()
                ].copy()
                max_observation_dates = panel_data.groupby(
                    ["series_id", "entity", "_quarter"], dropna=False
                )["_observation_date"].transform("max")
                panel_data = panel_data.loc[
                    panel_data["_observation_date"] == max_observation_dates
                ].copy()
                panel_data["quarter"] = panel_data["_quarter"].astype(str)
                panel_data["observation_date"] = panel_data[
                    "_observation_date"
                ].dt.date
                panel_data["period_end_date"] = pd.to_datetime(
                    panel_data["period_end_date"], errors="coerce"
                ).dt.date
                panel_data["available_date"] = panel_data["_available_date"].dt.date
                panel_data["value"] = panel_data["_value"]
                panel_frames.append(panel_data.loc[:, PANEL_COLUMNS])

        for series_id in sorted(series_ids):
            series_data = (
                report_data.loc[report_data["series_id"] == series_id]
                if not data.empty
                else pd.DataFrame(columns=COMMON_COLUMNS)
            )
            missing_values = (
                series_data["_value"].isna().sum()
                if "_value" in series_data
                else 0
            )
            missing_availability = (
                series_data["_available_date"].isna().sum()
                if "_available_date" in series_data
                else 0
            )
            violations = _count_point_in_time_violations(series_data)
            has_point_in_time_errors |= bool(missing_availability or violations)
            covered_quarters = (
                sorted(series_data["_quarter"].astype(str).unique())
                if "_quarter" in series_data
                else []
            )
            report_rows.append(
                {
                    "dataset": dataset,
                    "series_id": series_id,
                    "path": str(Path(relative_path)),
                    "file_exists": file_exists,
                    "rows": len(series_data),
                    "missing_values": int(missing_values),
                    "missing_available_date": int(missing_availability),
                    "point_in_time_violations": int(violations),
                    "covered_quarters": len(covered_quarters),
                    "missing_quarters": len(
                        expected_quarters.difference(covered_quarters)
                    ),
                }
            )

    report = pd.DataFrame(report_rows, columns=REPORT_COLUMNS)
    report_destination = Path(report_path)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(report_destination, index=False)
    if has_point_in_time_errors:
        raise PointInTimeError(
            f"Point-in-time errors found; see missing-data report at "
            f"{report_destination}"
        )

    panel = (
        pd.concat(panel_frames, ignore_index=True)
        if panel_frames
        else pd.DataFrame(columns=PANEL_COLUMNS)
    )
    if not panel.empty:
        panel = _append_derived_fundamentals(panel)
        panel = panel.sort_values(
            ["quarter", "series_id", "entity", "observation_date", "available_date"]
        ).reset_index(drop=True)
    panel_destination = Path(panel_path)
    panel_destination.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(panel_destination, index=False)
    return panel, report


def _append_derived_fundamentals(panel: pd.DataFrame) -> pd.DataFrame:
    """Add derived company fundamentals, retaining latest-input availability."""
    fundamentals = panel.loc[
        panel["series_id"].isin(
            {
                "revenue",
                "gross_profit",
                "operating_income",
                "operating_cash_flow",
                "capital_expenditure",
                "total_debt_current",
                "total_debt_noncurrent",
            }
        )
    ].copy()
    if fundamentals.empty:
        return panel

    fundamentals["available_date"] = pd.to_datetime(
        fundamentals["available_date"], errors="raise"
    )
    fundamentals["period_end_date"] = pd.to_datetime(
        fundamentals["period_end_date"], errors="raise"
    )
    fundamentals["value"] = pd.to_numeric(fundamentals["value"], errors="raise")
    latest = fundamentals.sort_values("available_date").drop_duplicates(
        ["entity", "period_end_date", "series_id"], keep="last"
    )
    values = latest.pivot(
        index=["entity", "period_end_date"],
        columns="series_id",
        values="value",
    )
    available = latest.groupby(["entity", "period_end_date"])[
        "available_date"
    ].max()
    retrieved = latest.groupby(["entity", "period_end_date"])[
        "retrieved_at"
    ].max()
    rows = []

    for (entity, period_end), inputs in values.iterrows():
        if "revenue" in inputs and pd.notna(inputs["revenue"]):
            if "gross_profit" in inputs and pd.notna(inputs["gross_profit"]):
                rows.append(
                    _derived_row(
                        "gross_margin",
                        entity,
                        period_end,
                        inputs["gross_profit"] / inputs["revenue"],
                        "ratio",
                        available.loc[(entity, period_end)],
                        retrieved.loc[(entity, period_end)],
                    )
                )
            if "operating_income" in inputs and pd.notna(
                inputs["operating_income"]
            ):
                rows.append(
                    _derived_row(
                        "operating_margin",
                        entity,
                        period_end,
                        inputs["operating_income"] / inputs["revenue"],
                        "ratio",
                        available.loc[(entity, period_end)],
                        retrieved.loc[(entity, period_end)],
                    )
                )
            if (
                "operating_cash_flow" in inputs
                and pd.notna(inputs["operating_cash_flow"])
                and "capital_expenditure" in inputs
                and pd.notna(inputs["capital_expenditure"])
            ):
                free_cash_flow = (
                    inputs["operating_cash_flow"] - inputs["capital_expenditure"]
                )
                rows.extend(
                    [
                        _derived_row(
                            "free_cash_flow",
                            entity,
                            period_end,
                            free_cash_flow,
                            "USD",
                            available.loc[(entity, period_end)],
                            retrieved.loc[(entity, period_end)],
                        ),
                        _derived_row(
                            "free_cash_flow_margin",
                            entity,
                            period_end,
                            free_cash_flow / inputs["revenue"],
                            "ratio",
                            available.loc[(entity, period_end)],
                            retrieved.loc[(entity, period_end)],
                        ),
                    ]
                )

        if (
            "total_debt_current" in inputs
            and pd.notna(inputs["total_debt_current"])
            and "total_debt_noncurrent" in inputs
            and pd.notna(inputs["total_debt_noncurrent"])
        ):
            rows.append(
                _derived_row(
                    "total_debt",
                    entity,
                    period_end,
                    inputs["total_debt_current"] + inputs["total_debt_noncurrent"],
                    "USD",
                    available.loc[(entity, period_end)],
                    retrieved.loc[(entity, period_end)],
                )
            )

    if not rows:
        return panel
    return pd.concat([panel, pd.DataFrame(rows, columns=PANEL_COLUMNS)], ignore_index=True)


def _derived_row(
    series_id: str,
    entity: str,
    period_end: pd.Timestamp,
    value: float,
    unit: str,
    available_date: pd.Timestamp,
    retrieved_at,
) -> dict:
    period_end_date = period_end.date()
    return {
        "quarter": str(period_end.to_period("Q-DEC")),
        "series_id": series_id,
        "entity": entity,
        "observation_date": period_end_date,
        "period_end_date": period_end_date,
        "available_date": available_date.date(),
        "value": value,
        "unit": unit,
        "frequency": "quarterly",
        "source": "derived:fundamental_metrics",
        "retrieved_at": retrieved_at,
    }


def _count_point_in_time_violations(data: pd.DataFrame) -> int:
    if data.empty or not {"observation_date", "available_date"}.issubset(data.columns):
        return 0
    observed = pd.to_datetime(data["observation_date"], errors="coerce")
    available = pd.to_datetime(data["available_date"], errors="coerce")
    return int(available.isna().sum() + (available < observed).fillna(False).sum())
