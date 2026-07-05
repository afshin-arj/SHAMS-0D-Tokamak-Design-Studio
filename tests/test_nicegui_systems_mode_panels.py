"""Import smoke for all Systems Mode parity panels."""

from __future__ import annotations


def test_systems_mode_panel_imports() -> None:
    from ui_nicegui.decks.systems_mode import render_systems_mode  # noqa: F401
    from ui_nicegui.decks.systems_mode import (  # noqa: F401
        assistant_ui,
        atlas_ui,
        audit_ui,
        base_design_ui,
        certification_ui,
        chronicle_ui,
        diagnostics_ui,
        explore_ui,
        export_ui,
        frontier_ui,
        precheck_ui,
        recover_ui,
        reproduce_ui,
        setup,
        solve_ui,
        stories_ui,
        timeline_ui,
        tools_ui,
        verdict,
    )
    from ui_nicegui.lib.systems_cert_registry import CERT_REGISTRY

    assert len(CERT_REGISTRY) >= 15
