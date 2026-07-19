"""Lock tests — Opt Lab champion warm-start (Certified Optimizer Phase 1.4).

Propose-only: champions load deterministic PointInputs into session + search
bounds seed; no auto-evaluate / auto-certify; honesty + no vNNN labels.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_VNNN = re.compile(r"\bv\d{3}\b", re.IGNORECASE)


def test_warm_start_module_and_surfaces_exist() -> None:
    assert (ROOT / "ui_nicegui" / "lib" / "opt_lab_warm_start.py").is_file()
    panel = (
        ROOT / "ui_nicegui" / "components" / "opt_lab_warm_start_panel.py"
    ).read_text(encoding="utf-8")
    assert "render_champion_warm_start" in panel
    assert "apply_champion_warm_start" in panel

    entry_panel = (
        ROOT / "ui_nicegui" / "components" / "opt_lab_entry_panel.py"
    ).read_text(encoding="utf-8")
    assert "render_champion_warm_start" in entry_panel

    systems = (
        ROOT / "ui_nicegui" / "decks" / "systems_mode" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "render_champion_warm_start" in systems

    pareto = (
        ROOT / "ui_nicegui" / "decks" / "pareto_lab" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "render_champion_warm_start" in pareto

    streamlit = (ROOT / "ui" / "decks" / "opt_lab.py").read_text(encoding="utf-8")
    assert "WARM_START_TITLE" in streamlit
    assert "champion_template_options" in streamlit


def test_warm_start_honesty_and_unversioned_labels() -> None:
    from ui_nicegui.lib.certified_opt_honesty import FORBIDDEN_POSITIVE_CLAIMS
    from ui_nicegui.lib.opt_lab_warm_start import (
        WARM_START_HONESTY,
        warm_start_user_facing_texts,
    )

    blob = " ".join(warm_start_user_facing_texts()).lower()
    assert "propose" in blob or "propose-only" in WARM_START_HONESTY.lower()
    assert "true minimum" in WARM_START_HONESTY.lower()
    assert "not" in WARM_START_HONESTY.lower()

    for text in warm_start_user_facing_texts():
        assert not _VNNN.search(text), f"version tag in warm-start copy: {text!r}"

    # Positive forbidden claims must not appear without ban markers.
    honesty_l = WARM_START_HONESTY.lower()
    for claim in FORBIDDEN_POSITIVE_CLAIMS:
        if claim.lower() in honesty_l:
            assert any(
                m in honesty_l for m in ("not", "never", "do not")
            ), f"forbidden positive claim without ban marker: {claim}"


def test_apply_champion_warm_start_deterministic_seed() -> None:
    import ui_nicegui.decks  # noqa: F401 — helm import order
    from studies.champion_cases import load_champion_definitions, resolve_inputs
    from ui_nicegui.lib.opt_lab_warm_start import (
        WARM_START_META_SCHEMA,
        apply_champion_warm_start,
        get_warm_start_case_id,
        get_warm_start_meta,
        warm_start_summary,
    )
    from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
    from ui_nicegui.session import DesignSession

    cases = load_champion_definitions()
    assert cases
    case = cases[0]
    case_id = str(case["case_id"])
    resolved = resolve_inputs(case)

    s1 = DesignSession()
    s2 = DesignSession()
    # Stale Systems / Pareto state must be cleared / refreshed from seed.
    s1.systems_bounds_overrides = {"Ip_MA": {"x0": 99.0, "lo": 1.0, "hi": 2.0}}
    s1.pareto_bounds = {"R0_m": (0.1, 0.2)}
    s1.last_eval = {"stale": True}

    m1 = apply_champion_warm_start(s1, case_id)
    m2 = apply_champion_warm_start(s2, case_id)

    assert m1["schema"] == WARM_START_META_SCHEMA
    assert m1["case_id"] == case_id == m2["case_id"]
    assert m1["propose_only"] is True
    assert m1["certified"] is False
    assert m1["evaluated"] is False
    assert m1["seed_knobs"] == m2["seed_knobs"]
    assert s1.inputs == s2.inputs
    assert s1.last_eval is None  # template clear; warm-start does not evaluate

    # Session knobs match champion basis for key seed fields.
    assert int(m1["override_count"]) > 0
    for key in ("R0_m", "Ip_MA", "Bt_T", "Paux_MW"):
        if key in resolved:
            assert float(s1.inputs[key]) == float(resolved[key]), key
            assert float(m1["seed_knobs"][key]) == float(resolved[key]), key

    assert get_warm_start_case_id(s1) == case_id
    assert get_warm_start_meta(s1) is not None
    assert get_warm_start_meta(s1)["case_id"] == case_id
    summary = warm_start_summary(s1)
    assert case_id in summary
    assert "not yet certified" in summary.lower()

    # Systems Mode picks x0 from new baseline (stale overrides cleared).
    assert s1.systems_bounds_overrides == {}
    assert s1.systems_recovery_seed_mode == "Point Designer baseline"
    _, _, variables = resolve_systems_problem(s1)
    if "Ip_MA" in variables:
        x0, lo, hi = variables["Ip_MA"]
        assert float(x0) == float(resolved["Ip_MA"])
        assert lo <= x0 <= hi

    # Pareto bounds refreshed around seed (not the stale 0.1–0.2 box).
    assert s1.pareto_bounds is not None
    r0_lo, r0_hi = s1.pareto_bounds["R0_m"]
    r0 = float(resolved["R0_m"])
    assert r0_lo <= r0 <= r0_hi
    assert (r0_lo, r0_hi) != (0.1, 0.2)

    # PD solver bounds forced from seed.
    assert s1.pd_ip_min < float(resolved["Ip_MA"]) < s1.pd_ip_max


def test_warm_start_does_not_auto_evaluate_or_certify() -> None:
    import ui_nicegui.decks  # noqa: F401
    from ui_nicegui.lib.opt_lab_warm_start import apply_champion_warm_start
    from ui_nicegui.lib.studio_entry import champion_template_options
    from ui_nicegui.session import DesignSession

    opts = champion_template_options()
    assert opts
    session = DesignSession()
    meta = apply_champion_warm_start(session, opts[0]["case_id"])
    assert meta["evaluated"] is False
    assert meta["certified"] is False
    assert session.last_eval is None
    assert session.pd_last_outputs is None
    assert getattr(session, "opt_lab_last_run_stamp", None) is None


def test_warm_start_infeasible_champion_loads() -> None:
    """NO-SOLUTION champions are valid seeds — infeasibility is not masked."""
    import ui_nicegui.decks  # noqa: F401
    from ui_nicegui.lib.opt_lab_warm_start import apply_champion_warm_start
    from ui_nicegui.lib.studio_entry import champion_template_options
    from ui_nicegui.session import DesignSession

    infeasible = [o for o in champion_template_options() if o["expect_hard_feasible"] is False]
    assert infeasible
    session = DesignSession()
    meta = apply_champion_warm_start(session, infeasible[0]["case_id"])
    assert meta["expect_hard_feasible"] is False
    assert session.build_point_inputs() is not None


def test_opt_lab_coming_next_no_longer_lists_warm_start_as_todo() -> None:
    deck = (ROOT / "ui_nicegui" / "decks" / "opt_lab" / "__init__.py").read_text(
        encoding="utf-8"
    )
    # Warm-start shipped; "Coming next" bullets must not advertise it as pending.
    assert "**Champion warm-start**" not in deck.split("Coming next in Opt Lab", 1)[-1]
    assert "SearchDrivers" in deck
    assert "render_opt_lab_entry" in deck
