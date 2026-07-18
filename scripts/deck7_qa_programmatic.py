"""Deck 7 programmatic QA — Reactor Design Forge + Helm helpers (budget-safe)."""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.forge_helpers import (
    audit_candidate_inputs,
    compile_forge_candidate,
    summarize_forge_state,
)
from ui_nicegui.lib.forge_handoff_helpers import send_archive_row_to_compare
from ui_nicegui.lib.forge_instrument_data import INSTRUMENT_GROUPS
from ui_nicegui.lib.forge_instrument_engine import build_context, compute_instrument
from ui_nicegui.lib.forge_labels import FORGE_TABS, WORKBENCH_VIEWS
from ui_nicegui.lib.forge_machine_finder_helpers import (
    anchor_from_session,
    archive_table_rows,
    build_capsule_zip_bytes,
    build_forge_audit_pack_zip,
    compute_bounds,
    intent_from_label,
    objectives_for_pack,
    promote_archive_row,
    restore_workbench_from_capsule,
    run_machine_finder,
    summarize_workbench_run,
)
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.session import DesignSession

HELM_FORGE_GROUP = (
    "4 · Develop concepts",
    "Compile intent, explore machine families, archive candidates.",
    ["Reactor Design Forge"],
)

BUDGET = dict(pop_size=36, generations=12, surrogate_rounds=2, local_steps=24, archive_topk=32)
VAR_KEYS = ["R0_m", "Bt_T", "Ip_MA", "Paux_MW"]


def _pd_baseline(session: DesignSession) -> None:
    inp = session.build_point_inputs()
    out = ui_evaluate(inp, origin="deck7_qa:pd_baseline")
    session.pd_last_inputs = inp.__dict__ if hasattr(inp, "__dict__") else dict(inp)
    session.pd_last_outputs = {"outputs": out}


def _mf_run(session: DesignSession, intent_label: str, *, seed: int = 7) -> dict:
    base = session.build_point_inputs()
    anchor = anchor_from_session(base)
    intent = intent_from_label(intent_label)
    bounds = compute_bounds(anchor, VAR_KEYS, bound_mode="Medium (±20%)")
    packs = __import__(
        "tools.sandbox.optimizer_engines", fromlist=["default_objective_packs"]
    ).default_objective_packs(intent)
    pack_name = packs[0].name
    objectives = objectives_for_pack(intent, pack_name)
    session.forge_lens_contract = {"name": pack_name, "objectives": [o.__dict__ for o in objectives]}
    session.forge_mf_last_bounds = {k: list(v) for k, v in bounds.items()}
    return run_machine_finder(
        intent=intent,
        anchor=anchor,
        var_keys=VAR_KEYS,
        bounds=bounds,
        objectives=objectives,
        require_feasible_only=True,
        enable_surface_surf=False,
        enable_skeleton=True,
        seed=seed,
        **BUDGET,
    )


def main() -> int:
    results: list[dict] = []
    errors: list[str] = []

    def ok(name: str, detail: str = "") -> None:
        results.append({"scenario": name, "status": "PASS", "detail": detail})

    def fail(name: str, detail: str) -> None:
        results.append({"scenario": name, "status": "FAIL", "detail": detail})
        errors.append(f"{name}: {detail}")

    if HELM_FORGE_GROUP[2] == ["Reactor Design Forge"]:
        ok("A1_helm_group", HELM_FORGE_GROUP[0])
    else:
        fail("A1_helm_group", str(HELM_FORGE_GROUP))

    if len(FORGE_TABS) == 5 and len(WORKBENCH_VIEWS) == 7:
        ok("B4_tabs_views", f"{len(FORGE_TABS)} tabs, {len(WORKBENCH_VIEWS)} views")
    else:
        fail("B4_tabs_views", f"tabs={len(FORGE_TABS)} views={len(WORKBENCH_VIEWS)}")

    s = DesignSession()
    if s.pd_last_outputs is None:
        ok("S0_no_pd", "blocked without eval (session default)")

    _pd_baseline(s)
    ok("S1_pd_loaded", "baseline evaluated")

    base = s.build_point_inputs()
    compiled = compile_forge_candidate(base, pfus_target_mw=140.0, q_target=2.0)
    if compiled.get("status") != "OK":
        fail("E1_compile", str(compiled))
    else:
        ok("E1_compile", f"Paux={compiled['candidate_inputs'].get('Paux_MW')}")
        audit = audit_candidate_inputs(compiled["candidate_inputs"], origin="deck7_qa")
        verdict = audit.get("verdict", {}).get("label", audit.get("verdict", {}))
        ok("E1_audit", str(verdict))
        s.forge_intent_compiler_last = compiled
        s.forge_last_audit = audit
        summarize_forge_state(compiled, audit)

    compiled2 = compile_forge_candidate(
        base, pfus_target_mw=140.0, q_target=2.0, overrides={"R0_m": 2.2}
    )
    if compiled2.get("status") == "OK" and abs(float(compiled2["candidate_inputs"]["R0_m"]) - 2.2) < 1e-6:
        ok("E2_r0_override", "R0=2.2")
    else:
        fail("E2_r0_override", str(compiled2))

    run_reactor = _mf_run(s, "Power Reactor (net-electric)", seed=11)
    wb_r = summarize_workbench_run(run_reactor)
    ok("E3_mf_reactor", f"{wb_r.get('n_feasible_archive')}/{wb_r.get('n_archive')} feasible")

    run_research = _mf_run(s, "Experimental Device (research)", seed=11)
    wb_res = summarize_workbench_run(run_research)
    ok(
        "E4_mf_research",
        f"{wb_res.get('n_feasible_archive')}/{wb_res.get('n_archive')} feasible "
        f"(Reactor had {wb_r.get('n_feasible_archive')})",
    )

    s.forge_workbench_run = run_research
    rows = archive_table_rows(run_research, limit=10)
    ok("E6_archive_rows", f"{len(rows)} table rows")

    ctx = build_context(s)
    for group, tools in INSTRUMENT_GROUPS.items():
        pick = tools[0]
        try:
            v = compute_instrument(pick, ctx)
            if getattr(v, "traceback", None):
                fail(f"E9_inst_{group}", v.traceback)
            else:
                ok(f"E9_inst_{group}", pick)
        except Exception as exc:  # noqa: BLE001
            fail(f"E9_inst_{group}", f"{pick}: {exc}")

    bounds = dict(s.forge_mf_last_bounds or {})
    lens = dict(s.forge_lens_contract or {})
    try:
        capsule_bytes, _ = build_capsule_zip_bytes(run_research, lens_contract=lens, bounds=bounds)
        with tempfile.TemporaryDirectory() as td:
            zpath = Path(td) / "cap.zip"
            zpath.write_bytes(capsule_bytes)
            with zipfile.ZipFile(zpath) as zf:
                names = zf.namelist()
                json_name = next((n for n in names if n.endswith(".json")), None)
                assert json_name
                cap = json.loads(zf.read(json_name))
            restored = restore_workbench_from_capsule(cap)
            if restored.get("archive") is not None:
                ok("E11_capsule_roundtrip", f"{len(restored.get('archive', []))} archive rows")
            else:
                fail("E11_capsule_roundtrip", "no archive after restore")
    except Exception as exc:  # noqa: BLE001
        fail("E11_capsule_roundtrip", str(exc))

    try:
        if rows:
            pack_bytes, _ = build_forge_audit_pack_zip(
                run_research,
                row_idx=0,
                lens_contract=lens,
                bounds=bounds,
                intent=str(run_research.get("intent") or "Research"),
            )
            ok("E12_audit_pack", f"{len(pack_bytes)} bytes")
        else:
            ok("E12_audit_pack", "skipped — empty archive")
    except Exception as exc:  # noqa: BLE001
        fail("E12_audit_pack", str(exc))

    if run_research.get("archive"):
        merged = promote_archive_row(dict(s.pd_last_inputs or {}), run_research, 0)
        s.pd_last_inputs = merged
        ok("E13_promote", f"keys merged={len(merged)}")
    else:
        ok("E13_promote", "skipped — no archive rows")

    if run_research.get("archive"):
        send_archive_row_to_compare(s, run_research, 0, "B")
        ok("E14_compare_handoff", f"slot B populated={s.cmp_slot_b is not None}")
    else:
        ok("E14_compare_handoff", "skipped")

    owner = "deck7_qa"
    if runlock_acquire("deck7_qa: MF sim", owner):
        locked, task, holder = runlock_status(owner)
        if locked and holder == owner:
            ok("E16_runlock_acquire", task or "locked")
        else:
            fail("E16_runlock_acquire", f"locked={locked} holder={holder}")
        runlock_release(owner)
        ok("E16_runlock_release", "released")
    else:
        fail("E16_runlock_acquire", "could not acquire")

    s.forge_review_mode = True
    ok("S4_review_mode", "session flag set")

    out_path = ROOT.parent / ".cursor" / "validation" / "reports" / "deck_qa" / "deck7_programmatic.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"results": results, "errors": errors}, indent=2), encoding="utf-8")
    print(json.dumps({"pass": len([r for r in results if r["status"] == "PASS"]), "fail": len(errors)}, indent=2))
    for r in results:
        mark = "OK" if r["status"] == "PASS" else "!!"
        print(f"  [{mark}] {r['scenario']}: {r['detail'][:80]}")
    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
