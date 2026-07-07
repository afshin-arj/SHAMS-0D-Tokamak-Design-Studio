"""Forge cross-deck handoffs."""
from __future__ import annotations

from ui_nicegui.lib.forge_handoff_helpers import (
    archive_row_handoff_payload,
    handoff_archive_row_to_scan_lab,
    handoff_archive_row_to_systems_mode,
)
from ui_nicegui.lib.forge_instrument_engine import filter_archive
from ui_nicegui.session import DesignSession


def _sample_run() -> dict:
    return {
        "archive": [
            {
                "feasible": True,
                "inputs": {"R0_m": 2.1, "Bt_T": 6.0, "Ip_MA": 8.0},
                "outputs": {"P_e_net_MW": 120.0, "Q_DT_eqv": 3.0},
                "cost": {"COE_proxy": 80.0},
                "min_signed_margin": 0.05,
                "_score": 4.0,
            },
            {
                "feasible": True,
                "inputs": {"R0_m": 2.5, "Bt_T": 5.5},
                "cost": {"COE_proxy": 200.0},
                "min_signed_margin": 0.02,
                "_score": 2.0,
            },
        ],
        "intent": "Reactor",
    }


def test_archive_row_handoff_payload() -> None:
    payload = archive_row_handoff_payload(_sample_run(), 0)
    assert payload.get("R0_m") == 2.1
    assert payload.get("P_e_net_MW") == 120.0


def test_filter_archive_max_coe() -> None:
    archive = _sample_run()["archive"]
    filtered = filter_archive(archive, max_coe=100.0)
    assert len(filtered) == 1


def test_handoff_scan_and_systems_queue() -> None:
    s = DesignSession()
    s.forge_mf_last_bounds = {"R0_m": [1.8, 2.5], "Bt_T": [4.0, 7.0]}
    s.forge_lens_contract = {"objectives": [{"key": "P_e_net_MW", "sense": "max"}]}
    run = _sample_run()
    focus = handoff_archive_row_to_scan_lab(s, run, 0)
    assert focus.get("source") == "Reactor Design Forge"
    assert s.scan_probe_focus is not None
    handoff_archive_row_to_systems_mode(s, run, 0)
    assert isinstance(s.systems_mode_queue, list) and s.systems_mode_queue
