"""SEC Company Facts adapter for quarterly fundamentals."""

from datetime import date, timedelta

import pandas as pd
import requests

from capex_engine.ingestion.base import COMMON_COLUMNS, DataSource

_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_QUARTER_MIN_DAYS = 70
_QUARTER_MAX_DAYS = 110


class SecCompanyFactsSource(DataSource):
    """Fetch quarterly USD facts, preserving filing-date availability."""

    def fetch(
        self,
        start_date,
        end_date,
        *,
        ticker: str,
        cik: str,
        user_agent: str,
        fact_mapping: dict[str, list[str]],
        fact_units: dict[str, str] | None = None,
        non_additive_series: set[str] | None = None,
        instant_series: set[str] | None = None,
    ) -> pd.DataFrame:
        start = _as_date(start_date)
        end = _as_date(end_date)
        if start > end:
            raise ValueError("start_date must not be after end_date")
        if not user_agent.strip():
            raise ValueError("A descriptive SEC user_agent is required")

        response = requests.get(
            _COMPANY_FACTS_URL.format(cik=str(cik).zfill(10)),
            headers={"User-Agent": user_agent},
            timeout=30,
        )
        response.raise_for_status()
        company_facts = response.json()["facts"]["us-gaap"]
        retrieved_at = pd.Timestamp.now(tz="UTC")
        fact_units = fact_units or {}
        non_additive_series = non_additive_series or set()
        instant_series = instant_series or set()
        rows = []

        for series_id, candidate_tags in fact_mapping.items():
            expected_unit = fact_units.get(series_id, "USD")
            fact = next(
                (
                    (company_facts[tag], expected_unit)
                    for tag in candidate_tags
                    if tag in company_facts
                    and expected_unit in company_facts[tag].get("units", {})
                ),
                None,
            )
            if fact is None:
                raise ValueError(
                    f"No supported SEC fact found for {series_id}: "
                    f"{candidate_tags} with unit {expected_unit}"
                )

            selected_fact, unit = fact
            quarterly_facts = _quarterly_facts(
                selected_fact["units"][unit],
                additive=series_id not in non_additive_series,
                instant=series_id in instant_series,
            )
            for observation in quarterly_facts:
                if not observation.get("end") or not observation.get("filed"):
                    continue

                period_end = _as_date(observation["end"])
                # SEC Company Facts provides filing dates, not filing times. A
                # one-day delay avoids treating a same-day filing as available
                # before its intraday publication time.
                available_date = _as_date(observation["filed"]) + timedelta(days=1)
                if not start <= period_end <= end:
                    continue

                rows.append(
                    {
                        "series_id": series_id,
                        "entity": ticker.upper(),
                        "observation_date": period_end,
                        "period_end_date": period_end,
                        "available_date": available_date,
                        "value": observation["val"],
                        "unit": unit,
                        "frequency": "quarterly",
                        "source": f"SEC Company Facts:{ticker.upper()}",
                        "retrieved_at": retrieved_at,
                    }
                )

        data = pd.DataFrame(rows, columns=COMMON_COLUMNS)
        if not data.empty:
            data = (
                data.sort_values(["series_id", "entity", "observation_date", "available_date"])
                .drop_duplicates(
                    subset=["series_id", "entity", "observation_date", "available_date"],
                    keep="last",
                )
                .reset_index(drop=True)
            )
        self.validate(data)
        return data


def _as_date(value) -> date:
    return pd.Timestamp(value).date()


def _quarterly_facts(
    facts: list[dict], *, additive: bool = True, instant: bool = False
) -> list[dict]:
    """Return standalone quarter values from SEC quarterly, YTD, and annual facts."""
    if instant:
        return sorted(
            (fact for fact in facts if fact.get("end") and fact.get("filed")),
            key=lambda fact: (_as_date(fact["end"]), _as_date(fact["filed"])),
        )

    filed_facts = [
        fact
        for fact in facts
        if fact.get("start") and fact.get("end") and fact.get("filed")
    ]
    direct = []
    cumulative = []
    for fact in filed_facts:
        duration = (_as_date(fact["end"]) - _as_date(fact["start"])).days
        if _QUARTER_MIN_DAYS <= duration <= _QUARTER_MAX_DAYS:
            direct.append(fact)
        elif additive and (
            150 <= duration <= 210
            or 230 <= duration <= 300
            or 320 <= duration <= 380
        ):
            cumulative.append(fact)

    # Prefer the source-reported standalone quarter where available. Otherwise,
    # derive a standalone quarter from the current cumulative fact and the
    # latest earlier cumulative fact with the same fiscal-year start.
    by_filing_period = {
        (_as_date(fact["end"]), _as_date(fact["filed"])): fact for fact in direct
    }
    for current in cumulative:
        current_start = _as_date(current["start"])
        current_end = _as_date(current["end"])
        current_filed = _as_date(current["filed"])
        filing_period = (current_end, current_filed)
        if filing_period in by_filing_period:
            continue

        prior_facts = [
            fact
            for fact in filed_facts
            if _as_date(fact["start"]) == current_start
            and _as_date(fact["end"]) < current_end
            and _as_date(fact["filed"]) <= current_filed
        ]
        if not prior_facts:
            continue
        prior = max(
            prior_facts,
            key=lambda fact: (_as_date(fact["end"]), _as_date(fact["filed"])),
        )
        by_filing_period[filing_period] = {
            **current,
            "val": current["val"] - prior["val"],
        }

    return sorted(
        by_filing_period.values(),
        key=lambda fact: (_as_date(fact["end"]), _as_date(fact["filed"])),
    )
