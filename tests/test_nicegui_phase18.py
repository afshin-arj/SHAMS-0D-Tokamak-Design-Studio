"""Phase 18: Control Room Artifacts + Chronicle + launch helpers."""
from __future__ import annotations

from ui_nicegui.decks import control_room as cr_pkg
from ui_nicegui.decks.control_room import artifacts, chronicle, render_control_room
from ui_nicegui.lib.control_room_helpers import ARTIFACT_TABS, CHRONICLE_TABS, CR_SECTIONS
from ui_nicegui.lib.cr_artifacts_helpers import artifact_summary, collect_session_artifacts
from ui_nicegui.lib.cr_chronicle_helpers import list_variable_registry_keys
from ui_nicegui.session import DesignSession


def test_phase18_control_room_sections() -> None:
    assert "Artifacts" in CR_SECTIONS
    assert "Chronicle" in CR_SECTIONS
    assert len(ARTIFACT_TABS) >= 3
    assert len(CHRONICLE_TABS) >= 6


def test_phase18_renderers_import() -> None:
    assert callable(render_control_room)
    assert callable(artifacts.render_artifacts)
    assert callable(chronicle.render_chronicle)


def test_phase18_all_sections_ported() -> None:
    assert set(CR_SECTIONS) == cr_pkg._PORTED


def test_artifact_summary_smoke() -> None:
    art = {"kind": "shams_run_artifact", "inputs": {}, "constraint_ledger": {"entries": []}}
    s = artifact_summary(art)
    assert "schema" in s


def test_collect_session_artifacts_empty() -> None:
    s = DesignSession()
    assert collect_session_artifacts(s) == []


def test_variable_registry_keys() -> None:
    keys = list_variable_registry_keys()
    assert isinstance(keys, list)


def test_launch_module_import() -> None:
    import ui_nicegui.launch as launch

    assert callable(launch.main)


def test_helm_console_imports() -> None:
    from ui_nicegui.components.helm_console import render_helm_console

    assert callable(render_helm_console)
