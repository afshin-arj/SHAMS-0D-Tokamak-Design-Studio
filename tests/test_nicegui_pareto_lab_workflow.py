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


def test_frontier_posture_and_policy_filter() -> None:
    from ui_nicegui.lib.pareto_helpers import frontier_posture
    from ui_nicegui.lib.pareto_interpret_helpers import policy_filter_front

    msg, tone = frontier_posture({"n_feasible": 0, "n_pareto": 0})
    assert tone == "negative"
    msg2, _ = frontier_posture({"n_feasible": 10, "n_pareto": 5, "confidence": "High"})
    assert "High-confidence" in msg2

    feasible = [
        {"TBR": 1.1, "q_div_MW_m2": 10.0, "sigma_vm_MPa": 400.0, "R0_m": 1.8, "P_e_net_MW": 100.0},
        {"TBR": 0.8, "q_div_MW_m2": 10.0, "sigma_vm_MPa": 400.0, "R0_m": 2.0, "P_e_net_MW": 120.0},
        {"TBR": 1.2, "q_div_MW_m2": 8.0, "sigma_vm_MPa": 350.0, "R0_m": 1.9, "P_e_net_MW": 90.0},
    ]
    filtered = policy_filter_front(feasible, {"R0_m": "min", "P_e_net_MW": "max"}, tbr_min=1.0)
    assert len(filtered) >= 1
    assert all(float(r.get("TBR", 0)) >= 1.0 for r in filtered)


def test_interpret_helpers_second_pass() -> None:
    from ui_nicegui.lib.pareto_helpers import compute_nan_objective_rates
    from ui_nicegui.lib.pareto_interpret_helpers import (
        detect_free_lunch_steps,
        explain_segment,
        objective_relevance_table,
        possible_next_questions,
    )

    seg = explain_segment(
        [{"dominant_constraint": "q95", "R0_m": 1.8, "P_e_net_MW": 100}],
        y_key="P_e_net_MW",
    )
    assert "q95" in seg.get("narrative", "")
    rel = objective_relevance_table(
        [{"R0_m": 1.8, "P_e_net_MW": 100}, {"R0_m": 2.0, "P_e_net_MW": 80}],
        [{"R0_m": 1.9, "P_e_net_MW": 95}],
        ["R0_m", "P_e_net_MW"],
    )
    assert rel
    rates = compute_nan_objective_rates([{"R0_m": 1.0}], ["R0_m", "missing"])
    assert rates["missing"] == 1.0
    qs = possible_next_questions({"summary": {"n_pareto": 1, "confidence": "Sparse"}, "intent_mode": "Reactor"})
    assert qs


def test_atlas_deck_name_matches_external_router() -> None:
    from ui_nicegui.lib.pareto_labels import EXTERNAL_GROUPS

    atlas_names = EXTERNAL_GROUPS.get("Atlas & narratives", [])
    assert "Regime-Conditioned Pareto Atlas 2.0" in atlas_names
    assert "Regime-Conditioned Pareto Atlas" not in atlas_names


def test_objective_catalog_includes_fusion_metrics() -> None:
    from ui_nicegui.lib.pareto_helpers import OBJ_CATALOG, metric_label

    for key in ("H98", "Pfus_DT_adj_MW", "tauE_eff_s", "Paux_MW"):
        assert key in OBJ_CATALOG
    assert "confinement" in metric_label("H98").lower() or "H-mode" in metric_label("H98")


def test_pareto_import_get_point_artifact_triple() -> None:
    import importlib

    mod = importlib.import_module("ui_nicegui.decks.pareto_lab")
    src = importlib.import_module("inspect").getsource(mod.render_pareto_lab)
    assert "get_point_artifact_triple" in src
    from ui_nicegui.lib.artifact_access import get_point_artifact_triple

    s = DesignSession()
    _, _, out = get_point_artifact_triple(s)
    assert out is None or isinstance(out, dict)


def test_interpret_tab_uses_json_view_not_ui_json() -> None:
    import inspect

    from ui_nicegui.decks.pareto_lab import interpret as interpret_mod

    src = inspect.getsource(interpret_mod)
    assert "render_json_blob" in src
    assert "ui.json" not in src


def test_external_router_refreshes_deck_body_on_category_change() -> None:
    import inspect

    from ui_nicegui.decks import pareto_lab as pl_mod

    src = inspect.getsource(pl_mod._render_external_router)
    assert "_deck_body.refresh" in src
    assert "on_change=_on_tool_change" in src


def test_render_json_blob_helper() -> None:
    from ui_nicegui.components.json_view import render_json_blob

    assert callable(render_json_blob)
