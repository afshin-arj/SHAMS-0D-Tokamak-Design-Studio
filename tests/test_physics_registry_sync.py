from __future__ import annotations

from dataclasses import fields

from models.inputs import PointInputs
from physics.physics_registry import PHYSICS_REGISTRY


def test_physics_registry_covers_core_input_groups() -> None:
    names = {f.name for f in fields(PointInputs)}
    # Registry must document at least power balance + operational limits domains
    assert "power_balance.v1" in PHYSICS_REGISTRY
    assert "operational_limits.v1" in PHYSICS_REGISTRY
    # Core geometry inputs exist in schema
    for key in ("R0_m", "a_m", "Bt_T", "Ip_MA", "Ti_keV", "Paux_MW"):
        assert key in names
