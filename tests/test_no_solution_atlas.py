from __future__ import annotations

from diagnostics.no_solution_atlas import build_no_solution_atlas, classify_mechanism
from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from shams_io.run_artifact import build_run_artifact
from ui.export_bundle import build_export_bundle


def test_classify_mechanism_transport() -> None:
    assert classify_mechanism("Transport spread") == "TRANSPORT"


def test_no_solution_atlas_infeasible() -> None:
    out = {
        "transport_spread_ratio_v396": 5.0,
        "transport_spread_max_v396": 1.5,
    }
    atlas = build_no_solution_atlas(out)
    assert atlas["verdict"] == "INFEASIBLE"
    assert atlas["schema"] == "no_solution_atlas.v1"
    assert atlas["dominant_mechanism"] in ("TRANSPORT", "GENERAL")


def test_no_solution_atlas_feasible() -> None:
    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    atlas = build_no_solution_atlas(out)
    assert atlas["verdict"] == "FEASIBLE"


def test_run_artifact_stamps_atlas_when_hard_infeasible() -> None:
    """Independence 1.1: hard-infeasible run artifacts carry no_solution_atlas.v1."""
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    # Constraint JSON with a failed hard constraint → feasible_hard False.
    cons = [
        {
            "name": "Transport spread",
            "value": 5.0,
            "limit": 1.5,
            "sense": "<=",
            "passed": False,
            "severity": "hard",
            "margin_frac": -2.0,
            "units": "",
            "group": "transport",
        }
    ]
    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={
            "transport_spread_ratio_v396": 5.0,
            "transport_spread_max_v396": 1.5,
            "Q": 1.0,
        },
        constraints=cons,
        meta={"label": "atlas_infeas", "mode": "point"},
    )
    assert art["kpis"]["feasible_hard"] is False
    assert "no_solution_atlas" in art
    atlas = art["no_solution_atlas"]
    assert atlas["schema"] == "no_solution_atlas.v1"
    assert atlas["verdict"] == "INFEASIBLE"
    assert "dominant_mechanism" in atlas


def test_run_artifact_omits_atlas_when_hard_feasible() -> None:
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    cons = [
        {
            "name": "beta_N",
            "value": 1.0,
            "limit": 3.0,
            "sense": "<=",
            "passed": True,
            "severity": "hard",
            "margin_frac": 0.5,
            "units": "",
            "group": "plasma",
        }
    ]
    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={"Q": 5.0, "beta_N": 1.0},
        constraints=cons,
        meta={"label": "atlas_feas", "mode": "point"},
    )
    assert art["kpis"]["feasible_hard"] is True
    assert "no_solution_atlas" not in art


def test_export_bundle_includes_atlas_when_infeasible() -> None:
    out = {
        "transport_spread_ratio_v396": 5.0,
        "transport_spread_max_v396": 1.5,
    }
    bundle = build_export_bundle(deck="Point Designer", outputs=out)
    assert bundle["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"
    assert bundle["no_solution_atlas"]["verdict"] == "INFEASIBLE"
    assert "manifest_sha256" in bundle


def test_export_bundle_omits_atlas_when_feasible() -> None:
    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    bundle = build_export_bundle(deck="Point Designer", outputs=out)
    assert "no_solution_atlas" not in bundle
