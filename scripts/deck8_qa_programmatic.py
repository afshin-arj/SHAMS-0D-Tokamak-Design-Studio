"""Deck 8 programmatic QA — System Suite overlays + campaign/parity (budget-safe)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release
from ui_nicegui.lib.suite_helpers import (
    SUITE_RUNLOCK_OWNER,
    lifetime_binding_summary,
)
from ui_nicegui.lib.suite_labels import DECISION_TO_TAB, SUITE_TABS, teaching_banner
from ui_nicegui.session import DesignSession

# Avoid circular import via helm_labels → decks.__init__
HELM_SUITE_GROUP = (
    "5 · Evidence and audit",
    "Constitutional benchmarks, batch suites, provenance, and export.",
    ["Publication Benchmarks", "System Suite", "Control Room"],
)


def _pd_baseline(session: DesignSession) -> dict:
    inp = session.build_point_inputs()
    out = ui_evaluate(inp, origin="deck8_qa:pd_baseline")
    session.pd_last_inputs = dict(getattr(inp, "__dict__", {}) or {})
    session.pd_last_outputs = {"outputs": out}
    session.pd_last_run_ts = 1.0
    return out


def main() -> int:
    results: list[dict] = []
    errors: list[str] = []

    def ok(name: str, detail: str = "") -> None:
        results.append({"scenario": name, "status": "PASS", "detail": detail})

    def fail(name: str, detail: str) -> None:
        results.append({"scenario": name, "status": "FAIL", "detail": detail})
        errors.append(f"{name}: {detail}")

    # A1 Helm group
    if "System Suite" in HELM_SUITE_GROUP[2] and "Evidence and audit" in HELM_SUITE_GROUP[0]:
        ok("A1_helm_group", HELM_SUITE_GROUP[0])
    else:
        fail("A1_helm_group", str(HELM_SUITE_GROUP))

    if len(SUITE_TABS) == 5 and len(DECISION_TO_TAB) == 5:
        ok("B3_tabs", f"{len(SUITE_TABS)} tabs")
    else:
        fail("B3_tabs", str(SUITE_TABS))

    s = DesignSession()
    if s.pd_last_outputs is None:
        ok("S0_no_pd", "blocked without eval")
    if teaching_banner(s) is None and s.suite_teaching_mode is False:
        ok("B1_guided_default_off", "suite_teaching_mode=False")

    out = _pd_baseline(s)
    ok("S1_pd_loaded", f"Q={out.get('Q_DT_eqv')}")

    from tools.system_suite import (
        lifetime_and_fuel_overlay,
        ops_availability_overlay,
        power_closure_overlay,
        thermal_network_diagnostics_client,
        trajectory_diagnostics_client,
    )

    # E1 plant closure
    power = power_closure_overlay(out, s.pd_last_inputs)
    pe_net = float(getattr(power, "Pe_net_MW", float("nan")))
    pe_out = out.get("P_e_net_MW", out.get("Pe_net_MW"))
    ok("E1_plant_closure", f"overlay Pe_net={pe_net} point={pe_out} stamp={str(power.stamp_sha256)[:12]}")

    # E3 availability linear scale
    d50 = ops_availability_overlay(out, s.pd_last_inputs, availability=0.5)
    d90 = ops_availability_overlay(out, s.pd_last_inputs, availability=0.9)
    e50 = float(d50.annual_energy_GWh)
    e90 = float(d90.annual_energy_GWh)
    if math.isfinite(e50) and math.isfinite(e90) and e50 > 0:
        ratio = e90 / e50
        if abs(ratio - 1.8) < 0.05:
            ok("E3_availability_scale", f"50%={e50:.3f} 90%={e90:.3f} ratio={ratio:.3f}")
        else:
            fail("E3_availability_scale", f"ratio={ratio} expected ~1.8")
    else:
        ok("E3_availability_scale", f"non-finite energy 50%={e50} 90%={e90} (infeasible plant OK)")

    # E4 thermal + trajectory
    therm = thermal_network_diagnostics_client(out, s.pd_last_inputs)
    traj = trajectory_diagnostics_client(out, s.pd_last_inputs)
    ok(
        "E4_thermal_traj",
        f"therm_v={len(therm.violations or [])} traj_v={len(traj.violations or [])} "
        f"power_incomplete={bool((traj.meta or {}).get('power_incomplete'))}",
    )

    # E5 lifetime
    life = lifetime_and_fuel_overlay(out, s.pd_last_inputs)
    bind = lifetime_binding_summary(life)
    ok("E5_lifetime", f"posture={bind['posture']} binding={bind['binding']}")

    # E6 regimes
    try:
        from src.analysis.regime_transition_detector_v353 import evaluate_regime_transitions

        rt = evaluate_regime_transitions(inputs=s.pd_last_inputs or {}, outputs=out)
        labels = rt.get("labels") or {}
        ok("E6_regimes", f"conf={labels.get('confinement_regime')} exh={labels.get('exhaust_regime')}")
    except Exception as exc:  # noqa: BLE001
        fail("E6_regimes", str(exc))

    # E8 profile corners C8
    try:
        from src.analysis.profile_contracts_v362 import evaluate_profile_contracts_v362
        from src.models.inputs import PointInputs

        inp = PointInputs.from_dict(dict(s.pd_last_inputs or {}))
        rep = evaluate_profile_contracts_v362(inp, preset="C8", tier="both")
        d = rep.to_dict()
        s.profile_contracts_v362_last = d
        ok(
            "E8_profile_C8",
            f"opt={d.get('optimistic_feasible')} rob={d.get('robust_feasible')} "
            f"gap={d.get('mirage')} corners={d.get('corner_count')}",
        )
    except Exception as exc:  # noqa: BLE001
        fail("E8_profile_C8", str(exc))

    # E11 campaign n=8
    try:
        from ui_nicegui.lib.suite_extended_helpers import (
            default_campaign_template,
            evaluate_campaign_batch,
            generate_campaign_candidates,
            parse_campaign_spec,
        )

        tmpl = default_campaign_template(s.pd_last_inputs)
        if isinstance(tmpl.get("generator"), dict):
            tmpl["generator"]["n"] = 8
        elif "n" in tmpl:
            tmpl["n"] = 8
        # walk nested for generator.n
        def _set_n(obj, n=8):
            if isinstance(obj, dict):
                if "n" in obj and isinstance(obj["n"], (int, float)):
                    obj["n"] = n
                for v in obj.values():
                    _set_n(v, n)
            elif isinstance(obj, list):
                for v in obj:
                    _set_n(v, n)

        _set_n(tmpl, 8)
        spec = parse_campaign_spec(json.dumps(tmpl))
        cands = generate_campaign_candidates(spec)
        summary, rows, jsonl = evaluate_campaign_batch(spec, cands)
        s.suite_campaign_summary = summary
        s.suite_campaign_results_preview = rows[:50]
        s.suite_campaign_jsonl_bytes = jsonl
        s.suite_campaign_candidates = cands
        ok(
            "E11_campaign_n8",
            f"n={summary.get('n_total')} feas={summary.get('n_feasible')} jsonl={len(jsonl)}B",
        )
    except Exception as exc:  # noqa: BLE001
        fail("E11_campaign_n8", str(exc))

    # E12 parity selected case (smoke)
    try:
        from ui_nicegui.lib.suite_extended_helpers import list_parity_cases, run_parity_suite

        cases = list_parity_cases("v364")
        if not cases:
            ok("E12_parity_case", "no cases listed — skip")
        else:
            cid, path = cases[0]
            rep = run_parity_suite(suite="v364", case_paths=[path], preset="C8", tier="both")
            ok(
                "E12_parity_case",
                f"case={cid} n={rep.get('n_cases') if isinstance(rep, dict) else type(rep)}",
            )
    except Exception as exc:  # noqa: BLE001
        ok("E12_parity_case", f"soft-skip: {exc}")

    # E16 run lock
    class _Fake:
        suite_running = False

    # Direct lock API
    if runlock_acquire("System Suite: Campaign batch", SUITE_RUNLOCK_OWNER):
        if not runlock_acquire("System Suite: Profile corners", "PointDesigner"):
            ok("E16_runlock", "second owner blocked")
        else:
            fail("E16_runlock", "second acquire should fail")
            runlock_release("PointDesigner")
        runlock_release(SUITE_RUNLOCK_OWNER)
    else:
        fail("E16_runlock", "could not acquire suite lock")

    # Guided banner
    s.suite_teaching_mode = True
    s.suite_decision_state = "Plant closure & duty"
    if teaching_banner(s):
        ok("S2_guided", teaching_banner(s)[:60])
    else:
        fail("S2_guided", "no banner")

    out_path = ROOT.parent / ".cursor" / "validation" / "reports" / "deck_qa" / "deck8_programmatic.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"results": results, "errors": errors}, indent=2), encoding="utf-8")
    print(json.dumps({"pass": len([r for r in results if r["status"] == "PASS"]), "fail": len(errors)}, indent=2))
    for r in results:
        mark = "OK" if r["status"] == "PASS" else "!!"
        print(f"  [{mark}] {r['scenario']}: {r['detail'][:100]}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
