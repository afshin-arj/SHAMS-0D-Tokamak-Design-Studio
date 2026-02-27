from __future__ import annotations

import json

from src.extopt.frontier_intake_v406 import (
    ParetoObjective,
    parse_candidate_set_csv,
    parse_candidate_set_json,
    pareto_front,
)


def test_parse_candidate_set_json_minimal():
    d = {
        "schema_version": "shams.extopt_candidate_set.v1",
        "candidates": [
            {"id": "a", "overrides": {"R0_m": 6.2, "a_m": 2.0}},
            {"id": "b", "R0_m": 6.0, "a_m": 1.9},
        ],
    }
    cs = parse_candidate_set_json(d)
    assert cs.schema_version == "shams.extopt_candidate_set.v1"
    assert len(cs.candidates) == 2
    assert cs.candidates[0]["id"] == "a"
    assert "R0_m" in cs.candidates[0]["overrides"]


def test_parse_candidate_set_csv_basic():
    csv_bytes = b"id,R0_m,a_m\nA,6.2,2.0\nB,6.0,1.9\n"
    cs = parse_candidate_set_csv(csv_bytes)
    assert cs.schema_version.startswith("shams.extopt_candidate_set.csv")
    assert len(cs.candidates) == 2
    assert cs.candidates[0]["id"] == "A"
    assert cs.candidates[1]["overrides"]["a_m"] == 1.9


def test_pareto_front_minimization():
    rows = [
        {"id": "a", "f": 1.0, "g": 2.0},
        {"id": "b", "f": 1.5, "g": 1.0},
        {"id": "c", "f": 2.0, "g": 3.0},  # dominated by a
    ]
    front = pareto_front(rows, [ParetoObjective(key="f", sense="min"), ParetoObjective(key="g", sense="min")])
    ids = [r["id"] for r in front]
    assert "c" not in ids
    assert set(ids) == {"a", "b"}
