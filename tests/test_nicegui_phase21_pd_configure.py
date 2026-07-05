"""Phase 21: Point Designer Configure parity — imports and build_point_inputs smoke."""

from __future__ import annotations

from ui_nicegui.decks.point_designer.configure_engineering import render_engineering_plant
from ui_nicegui.decks.point_designer.configure_physics import render_model_options, render_power_composition
from ui_nicegui.lib.pd_overlay_catalog import ALL_OVERLAY_KEYS, seed_overlay_defaults
from ui_nicegui.lib.pd_overlay_knobs import OVERLAY_NUMERIC_PANELS
from ui_nicegui.lib.pd_panel_labels import CONFIGURE_SECTION_ORDER
from ui_nicegui.lib.point_inputs_builder import build_point_inputs
from ui_nicegui.session import DesignSession


def test_phase21_configure_physics_imports() -> None:
    assert callable(render_model_options)
    assert callable(render_power_composition)


def test_phase21_configure_engineering_import() -> None:
    assert callable(render_engineering_plant)


def test_phase21_configure_section_order() -> None:
    assert "model_options" in CONFIGURE_SECTION_ORDER
    assert "power_composition" in CONFIGURE_SECTION_ORDER
    assert "engineering_plant" in CONFIGURE_SECTION_ORDER
    assert CONFIGURE_SECTION_ORDER.index("model_options") < CONFIGURE_SECTION_ORDER.index("operating_targets")


def test_phase21_overlay_catalog_keys() -> None:
    assert "include_damage_strength_coupling_v393" in ALL_OVERLAY_KEYS
    assert "cd_mix_enable" in ALL_OVERLAY_KEYS
    assert "use_lambda_q" not in ALL_OVERLAY_KEYS  # PointInputs field, not overlay toggle


def test_phase21_overlay_numeric_panels_expanded() -> None:
    flags = [p[0] for p in OVERLAY_NUMERIC_PANELS]
    assert "include_profile_family_v358" in flags
    assert "include_neutronics_materials_coupling_v372" in flags
    assert "include_damage_strength_coupling_v393" in flags
    assert "cd_mix_enable" in flags


def test_phase21_build_point_inputs_smoke() -> None:
    s = DesignSession()
    seed_overlay_defaults(s.overlay)
    s.overlay["include_transport_envelope_v396"] = True
    s.overlay["include_radiation"] = True
    s.inputs["use_lambda_q"] = True
    s.inputs["confinement_scaling"] = "ITER89P"
    s.knobs["transport_spread_max_v396"] = 0.3
    s.knobs["pd_confidence"] = "Nominal"
    s.knobs["_warn_frac_max"] = 0.90
    s.knobs["_subsystem_enabled"] = {"build": True, "magnets": True}
    inp = build_point_inputs(s)
    assert str(getattr(inp, "confinement_scaling", "")) == "ITER89P"
    assert bool(getattr(inp, "include_transport_envelope_v396", False))
    assert bool(getattr(inp, "use_lambda_q", False))
    assert bool(getattr(inp, "include_radiation", False))


def test_phase21_build_point_inputs_overlay_priority() -> None:
    s = DesignSession()
    s.inputs["include_hmode_physics"] = False
    s.overlay["include_hmode_physics"] = True
    inp = build_point_inputs(s)
    assert bool(getattr(inp, "include_hmode_physics", False)) is True


def test_phase21_configure_render_import() -> None:
    from ui_nicegui.decks.point_designer.configure import render_configure

    assert callable(render_configure)
