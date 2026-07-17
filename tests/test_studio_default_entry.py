"""Independence Phase 3.4 — Studio as default entry lock tests.

Contract: the Studio lands on a verdict-first entry path (Point Designer),
champion templates load deterministic PointInputs with one click, onboarding
copy treats NO-SOLUTION as first-class and links migration guide + champion
cases, and no user-facing entry label carries an internal version tag.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_VERSION_TAG = re.compile(r"\bv\d{3}\b", re.IGNORECASE)


def test_default_landing_deck_is_point_designer() -> None:
    from ui_nicegui.session import DesignSession

    session = DesignSession()
    assert session.active_deck == "Point Designer"
    assert session.studio_entry_dismissed is False

    app_src = (ROOT / "ui_nicegui" / "app.py").read_text(encoding="utf-8")
    assert 'ui.page("/")' in app_src, "root route must render the studio shell"


def test_entry_copy_contract() -> None:
    from ui_nicegui.lib import studio_entry as se

    assert se.STUDIO_ENTRY_TITLE
    assert "verdict" in se.STUDIO_ENTRY_TAGLINE.lower()
    assert "NO-SOLUTION" in se.STUDIO_ENTRY_TAGLINE or "NO-SOLUTION" in se.STUDIO_NO_SOLUTION_NOTE
    assert "first-class" in se.STUDIO_NO_SOLUTION_NOTE
    assert len(se.STUDIO_WHAT_SHAMS_ANSWERS) >= 3
    assert len(se.STUDIO_STEPS) >= 3

    # Onboarding docs must exist and include migration guide + champion cases.
    paths = [p for _, p in se.STUDIO_DOC_LINKS]
    assert "docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md" in paths
    assert "docs/CHAMPION_CASES.md" in paths
    for _, rel in se.STUDIO_DOC_LINKS:
        assert (ROOT / rel).is_file(), f"missing onboarding doc: {rel}"


def test_entry_copy_anti_overclaim() -> None:
    from ui_nicegui.lib import studio_entry as se

    blob = " ".join(
        [se.STUDIO_ENTRY_TITLE, se.STUDIO_ENTRY_TAGLINE, se.STUDIO_NO_SOLUTION_NOTE]
        + se.STUDIO_WHAT_SHAMS_ANSWERS
        + se.STUDIO_STEPS
        + [label for label, _ in se.STUDIO_DOC_LINKS]
    ).lower()
    assert not re.search(r"process\s+(?:is|has been)\s+retired", blob)


def test_entry_labels_unversioned() -> None:
    from ui_nicegui.lib import studio_entry as se

    user_facing = (
        [se.STUDIO_ENTRY_TITLE, se.STUDIO_ENTRY_TAGLINE, se.STUDIO_NO_SOLUTION_NOTE]
        + se.STUDIO_WHAT_SHAMS_ANSWERS
        + se.STUDIO_STEPS
        + [label for label, _ in se.STUDIO_DOC_LINKS]
        + [o["label"] for o in se.champion_template_options()]
        + [o["story"] for o in se.champion_template_options()]
    )
    for text in user_facing:
        assert not _VERSION_TAG.search(text), f"version tag in user-facing entry label: {text!r}"


def test_champion_template_options_deterministic() -> None:
    from studies.champion_cases import load_champion_definitions
    from ui_nicegui.lib.studio_entry import champion_template_options

    a = champion_template_options()
    b = champion_template_options()
    assert a == b
    assert len(a) >= 3
    case_ids = [o["case_id"] for o in a]
    assert case_ids == sorted(case_ids)
    assert set(case_ids) == {str(c["case_id"]) for c in load_champion_definitions()}
    # NO-SOLUTION stories are part of the default entry — at least one infeasible template.
    assert any(o["expect_hard_feasible"] is False for o in a)
    assert any(o["expect_hard_feasible"] is True for o in a)


def test_apply_champion_template_deterministic_inputs() -> None:
    import math
    from dataclasses import asdict

    import ui_nicegui.decks  # noqa: F401 — load deck package first (helm_labels import-order)
    from studies.champion_cases import load_champion_definitions, resolve_inputs
    from ui_nicegui.lib.helm_labels import DESIGN_INTENT_OPTIONS
    from ui_nicegui.lib.pd_intent_policy import design_intent_key
    from ui_nicegui.lib.studio_entry import apply_champion_template
    from ui_nicegui.session import DesignSession

    # UI radiation-gating fields: when the radiation overlay is off (studio
    # default), build_point_inputs neutralizes these — identically to Helm's
    # own reference-machine loads. Everything else must match the champion
    # evaluation basis field-for-field.
    ui_radiation_gated = {"zeff", "dilution_fuel", "f_rad_core", "include_synchrotron"}

    cases = {str(c["case_id"]): c for c in load_champion_definitions()}
    for case_id, case in cases.items():
        s1 = DesignSession()
        s2 = DesignSession()
        s1.last_eval = {"stale": True}  # template load must clear cached evaluations
        ov1 = apply_champion_template(s1, case_id)
        ov2 = apply_champion_template(s2, case_id)
        assert ov1 == ov2, case_id
        assert ov1, f"template applied no inputs: {case_id}"
        assert s1.inputs == s2.inputs, case_id
        assert s1.last_eval is None and s1.pd_last_outputs is None, case_id

        # Applied values match the champion evaluation basis exactly.
        resolved = resolve_inputs(case)
        for key, val in ov1.items():
            assert resolved[key] == val, f"{case_id}: {key}"
            assert s1.inputs.get(key) == val, f"{case_id}: {key} not in session inputs"

        # Q accounting follows the template's heating power (reviewer gate:
        # never evaluate Q with a stale session Paux_for_Q_MW default).
        assert float(s1.inputs["Paux_for_Q_MW"]) == float(ov1["Paux_MW"]), case_id

        # Mission profile follows the case Design Intent and is a valid Helm option.
        assert s1.design_intent in DESIGN_INTENT_OPTIONS, case_id
        assert design_intent_key(s1.design_intent) == design_intent_key(
            str(case.get("design_intent") or "Research")
        ), case_id

        # Full-basis parity: built PointInputs equal the champion basis on every
        # field except the documented UI radiation-gating set.
        built = asdict(s1.build_point_inputs())
        for key, val in resolved.items():
            if key in ui_radiation_gated:
                continue
            got = built.get(key)
            if isinstance(val, float) and isinstance(got, float) and math.isnan(val) and math.isnan(got):
                continue
            assert got == val, f"{case_id}: {key} built={got!r} basis={val!r}"


def test_infeasible_template_loads_without_masking() -> None:
    """NO-SOLUTION templates load like any other — infeasibility is never hidden."""
    from ui_nicegui.lib.studio_entry import apply_champion_template, champion_template_options
    from ui_nicegui.session import DesignSession

    infeasible = [o for o in champion_template_options() if o["expect_hard_feasible"] is False]
    assert infeasible
    session = DesignSession()
    overrides = apply_champion_template(session, infeasible[0]["case_id"])
    assert overrides
    assert session.build_point_inputs() is not None


def test_point_designer_renders_studio_entry() -> None:
    src = (ROOT / "ui_nicegui" / "decks" / "point_designer" / "__init__.py").read_text(encoding="utf-8")
    assert "render_studio_entry" in src
    assert "studio_entry_dismissed" in src
    # Entry card only shows before the first evaluation.
    assert "pd_last_outputs or session.last_eval" in src


def test_launchpad_champion_path_routes_to_point_designer() -> None:
    from ui_nicegui.lib.control_room_helpers import LAUNCHPAD_DECK, LAUNCHPAD_PATHS

    assert LAUNCHPAD_DECK["Run a champion feasibility template"] == "Point Designer"
    champion_rows = [p for p in LAUNCHPAD_PATHS if p[0] == "Run a champion feasibility template"]
    assert champion_rows
    assert "Point Designer" in champion_rows[0][1]


def test_streamlit_parity_entry_block() -> None:
    src = (ROOT / "ui" / "decks" / "point_designer.py").read_text(encoding="utf-8")
    assert "Start a systems study" in src
    assert "NO-SOLUTION" in src
    assert "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md" in src
    assert "CHAMPION_CASES.md" in src


def test_roadmap_marks_phase_3_4() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "3.4" in roadmap
    assert "default entry" in roadmap.lower()
    assert "DONE" in roadmap
