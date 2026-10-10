import pandas as pd
import pytest

from capex_engine.ingestion import COMMON_COLUMNS
from capex_engine.processing import (
    PointInTimeError,
    build_quarterly_panel,
    filter_available_as_of,
)


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
