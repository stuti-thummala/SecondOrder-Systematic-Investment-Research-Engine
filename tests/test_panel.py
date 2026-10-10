import pandas as pd
import pytest

from capex_engine.ingestion import COMMON_COLUMNS
from capex_engine.processing import (
    PointInTimeError,
    build_quarterly_panel,
    filter_available_as_of,
)
from capex_engine.ingestion import DataValidationError


def _observation(observation_date, available_date, value):
    return {
        "series_id": "revenue",
        "entity": "NVDA",
        "observation_date": observation_date,
        "period_end_date": observation_date,
        "available_date": available_date,
        "value": value,
        "unit": "USD",
        "frequency": "quarterly",
        "source": "SEC Company Facts:NVDA",
        "retrieved_at": "2024-05-21T00:00:00Z",
    }


def _fundamental(series_id, value, available_date="2024-05-20"):
    return {
        **_observation("2024-03-31", available_date, value),
        "series_id": series_id,
    }


def test_quarterly_panel_preserves_availability_and_as_of_filter(tmp_path):
    raw_root = tmp_path / "raw"
    source_path = raw_root / "fundamentals" / "nvda.csv"
    source_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [_observation("2024-03-31", "2024-05-20", 100)]
    ).to_csv(source_path, index=False)

    panel, report = build_quarterly_panel(
        raw_root,
        {"nvda_fundamentals": ("fundamentals/nvda.csv", ["revenue"])},
        tmp_path / "processed" / "quarterly_panel.csv",
        tmp_path / "metadata" / "missing_data_report.csv",
        "2024-01-01",
        "2024-06-30",
    )

    assert list(panel.columns) == ["quarter", *COMMON_COLUMNS]
    assert panel["quarter"].tolist() == ["2024Q1"]
    assert panel["available_date"].tolist() == [pd.Timestamp("2024-05-20").date()]
    assert report["point_in_time_violations"].sum() == 0
    assert report["missing_quarters"].tolist() == [1]
    assert filter_available_as_of(panel, "2024-04-30").empty
    assert len(filter_available_as_of(panel, "2024-05-20")) == 1


def test_quarterly_panel_reports_and_rejects_point_in_time_violations(tmp_path):
    raw_root = tmp_path / "raw"
    source_path = raw_root / "fundamentals" / "nvda.csv"
    source_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [_observation("2024-03-31", "2024-03-30", 100)]
    ).to_csv(source_path, index=False)
    report_path = tmp_path / "metadata" / "missing_data_report.csv"

    with pytest.raises(PointInTimeError, match="missing-data report"):
        build_quarterly_panel(
            raw_root,
            {"nvda_fundamentals": ("fundamentals/nvda.csv", ["revenue"])},
            tmp_path / "processed" / "quarterly_panel.csv",
            report_path,
            "2024-01-01",
            "2024-03-31",
        )

    report = pd.read_csv(report_path)
    assert report["point_in_time_violations"].tolist() == [1]
    assert not (tmp_path / "processed" / "quarterly_panel.csv").exists()


def test_missing_expected_input_is_explicit_in_coverage_report(tmp_path):
    _, report = build_quarterly_panel(
        tmp_path / "raw",
        {"nvda_fundamentals": ("fundamentals/nvda.csv", ["revenue"])},
        tmp_path / "processed" / "quarterly_panel.csv",
        tmp_path / "metadata" / "missing_data_report.csv",
        "2024-01-01",
        "2024-03-31",
    )

    assert report.loc[0, "file_exists"] == False  # noqa: E712
    assert report.loc[0, "rows"] == 0
    assert report.loc[0, "missing_quarters"] == 1


def test_quarterly_panel_rejects_invalid_observation_dates(tmp_path):
    raw_root = tmp_path / "raw"
    source_path = raw_root / "fundamentals" / "nvda.csv"
    source_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [_observation("not-a-date", "2024-05-20", 100)]
    ).to_csv(source_path, index=False)

    with pytest.raises(DataValidationError, match="observation dates"):
        build_quarterly_panel(
            raw_root,
            {"nvda_fundamentals": ("fundamentals/nvda.csv", ["revenue"])},
            tmp_path / "processed" / "quarterly_panel.csv",
            tmp_path / "metadata" / "missing_data_report.csv",
            "2024-01-01",
            "2024-06-30",
        )


def test_quarterly_panel_derives_margins_cash_flow_and_total_debt(tmp_path):
    raw_root = tmp_path / "raw"
    source_path = raw_root / "fundamentals" / "nvda.csv"
    source_path.parent.mkdir(parents=True)
    rows = [
        _fundamental("revenue", 1000, "2024-05-20"),
        _fundamental("gross_profit", 600, "2024-05-21"),
        _fundamental("operating_income", 300, "2024-05-20"),
        _fundamental("operating_cash_flow", 250, "2024-05-20"),
        _fundamental("capital_expenditure", 50, "2024-05-22"),
        _fundamental("total_debt_current", 20, "2024-05-20"),
        _fundamental("total_debt_noncurrent", 80, "2024-05-21"),
    ]
    pd.DataFrame(rows).to_csv(source_path, index=False)

    panel, _ = build_quarterly_panel(
        raw_root,
        {
            "nvda_fundamentals": (
                "fundamentals/nvda.csv",
                [row["series_id"] for row in rows],
            )
        },
        tmp_path / "processed" / "quarterly_panel.csv",
        tmp_path / "metadata" / "missing_data_report.csv",
        "2024-01-01",
        "2024-06-30",
    )

    derived = panel.loc[
        panel["source"] == "derived:fundamental_metrics"
    ].set_index("series_id")
    assert derived.loc["gross_margin", "value"] == 0.6
    assert derived.loc["operating_margin", "value"] == 0.3
    assert derived.loc["free_cash_flow", "value"] == 200
    assert derived.loc["free_cash_flow_margin", "value"] == 0.2
    assert derived.loc["total_debt", "value"] == 100
    assert set(derived["available_date"]) == {pd.Timestamp("2024-05-22").date()}
