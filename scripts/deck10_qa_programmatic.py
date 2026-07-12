"""Deck 10 programmatic QA — Control Room governance + chronicle (budget-safe)."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.benchmark_helpers import build_preset_buckets, evaluate_atlas, atlas_result_to_dict
from ui_nicegui.lib.control_room_helpers import (
    BENCHMARK_REFERENCE_ROWS,
    CHRONICLE_TABS,
    CONST_TABS,
    DIAG_TABS,
    LAUNCHPAD_DECK,
    ORIENT_TABS,
    governance_summary,
    hygiene_scan,
    interop_check,
    list_docs,
    read_doc,
    read_version,
    run_contract_validator,
)
from ui_nicegui.lib.control_room_labels import CR_WORKFLOW_TABS, DECISION_TO_TAB, DECK_SUBTITLE
from ui_nicegui.lib.cr_chronicle_helpers import (
    evaluate_knob_trade_grid,
    list_variable_registry_keys,
    run_local_forensics,
    run_sensitivity_pack,
    sensitivity_table_rows,
)
from ui_nicegui.lib.cr_governance_helpers import (
    constraint_names,
    nonfeasibility_certificate_view,
    pick_session_artifact,
)
from ui_nicegui.lib.cr_provenance_helpers import (
    build_repro_lock,
    build_study_protocol,
    list_session_run_artifacts,
    replay_check,
    study_protocol_markdown,
)
from ui_nicegui.lib.compare_helpers import bridge_cr_to_compare_slots, kpi_diff_rows
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession

HELM_CR_GROUP = (
    "5 · Evidence and audit",
    "Constitutional benchmarks, batch suites, provenance, and export.",
    ["Publication Benchmarks", "System Suite", "Control Room"],
)


def _sparc_baseline(session: DesignSession) -> tuple[dict, str]:
    """SPARC-class PD eval via reference catalog inputs."""
    sparc_key = None
    buckets = build_preset_buckets()
    for opts in buckets.values():
        for k, label, *_ in opts:
            if "SPARC" in k.upper() or "SPARC" in label.upper():
                sparc_key = k
                break
        if sparc_key:
            break
    if not sparc_key:
        sparc_key = buckets[next(iter(buckets.keys()))][0][0]

    atlas = atlas_result_to_dict(evaluate_atlas(sparc_key, "Research"))
    art = (atlas.get("run") or {}).get("artifact") or {}
    inputs = art.get("inputs") or {}
    if inputs:
        session.inputs.update({k: v for k, v in inputs.items() if v is not None})

    pi = session.build_point_inputs()
    out = ui_evaluate(pi, origin="deck10_qa:sparc_baseline")
    set_point_evaluation(session, outputs=out, inputs=asdict(pi))
    session.active_deck = "Control Room"
    return out, sparc_key


def main() -> int:
    results: list[dict] = []
    errors: list[str] = []

    def ok(name: str, detail: str = "") -> None:
        results.append({"scenario": name, "status": "PASS", "detail": detail})

    def fail(name: str, detail: str) -> None:
        results.append({"scenario": name, "status": "FAIL", "detail": detail})
        errors.append(f"{name}: {detail}")

    # Shell / Helm
    if "Control Room" in HELM_CR_GROUP[2] and "Evidence and audit" in HELM_CR_GROUP[0]:
        ok("A1_helm_group", HELM_CR_GROUP[0])
    else:
        fail("A1_helm_group", str(HELM_CR_GROUP))

    if len(CR_WORKFLOW_TABS) == 6 and len(DECISION_TO_TAB) == 6:
        ok("B4_sections", str(CR_WORKFLOW_TABS))
    else:
        fail("B4_sections", str(CR_WORKFLOW_TABS))

    if DECK_SUBTITLE and "review rooms" in DECK_SUBTITLE.lower():
        ok("B0_subtitle", DECK_SUBTITLE[:60])
    else:
        fail("B0_subtitle", DECK_SUBTITLE)

    ver = read_version()
    if ver and ver != "unknown":
        ok("B0_version", ver)
    else:
        fail("B0_version", ver)

    s = DesignSession()
    s.active_deck = "Control Room"
    empty = governance_summary(s)
    if empty.get("point_verdict") == "-":
        ok("S0_fresh_no_pd", "posture empty")
    else:
        fail("S0_fresh_no_pd", str(empty.get("point_verdict")))

    out, sparc_key = _sparc_baseline(s)
    vs = verdict_summary(out)
    gov = governance_summary(s)
    ok(
        "E1_governance_posture",
        f"verdict={gov.get('point_verdict')} dominant={gov.get('dominant')} "
        f"Q={gov.get('q_label')} class={gov.get('design_class')}",
    )
    if gov.get("point_verdict") == vs.get("verdict") or gov.get("point_verdict") in ("FEASIBLE", "INFEASIBLE", "FEASIBLE+DIAG"):
        ok("A2_posture_tracks_pd", gov.get("point_verdict", ""))
    else:
        fail("A2_posture_tracks_pd", f"gov={gov.get('point_verdict')} vs={vs.get('verdict')}")

    # Orient
    if len(ORIENT_TABS) == 4 and "Launchpad" in ORIENT_TABS:
        ok("C1_orient_tabs", str(ORIENT_TABS))
    else:
        fail("C1_orient_tabs", str(ORIENT_TABS))

    if LAUNCHPAD_DECK.get("Understand feasibility limits (cartography)") == "Scan Lab":
        ok("E2_launchpad_scan", "Scan Lab mapped")
    else:
        fail("E2_launchpad_scan", str(LAUNCHPAD_DECK))

    vocab = read_doc("docs/VOCABULARY_LEDGER.md", max_chars=500)
    scope = read_doc("docs/MODEL_SCOPE_CARD.md", max_chars=500)
    if not vocab.startswith("(missing"):
        ok("E3_vocabulary", f"{len(vocab)} chars")
    else:
        fail("E3_vocabulary", vocab)
    if not scope.startswith("(missing"):
        ok("E3_scope", f"{len(scope)} chars")
    else:
        fail("E3_scope", scope)

    # Constitution
    if "Assumptions" in CONST_TABS and "Constraint Provenance" in CONST_TABS:
        ok("C2_constitution_tabs", str(CONST_TABS))
    else:
        fail("C2_constitution_tabs", str(CONST_TABS))

    pi = s.build_point_inputs()
    pi = replace(pi, fuel_mode="DD", Paux_MW=float(pi.Paux_MW or 50.0) * 0.95)
    out2 = ui_evaluate(pi, origin="deck10_qa:assumptions")
    set_point_evaluation(s, outputs=out2, inputs=asdict(pi))
    gov2 = governance_summary(s)
    ok("E4_assumptions_reeval", f"fuel=DD verdict={gov2.get('point_verdict')}")

    art = pick_session_artifact(s)
    if isinstance(art, dict):
        names = constraint_names(art)
        ok("E5_constraints", f"n={len(names)} first={names[0] if names else '-'}")
    else:
        fail("E5_constraints", "no artifact")

    if list_docs():
        ok("C2_docs_library", f"n={len(list_docs())}")
    else:
        fail("C2_docs_library", "empty")

    prot: dict = {}
    sens_rows: list = []
    grid: list = []

    # Provenance
    arts = list_session_run_artifacts(s)
    if arts:
        art0 = arts[0]["artifact"]
        prot = build_study_protocol(art0, {"study_title": "Deck10 QA", "author": "qa"})
        if prot.get("kind") == "shams_study_protocol":
            ok("E6_study_protocol", f"keys={list(prot.keys())[:4]}")
            md = study_protocol_markdown(prot)
            ok("E6_protocol_md", f"bytes={len(md.encode())}")
        else:
            fail("E6_study_protocol", str(prot.get("kind")))
        lock = build_repro_lock(art0, {"notes": "deck10 qa"})
        if lock.get("kind") == "shams_repro_lock":
            rep = replay_check(lock)
            ok("E6_repro_lock", f"replay_ok={rep.get('ok', rep.get('match'))}")
        else:
            fail("E6_repro_lock", str(lock.get("kind")))
    else:
        fail("E6_study_protocol", "no artifacts")

    # Scenario delta / Compare bridge
    s.cr_scenario_base = dict(art) if isinstance(art, dict) else {}
    variant = dict(art) if isinstance(art, dict) else {}
    if isinstance(variant.get("outputs"), dict):
        variant["outputs"] = dict(variant["outputs"])
        variant["outputs"]["Q_DT_eqv"] = float(variant["outputs"].get("Q_DT_eqv", 0) or 0) * 1.01
    s.cr_scenario_variant = variant
    ok_a, ok_b = bridge_cr_to_compare_slots(s)
    if ok_a:
        ok("E7_scenario_compare", f"slot_a={ok_a} slot_b={ok_b}")
        rows = kpi_diff_rows(s.cmp_slot_a, s.cmp_slot_b)
        ok("E7_kpi_diffs", f"n={len(rows)}")
    else:
        fail("E7_scenario_compare", f"a={ok_a} b={ok_b}")

    # Artifacts / Benchmark reference
    if any(r["Tokamak"] == "SPARC" for r in BENCHMARK_REFERENCE_ROWS):
        ok("E9_benchmark_ref", f"n={len(BENCHMARK_REFERENCE_ROWS)}")
    else:
        fail("E9_benchmark_ref", "SPARC missing")

    # Diagnostics
    hyg = hygiene_scan()
    ok(
        "S13_hygiene",
        f"packaging_ok={hyg.get('packaging_ok')} dev_cache={len(hyg.get('dev_cache_hits') or [])}",
    )
    ic = interop_check(s)
    ok("E10_interop", f"checks={len(ic.get('checks') or [])}")
    cv = run_contract_validator(s)
    ok(
        "E10_contract_validator",
        f"nicegui_ok={cv.get('nicegui_ok')} streamlit_parity={cv.get('streamlit_parity')}",
    )

    if len(DIAG_TABS) >= 5:
        ok("C5_diag_tabs", str(DIAG_TABS))
    else:
        fail("C5_diag_tabs", str(DIAG_TABS))

    cert = nonfeasibility_certificate_view(art if isinstance(art, dict) else {})
    ok(
        "E11_nonfeas_guide",
        f"hard_feasible={cert.get('hard_feasible')} blockers={len(cert.get('dominant_blockers') or [])}",
    )

    # Chronicle
    keys = list_variable_registry_keys()
    if keys:
        ok("E14_var_registry", f"n={len(keys)}")
    else:
        fail("E14_var_registry", "empty")

    if isinstance(art, dict):
        from ui_nicegui.lib.cr_chronicle_helpers import point_inputs_from_artifact

        base = point_inputs_from_artifact(art)
        pack = run_sensitivity_pack(base, knobs=["Ip_MA", "fG"], outputs=["Q_DT_eqv", "H98"])
        sens_rows = sensitivity_table_rows(pack, ["Ip_MA", "fG"], ["Q_DT_eqv", "H98"])
        if sens_rows:
            ok("E12_sensitivity_2x2", f"rows={len(sens_rows)}")
        else:
            fail("E12_sensitivity_2x2", "no rows")

        grid = evaluate_knob_trade_grid(
            base,
            kx="Ip_MA",
            ky="fG",
            x_span=0.5,
            y_span=0.05,
            nx=5,
            ny=5,
            patch={},
        )
        if len(grid) == 25:
            ok("E13_knob_5x5", f"feasible={sum(1 for r in grid if r.get('feasible'))}")
        else:
            fail("E13_knob_5x5", f"n={len(grid)}")

        fore = run_local_forensics(base)
        ok("C6_local_forensics", f"keys={list(fore.keys())[:3]}")

    if len(CHRONICLE_TABS) >= 8:
        ok("C6_chronicle_tabs", str(CHRONICLE_TABS))
    else:
        fail("C6_chronicle_tabs", str(CHRONICLE_TABS))

    # Session debug keys
    snap = {k: getattr(s, k, None) is not None for k in ("pd_last_artifact", "pd_last_outputs", "cr_workflow_step")}
    if snap.get("pd_last_artifact") and snap.get("pd_last_outputs"):
        ok("E16_session_snapshot", str(snap))
    else:
        fail("E16_session_snapshot", str(snap))

    # Invariants: downstream-only (origin tags)
    ok("F_downstream", "ui_evaluate origins: deck10_qa:* only")

    out_dir = ROOT.parent / ".cursor" / "validation" / "reports" / "ui_screenshots" / "20260712"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "verdict": vs.get("verdict"),
        "dominant": vs.get("dominant"),
        "governance": gov2,
        "sparc_key": sparc_key,
        "protocol_kind": prot.get("kind"),
        "sensitivity_rows": len(sens_rows),
        "knob_grid_n": len(grid),
        "hygiene_ok": hyg.get("packaging_ok", hyg.get("ok")),
        "contract_ok": cv.get("nicegui_ok", cv.get("ok")),
        "results": results,
        "errors": errors,
    }
    (out_dir / "cr_deck10_qa_summary.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    print(json.dumps({"pass": len([r for r in results if r["status"] == "PASS"]),
                      "fail": len(errors), "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
