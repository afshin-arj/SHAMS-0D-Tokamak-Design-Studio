"""System Suite deep-review regression tests — UX helpers and overlay semantics."""

from __future__ import annotations

import math

from tools.system_suite import lifetime_and_fuel_overlay, trajectory_diagnostics_client
from ui_nicegui.lib.suite_helpers import (
    SUITE_RUNLOCK_OWNER,
    authority_version_badges,
    bridge_campaign_to_pareto,
    campaign_results_to_atlas_records,
    campaign_to_concept_family_yaml,
    envelope_posture_summary,
    impurity_radiation_summary,
    lifetime_binding_summary,
)
from ui_nicegui.lib.verdict_core import subsystem_status
from ui_nicegui.session import DesignSession


def test_subsystem_status_warn_for_diagnostic_fail() -> None:
    out = {"constraints_dummy": True}
    status = subsystem_status(out)
    assert "magnets" in status


def test_lifetime_binding_summary_negative_margin() -> None:
    class LR:
        fw_dpa_margin = -0.1
        cycles_margin = 0.5
        tbr_margin = -0.02

    s = lifetime_binding_summary(LR())
    assert s["posture"] == "LIFETIME BINDING"
    assert "FW dpa" in s["binding"]
    assert "TBR" in s["binding"]


def test_trajectory_power_incomplete_flag() -> None:
    tr = trajectory_diagnostics_client({"P_e_net_MW": float("nan"), "P_recirc_MW": 10.0})
    assert tr.meta.get("power_incomplete") is True


def test_authority_version_badges_from_enabled_flags() -> None:
    badges = authority_version_badges({"magnet_v400_enabled": True, "nm_authority_v401_enabled": True})
    assert "Magnet technology" in badges
    assert "Neutronics" in badges
    # User-facing badges must not carry internal overlay version tags.
    assert not any("v4" in b.lower() for b in badges)


def test_envelope_posture_summary_campaign() -> None:
    s = DesignSession()
    s.suite_campaign_summary = {"n_feasible": 3, "n_total": 10}
    text = envelope_posture_summary(s)
    assert "Campaign: 3/10" in text


def test_suite_runlock_owner_constant() -> None:
    assert SUITE_RUNLOCK_OWNER == "SystemSuite"


def test_lifetime_overlay_finite_margins() -> None:
    rep = lifetime_and_fuel_overlay(
        {"fw_dpa_per_year": 5.0, "fw_dpa_max_per_year": 10.0, "TBR": 1.05, "TBR_min": 1.0},
        {},
    )
    assert math.isfinite(rep.fw_dpa_margin)
    assert math.isfinite(rep.tbr_margin)


def test_impurity_radiation_summary_binding() -> None:
    s = impurity_radiation_summary({
        "Prad_core_MW": 20.0,
        "P_SOL_MW": 50.0,
        "q_div_MW_m2": 12.0,
        "q_div_max_MW_m2": 10.0,
        "detachment_f_z_required": 1e-2,
        "detachment_fz_max": 5e-3,
        "include_radiation": True,
        "impurity_partition_core": 0.2,
        "impurity_partition_sol": 0.3,
    })
    assert s["posture"] == "EXHAUST BINDING"
    assert "q_div" in s["binding"]
    assert "f_z" in s["binding"]
    assert s["radiation_enabled"] is True


def test_campaign_to_concept_family_yaml() -> None:
    ybytes, name = campaign_to_concept_family_yaml(
        {"R0_m": 6.0, "Bt_T": 5.0},
        [{"cid": "c0", "R0_m": 6.2}, {"cid": "c1", "Bt_T": 5.5}],
        name="test_family",
    )
    assert name == "test_family.yaml"
    text = ybytes.decode("utf-8")
    assert "concept_family.v1" in text
    assert "c0" in text


def test_campaign_results_to_atlas_and_bridge() -> None:
    rows = [
        {
            "cid": "a",
            "inputs": {"R0_m": 6.0},
            "feasible_hard": True,
            "dominant_mechanism": "exhaust",
            "artifact": {"outputs": {"P_e_net_MW": 100.0, "plasma_regime": "H"}, "kpis": {}},
        }
    ]
    recs = campaign_results_to_atlas_records(None, rows)
    assert len(recs) == 1
    assert recs[0]["robustness_class"] == "robust"
    assert recs[0].get("P_e_net_MW") == 100.0

    s = DesignSession()
    s.suite_campaign_results_preview = rows
    s.suite_campaign_candidates = [{"cid": "a", "R0_m": 6.1}]
    s.pd_last_artifact = {"inputs": {"R0_m": 6.0, "Bt_T": 5.0}, "outputs": {"Q": 1.0}}
    meta = bridge_campaign_to_pareto(s)
    assert meta["n_records"] == 1
    assert meta["n_candidates"] == 1
    assert isinstance(s.extopt_suite_upload_bytes, (bytes, bytearray))
    assert len(s.regime_atlas_records or []) == 1
    assert "System Suite" in str(meta.get("source", ""))


def test_legacy_streamlit_system_suite_removed() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert not (root / "ui" / "decks" / "system_suite.py").exists()
    assert not (root / "ui" / "decks" / "system_suite_hooks.py").exists()
