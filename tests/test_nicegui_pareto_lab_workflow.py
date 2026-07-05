"""Pareto Lab NiceGUI workflow — labels, interpret helpers, tab routing."""
from __future__ import annotations

from ui_nicegui.decks.pareto_lab import render_pareto_lab
from ui_nicegui.decks.pareto_lab import explore, export_handoff, interpret
from ui_nicegui.lib.pareto_interpret_helpers import (
    interaction_matrix,
    knee_candidates,
    publication_pack_bytes,
    restore_pareto_artifact,
    trade_narrative,
)
from ui_nicegui.lib.pareto_labels import (
    DECISION_TO_TAB,
    EXTERNAL_GROUPS,
    PARETO_TABS,
    normalize_pareto_tab,
)
from ui_nicegui.lib.pareto_helpers import default_bounds, run_pareto_study
from ui_nicegui.session import DesignSession


def test_pareto_workflow_tabs() -> None:
    assert len(PARETO_TABS) == 5
    assert normalize_pareto_tab("Internal Pareto Frontier") == "1 · Setup & Run"
    assert DECISION_TO_TAB["Explore trade-offs on a plot"] == "2 · Explore Frontier"


def test_external_groups_cover_all_decks() -> None:
    from ui_nicegui.decks.pareto_lab.external import render_external_deck

    all_tools = [t for g in EXTERNAL_GROUPS.values() for t in g]
    assert len(all_tools) == 11
    assert callable(render_external_deck)


def test_interpret_helpers_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    result = run_pareto_study(
        base,
        bounds=default_bounds(base),
        objectives={"R0_m": "min", "P_e_net_MW": "max"},
        n_samples=30,
        seed=7,
        intent_mode="Reactor",
    )
    feasible = result.get("feasible") or []
    pareto = result.get("pareto") or []
    keys, rows = interaction_matrix(feasible, ["R0_m", "P_e_net_MW"])
    assert keys == ["R0_m", "P_e_net_MW"]
    if feasible:
        assert isinstance(rows, list)
    knees = knee_candidates(pareto, "R0_m", "P_e_net_MW", top_k=3)
    assert isinstance(knees, list)
    narrative = trade_narrative(result)
    assert "Pareto trade-off summary" in narrative
    blob = publication_pack_bytes(result, narrative=narrative)
    assert blob[:2] == b"PK"
    restored = restore_pareto_artifact(result)
    assert restored.get("summary")


def test_session_workflow_defaults() -> None:
    s = DesignSession()
    assert s.pareto_workflow_step == "1 · Setup & Run"
    assert s.pareto_teaching_mode is True
    assert callable(render_pareto_lab)


def test_pareto_v2_enrichment_smoke() -> None:
    from ui_nicegui.lib.pareto_interpret_helpers import (
        enrich_pareto_front,
        objective_sanity_warnings,
        sampling_honesty,
    )

    pareto = [{"R0_m": 1.8, "P_e_net_MW": 100, "dominant_constraint": "q95", "min_constraint_margin": 0.2}]
    feasible = pareto * 12
    enriched = enrich_pareto_front(pareto, feasible, x_key="R0_m", y_key="P_e_net_MW")
    assert enriched and "geography" in enriched[0]
    assert isinstance(objective_sanity_warnings({"R0_m": "min"}, "Reactor"), list)
    rep = {"all": feasible, "feasible": feasible, "pareto": pareto, "objectives": {"R0_m": "min", "P_e_net_MW": "max"}}
    assert sampling_honesty(rep)["n_feasible"] == 12
    assert callable(explore.render_explore_tab)
    assert callable(interpret.render_interpret_tab)
    assert callable(export_handoff.render_export_tab)
