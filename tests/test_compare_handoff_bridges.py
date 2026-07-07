"""Compare inbound handoffs and Control Room bridge."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.lib.compare_helpers import (
    bridge_compare_slots_to_cr,
    bridge_cr_to_compare_slots,
    normalize_compare_artifact,
    send_row_to_compare_slot,
    store_compare_slot,
)
from ui_nicegui.session import DesignSession


def test_store_compare_slot_both() -> None:
    s = DesignSession()
    art_a = {"outputs": {"Q": 1.0}, "inputs": {"R0_m": 1.8}, "label": "test A"}
    art_b = {"outputs": {"Q": 2.0}, "inputs": {"R0_m": 2.0}, "label": "test B"}
    store_compare_slot(s, art_a, "A", label="A")
    store_compare_slot(s, art_b, "B", label="B")
    assert isinstance(s.cmp_slot_a, dict)
    assert isinstance(s.cmp_slot_b, dict)
    assert s.cmp_slot_a_meta.get("label") == "A"


def test_bridge_cr_to_compare_and_back() -> None:
    s = DesignSession()
    s.cr_scenario_base = {"outputs": {"Q_DT_eqv": 5.0}, "inputs": {"R0_m": 1.7}}
    s.cr_scenario_variant = {"outputs": {"Q_DT_eqv": 6.0}, "inputs": {"R0_m": 1.9}}
    ok_a, ok_b = bridge_cr_to_compare_slots(s)
    assert ok_a and ok_b
    assert s.cmp_slot_a is not None
    assert s.cmp_slot_b is not None

    s.cr_scenario_base = None
    s.cr_scenario_variant = None
    back_a, back_b = bridge_compare_slots_to_cr(s)
    assert back_a and back_b
    assert isinstance(s.cr_scenario_base, dict)
    assert isinstance(s.cr_scenario_variant, dict)
    assert normalize_compare_artifact(s.cr_scenario_base).get("outputs", {}).get("Q_DT_eqv") == 5.0


def test_send_row_to_compare_slot_smoke() -> None:
    s = DesignSession()
    row = {"R0_m": float(s.inputs.get("R0_m", 1.85))}
    art = send_row_to_compare_slot(s, row, "A", label="test row")
    assert isinstance(art, dict)
    assert isinstance(s.cmp_slot_a, dict)


def test_legacy_streamlit_trade_study_removed() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "ui" / "trade_study_studio.py").exists()
    assert not (root / "ui" / "decks" / "trade_study_studio.py").exists()
