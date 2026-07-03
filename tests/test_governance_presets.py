from __future__ import annotations

from schema.governance_presets import (
    apply_governance_preset,
    is_reactor_intent,
    tritium_tight_closure_default,
)


def test_reactor_tritium_default_on() -> None:
    assert tritium_tight_closure_default("Power Reactor (net-electric)") is True
    assert tritium_tight_closure_default("Experimental Device (research)") is False


def test_apply_governance_preset_reactor() -> None:
    fields: dict = {}
    apply_governance_preset(fields, design_intent="Power Reactor (net-electric)")
    assert fields["include_tritium_tight_closure"] is True
    assert fields["T_in_vessel_max_kg"] == 4.0


def test_is_reactor_intent() -> None:
    assert is_reactor_intent("Power Reactor (net-electric)")
    assert not is_reactor_intent("Experimental Device (research)")
