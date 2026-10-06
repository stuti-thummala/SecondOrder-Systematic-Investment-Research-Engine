from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_yaml(relative_path: str) -> dict:
    with (PROJECT_ROOT / relative_path).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_configured_universes_match_day_one_scope():
    companies = _read_yaml("config/companies.yaml")
    research = _read_yaml("config/research.yaml")

    assert research["core_universe"] == list(companies["core_companies"])
    assert research["capex_drivers"] == list(companies["capex_drivers"])
    assert len(research["core_universe"]) == 3
    assert len(research["capex_drivers"]) == 3


def test_initial_hypotheses_and_causal_graph_are_machine_readable():
    hypotheses = _read_yaml("research/hypotheses.yaml")["hypotheses"]
    graph = _read_yaml("research/causal_graph.yaml")
    edge_statuses = {edge["status"] for edge in graph["edges"]}

    assert [hypothesis["id"] for hypothesis in hypotheses] == [
        f"H-{number:03}"
        for number in range(1, 9)
    ]
    assert len(graph["edges"]) >= 3
    assert edge_statuses == {"untested"}
    assert all(edge["economic_rationale"] for edge in graph["edges"])


def test_data_dictionary_includes_point_in_time_observation_schema():
    fields = _read_yaml("data/metadata/data_dictionary.yaml")["observation_schema"]

    assert {
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
    } == set(fields)
