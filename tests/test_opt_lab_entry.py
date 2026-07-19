"""Certified Optimizer 1.1 — Opt Lab entry surface lock tests.

Contract: NiceGUI registers Opt Lab deck with a three-step propose→CCFS path,
honesty phrases (Proposed — SHAMS-certified; never true minimum), routes into
existing Systems Mode / Pareto / Certified Search, no user-facing vNNN labels,
and Streamlit cheap parity. L0 untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_VERSION_TAG = re.compile(r"\bv\d{3}\b", re.IGNORECASE)


def test_opt_lab_deck_registered() -> None:
    from ui_nicegui.decks.labels import DECK_LABELS
    from ui_nicegui.decks import DECK_RENDERERS
    from ui_nicegui.lib.helm_labels import HELM_NAV_GROUPS
    from ui_nicegui.lib.opt_lab_entry import OPT_LAB_DECK

    assert OPT_LAB_DECK == "Opt Lab"
    assert OPT_LAB_DECK in DECK_LABELS
    assert OPT_LAB_DECK in DECK_RENDERERS
    assert callable(DECK_RENDERERS[OPT_LAB_DECK])
    assert DECK_LABELS.index("Systems Mode") < DECK_LABELS.index(OPT_LAB_DECK)
    assert DECK_LABELS.index(OPT_LAB_DECK) < DECK_LABELS.index("Compare")

    seen = [d for _, _, decks in HELM_NAV_GROUPS for d in decks]
    assert set(seen) == set(DECK_LABELS)
    assert OPT_LAB_DECK in seen


def test_opt_lab_three_step_path() -> None:
    from ui_nicegui.lib.opt_lab_entry import OPT_LAB_ROUTES, OPT_LAB_STEPS

    assert len(OPT_LAB_STEPS) == 3
    blob = " ".join(OPT_LAB_STEPS).lower()
    assert "propose" in blob or "pointinputs" in blob.replace(" ", "")
    assert "verified" in blob
    assert "rejected" in blob
    assert "atlas" in blob
    assert "proposed — shams-certified" in blob or "shams-certified" in blob

    decks = {deck for _, deck, _ in OPT_LAB_ROUTES}
    assert decks == {"Systems Mode", "Pareto Lab", "Control Room"}
    hooks = {h for _, _, h in OPT_LAB_ROUTES}
    assert "certified_search" in hooks
    assert "systems_mode" in hooks
    assert "pareto_lab" in hooks


def test_opt_lab_honesty_phrases() -> None:
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_FORBIDDEN_PHRASES,
        OPT_LAB_HONESTY_LINE,
        OPT_LAB_REQUIRED_PHRASES,
        OPT_LAB_TAGLINE,
        opt_lab_user_facing_texts,
    )

    blob = " ".join(opt_lab_user_facing_texts())
    for phrase in OPT_LAB_REQUIRED_PHRASES:
        assert phrase in blob or phrase.lower() in blob.lower(), phrase

    assert "Proposed — SHAMS-certified" in OPT_LAB_HONESTY_LINE
    assert "CCFS" in OPT_LAB_TAGLINE or "CCFS" in blob

    lower = blob.lower()
    for bad in OPT_LAB_FORBIDDEN_PHRASES:
        assert bad.lower() not in lower, f"forbidden phrase in Opt Lab copy: {bad!r}"


def test_opt_lab_labels_unversioned() -> None:
    from ui_nicegui.lib.opt_lab_entry import opt_lab_user_facing_texts

    for text in opt_lab_user_facing_texts():
        assert not _VERSION_TAG.search(text), f"version tag in Opt Lab label: {text!r}"


def test_opt_lab_route_session_hooks() -> None:
    from ui_nicegui.lib.opt_lab_entry import apply_opt_lab_route_session
    from ui_nicegui.session import DesignSession

    session = DesignSession()
    apply_opt_lab_route_session(session, "certified_search")
    assert session.cr_workflow_step == "6 · Chronicle"
    assert session.cr_section == "Chronicle"
    assert session.cr_chronicle_tab == "Certified Search"

    apply_opt_lab_route_session(session, "systems_mode")
    assert session.systems_workflow_step == "3 · Alternatives"

    apply_opt_lab_route_session(session, "pareto_lab")
    assert session.pareto_workflow_step == "1 · Setup & Run"


def test_opt_lab_nicegui_and_streamlit_surfaces() -> None:
    deck_init = (ROOT / "ui_nicegui" / "decks" / "opt_lab" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "render_opt_lab" in deck_init
    assert "render_opt_lab_entry" in deck_init

    panel = (ROOT / "ui_nicegui" / "components" / "opt_lab_entry_panel.py").read_text(
        encoding="utf-8"
    )
    assert "OPT_LAB_STEPS" in panel
    assert "OPT_LAB_ROUTES" in panel

    streamlit = (ROOT / "ui" / "decks" / "opt_lab.py").read_text(encoding="utf-8")
    assert "OPT_LAB_STEPS" in streamlit
    assert "Proposed — SHAMS-certified" in streamlit or "SHAMS-certified" in streamlit

    app = (ROOT / "ui" / "app.py").read_text(encoding="utf-8")
    assert '"Opt Lab"' in app
    assert "ui.decks.opt_lab" in app


def test_opt_lab_launchpad_and_workflow() -> None:
    from ui_nicegui.lib.control_room_helpers import LAUNCHPAD_DECK, LAUNCHPAD_PATHS
    from ui_nicegui.lib.deck_workflow import DECK_WORKFLOW_CAPTIONS
    from ui_nicegui.lib.helm_workflow_guide import DECK_NOW_ACTIONS, DECK_SHORT_VERBS
    from ui_nicegui.lib.mode_scope_data import MODE_SCOPE

    assert LAUNCHPAD_DECK.get("Start a certified search (Opt Lab)") == "Opt Lab"
    titles = [p[0] for p in LAUNCHPAD_PATHS]
    assert "Start a certified search (Opt Lab)" in titles

    assert "Opt Lab" in DECK_WORKFLOW_CAPTIONS
    assert "Opt Lab" in DECK_NOW_ACTIONS
    assert "Opt Lab" in DECK_SHORT_VERBS
    assert "opt_lab" in MODE_SCOPE


def test_roadmap_marks_1_1() -> None:
    roadmap = (ROOT / "docs" / "CERTIFIED_OPTIMIZER_ROADMAP.md").read_text(encoding="utf-8")
    assert "1.1" in roadmap
    # After ship this test expects DONE; written to pass once roadmap is updated.
    assert re.search(r"1\.1\s*\|[^|]*\|\s*\*\*DONE\*\*", roadmap) or (
        "**DONE**" in roadmap and "Opt Lab entry" in roadmap
    )
