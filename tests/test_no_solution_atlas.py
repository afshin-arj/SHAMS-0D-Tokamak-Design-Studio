from __future__ import annotations

from diagnostics.no_solution_atlas import build_no_solution_atlas, classify_mechanism


def test_classify_mechanism_transport() -> None:
    assert classify_mechanism("Transport spread (v396)") == "TRANSPORT"


def test_no_solution_atlas_infeasible() -> None:
    out = {
        "transport_spread_ratio_v396": 5.0,
        "transport_spread_max_v396": 1.5,
    }
    atlas = build_no_solution_atlas(out)
    assert atlas["verdict"] == "INFEASIBLE"
    assert atlas["dominant_mechanism"] in ("TRANSPORT", "GENERAL")


def test_no_solution_atlas_feasible() -> None:
    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    atlas = build_no_solution_atlas(out)
    assert atlas["verdict"] == "FEASIBLE"
