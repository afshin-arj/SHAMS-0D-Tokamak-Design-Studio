"""Tests for machine-build / radial closure authority v412."""
from __future__ import annotations

import math

from analysis.machine_build_authority_v412 import evaluate_machine_build_authority_v412


def test_v412_disabled_returns_empty() -> None:
    class Inp:
        include_machine_build_authority_v412 = False

    r = evaluate_machine_build_authority_v412({}, Inp())
    assert r == {}
    assert "machine_v412_system_margin" not in r


def test_v412_computes_layer_ledger_and_closure() -> None:
    class Inp:
        include_machine_build_authority_v412 = True
        R0_m = 6.0
        a_m = 2.0
        delta = 0.3
        t_gap_m = 0.05
        t_gap_min_m = 0.02
        gap_to_cryostat_m_v392 = 0.8
        fragile_margin_frac = 0.05
        machine_build_closure_margin_min_v412 = float("nan")
        machine_build_inboard_margin_min_m_v412 = float("nan")
        machine_build_gap_min_m_v412 = float("nan")
        machine_build_layer_surplus_min_m_v412 = float("nan")

    out = {
        "inboard_space_m": 4.6,
        "inboard_build_total_m": 1.65,
        "inboard_margin_m": 2.95,
        "spent_noncoil_m": 1.3,
        "R_coil_inner_m": 3.3,
        "radial_build_ok": 1.0,
        "stack_ok": 1.0,
        "radial_stack": [
            {"name": "First wall", "thickness_m": 0.02, "min_thickness_m": 0.01, "kind": "fw"},
            {"name": "Blanket", "thickness_m": 0.50, "min_thickness_m": 0.40, "kind": "blanket"},
            {"name": "Shield", "thickness_m": 0.70, "min_thickness_m": 0.50, "kind": "shield"},
            {"name": "Vacuum vessel", "thickness_m": 0.05, "min_thickness_m": 0.03, "kind": "vessel"},
            {"name": "Gap", "thickness_m": 0.05, "min_thickness_m": 0.02, "kind": "gap"},
            {"name": "TF winding pack", "thickness_m": 0.20, "min_thickness_m": 0.10, "kind": "coil"},
            {"name": "TF structure", "thickness_m": 0.15, "min_thickness_m": 0.10, "kind": "structure"},
        ],
        "fragile_margin_frac": 0.05,
    }

    r = evaluate_machine_build_authority_v412(out, Inp())
    assert r["machine_v412_enabled"] is True
    assert r["machine_v412_screening_tier"] == "proxy"
    assert r["machine_v412_overlay_version"].startswith("v412")
    assert r["machine_v412_authority_id"] == "machine_build_authority_v412"
    assert r["machine_v412_n_layers"] == 7
    assert isinstance(r["machine_v412_layer_ledger"], list)
    assert len(r["machine_v412_layer_ledger"]) == 7
    assert r["machine_v412_layers_ok"] is True
    assert r["machine_v412_closure_ok"] is True

    m = float(r["machine_v412_system_margin"])
    assert math.isfinite(m)
    assert r["machine_v412_system_tier"] in {"comfortable", "near_limit", "deficit", "unknown"}
    assert r["machine_v412_dominant_aspect"]
    assert abs(float(r["machine_v412_inboard_margin_m"]) - 2.95) < 1e-9
    assert math.isfinite(float(r["machine_v412_outboard_R_outer_m"]))
    assert "PROXY" in r["machine_v412_provenance"].upper() or "proxy" in r["machine_v412_provenance"].lower()
    assert "PROCESS MFILE" in r["machine_v412_provenance"] or "not PROCESS" in r["machine_v412_provenance"]
    assert "m" in r["machine_v412_units"]["lengths"]


def test_v412_deterministic() -> None:
    class Inp:
        include_machine_build_authority_v412 = True
        R0_m = 3.0
        a_m = 1.0
        delta = 0.0

    out = {
        "inboard_space_m": 2.0,
        "inboard_build_total_m": 1.5,
        "inboard_margin_m": 0.5,
        "R_coil_inner_m": 0.8,
        "radial_build_ok": 1.0,
        "stack_ok": 1.0,
        "radial_stack": [
            {"name": "Gap", "thickness_m": 0.03, "min_thickness_m": 0.01, "kind": "gap"},
            {"name": "Blanket", "thickness_m": 0.5, "min_thickness_m": 0.4, "kind": "blanket"},
        ],
        "fragile_margin_frac": 0.05,
    }
    a = evaluate_machine_build_authority_v412(out, Inp())
    b = evaluate_machine_build_authority_v412(out, Inp())
    assert a["machine_v412_system_margin"] == b["machine_v412_system_margin"]
    assert a["machine_v412_dominant_aspect"] == b["machine_v412_dominant_aspect"]
    assert a["machine_v412_inboard_closure_margin"] == b["machine_v412_inboard_closure_margin"]


def test_v412_deficit_when_inboard_negative() -> None:
    class Inp:
        include_machine_build_authority_v412 = True
        R0_m = 2.0
        a_m = 1.0

    out = {
        "inboard_space_m": 1.0,
        "inboard_build_total_m": 1.5,
        "inboard_margin_m": -0.5,
        "R_coil_inner_m": -0.2,
        "radial_build_ok": 0.0,
        "stack_ok": 0.0,
        "radial_stack": [
            {"name": "Blanket", "thickness_m": 1.0, "min_thickness_m": 0.5, "kind": "blanket"},
            {"name": "Gap", "thickness_m": 0.5, "min_thickness_m": 0.0, "kind": "gap"},
        ],
        "fragile_margin_frac": 0.05,
    }
    r = evaluate_machine_build_authority_v412(out, Inp())
    assert r["machine_v412_closure_ok"] is False
    assert float(r["machine_v412_system_margin"]) < 0.0
    assert r["machine_v412_system_tier"] == "deficit"


def test_v412_optional_cap_echoed() -> None:
    class Inp:
        include_machine_build_authority_v412 = True
        machine_build_closure_margin_min_v412 = 0.05
        machine_build_inboard_margin_min_m_v412 = 0.1
        machine_build_gap_min_m_v412 = 0.02
        machine_build_layer_surplus_min_m_v412 = float("nan")

    out = {
        "inboard_space_m": 3.0,
        "inboard_build_total_m": 1.0,
        "inboard_margin_m": 2.0,
        "R_coil_inner_m": 2.0,
        "radial_stack": [
            {"name": "Gap", "thickness_m": 0.05, "min_thickness_m": 0.0, "kind": "gap"},
        ],
        "fragile_margin_frac": 0.05,
    }
    r = evaluate_machine_build_authority_v412(out, Inp())
    assert float(r["machine_build_closure_margin_min_v412"]) == 0.05
    assert float(r["machine_build_inboard_margin_min_m_v412"]) == 0.1
    assert float(r["machine_build_gap_min_m_v412"]) == 0.02
    # Cap forces gap aspect: 0.05/0.02 - 1 = 1.5
    assert abs(float(r["machine_v412_gap_clearance_margin"]) - 1.5) < 1e-9


def test_v412_ui_summary_helper() -> None:
    from ui_nicegui.lib.pd_parity_helpers import machine_v412_summary

    assert machine_v412_summary({"machine_v412_enabled": False}) is None
    s = machine_v412_summary(
        {
            "machine_v412_enabled": True,
            "machine_v412_screening_tier": "proxy",
            "machine_v412_system_margin": 0.2,
            "machine_v412_system_tier": "comfortable",
            "machine_v412_dominant_aspect": "inboard_closure",
            "machine_v412_dominant_aspect_margin": 0.2,
            "machine_v412_inboard_margin_m": 0.5,
            "machine_v412_closure_ok": True,
            "machine_v412_n_layers": 7,
            "machine_v412_outboard_R_outer_m": 10.0,
            "machine_v412_provenance": "proxy",
            "machine_v412_narrative": "test",
            "machine_v412_inboard_closure_margin": 0.2,
            "machine_v412_coil_bore_margin": 0.3,
            "machine_v412_gap_clearance_margin": 0.4,
            "machine_v412_layer_mins_margin": 0.5,
            "machine_v412_layer_ledger": [],
        }
    )
    assert s is not None
    assert s["dominant_aspect"] == "inboard_closure"
    assert s["screening_tier"] == "proxy"


def _base_inp(**kwargs):
    from src.schema.inputs import PointInputs
    from dataclasses import replace

    base = PointInputs(
        R0_m=1.85,
        a_m=0.6,
        kappa=1.75,
        Bt_T=12.0,
        Ip_MA=8.0,
        Ti_keV=10.0,
        fG=0.85,
        Paux_MW=25.0,
    )
    return replace(base, **kwargs) if kwargs else base


def test_v412_hot_ion_flag_off_no_keys() -> None:
    """Flag OFF must not stamp v412 keys into evaluator outputs (L0 frozen)."""
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_machine_build_authority_v412=False)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("machine_v412_enabled", False)) is False
    assert "machine_v412_system_margin" not in out
    # L0 radial keys still present
    assert "inboard_margin_m" in out


def test_v412_hot_ion_flag_on_stamps_ledger() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_machine_build_authority_v412=True)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("machine_v412_enabled")) is True
    m = float(out["machine_v412_system_margin"])
    assert out.get("machine_v412_screening_tier") == "proxy"
    assert isinstance(out.get("machine_v412_layer_ledger"), list)
    assert math.isfinite(m)
    assert math.isfinite(float(out["machine_v412_outboard_R_outer_m"]))


def test_v412_flag_off_preserves_l0_numerics_vs_on() -> None:
    """Enabling v412 must not change core L0 radial / plasma numerics."""
    from src.evaluator.core import Evaluator

    off = dict(Evaluator().evaluate(_base_inp(include_machine_build_authority_v412=False)).out or {})
    on = dict(Evaluator().evaluate(_base_inp(include_machine_build_authority_v412=True)).out or {})
    for key in (
        "inboard_margin_m",
        "R_coil_inner_m",
        "B_peak_T",
        "Q",
        "P_fus_MW",
        "radial_build_ok",
    ):
        if key not in off:
            continue
        a, b = off[key], on[key]
        if isinstance(a, float) and isinstance(b, float):
            if math.isnan(a) and math.isnan(b):
                continue
            assert a == b, f"L0 drift on {key}: {a} vs {b}"
        else:
            assert a == b, f"L0 drift on {key}"
