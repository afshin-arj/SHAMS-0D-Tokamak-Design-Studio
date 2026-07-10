"""System Suite deep-review regression tests — UX helpers and overlay semantics."""

from __future__ import annotations

import math

from tools.system_suite import lifetime_and_fuel_overlay, trajectory_diagnostics_client
from ui_nicegui.lib.suite_helpers import (
    SUITE_RUNLOCK_OWNER,
    authority_version_badges,
    envelope_posture_summary,
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
    assert "v400 magnets" in badges
    assert "v401 neutronics" in badges


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
