"""Compare deck helpers — artifact normalization and diff tables."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Mapping, Optional

COMPARE_METRICS: List[str] = [
    "Q",
    "Q_DT_eqv",
    "Pfus_total_MW",
    "P_e_net_MW",
    "P_recirc_MW",
    "beta_N",
    "q95_proxy",
    "H98",
    "tauE_eff_s",
    "fG",
    "TBR",
    "Bpeak_TF_T",
    "B_peak_T",
    "q_div_MW_m2",
    "neutron_wall_load_MW_m2",
    "sigma_vm_MPa",
    "COE_proxy_USD_per_MWh",
]


def _pick_output(out: dict, key: str) -> Any:
    if key in out:
        return out.get(key)
    aliases = {
        "Q": ["Q_DT_eqv"],
        "Q_DT_eqv": ["Q"],
        "Pfus_total_MW": ["P_fus_MW", "Pfus_MW"],
        "P_fus_MW": ["Pfus_total_MW"],
        "Bpeak_TF_T": ["B_peak_T"],
        "B_peak_T": ["Bpeak_TF_T"],
        "P_e_net_MW": ["P_net_e_MW", "Pnet_MWe", "Pe_net_MW", "P_net_MW"],
        "P_net_e_MW": ["P_e_net_MW", "Pnet_MWe", "Pe_net_MW", "P_net_MW"],
        "Pnet_MWe": ["P_e_net_MW", "P_net_e_MW", "Pe_net_MW"],
        "Pe_net_MW": ["P_e_net_MW", "P_net_e_MW", "P_net_MW"],
        "H98": ["H_IPB98y2", "H98y2", "H_IPB98"],
        "H_IPB98y2": ["H98", "H98y2", "H_IPB98"],
        "tauE_eff_s": ["tau_E_s", "tauE_s"],
        "tau_E_s": ["tauE_eff_s", "tauE_s"],
        "beta_N": ["betaN", "betaN_proxy"],
        "betaN": ["beta_N", "betaN_proxy"],
        "q95": ["q95_proxy"],
        "q95_proxy": ["q95"],
        "TBR": ["tbr_proxy_v403"],
    }
    for alt in aliases.get(key, []):
        if alt in out:
            return out.get(alt)
    return float("nan")


def normalize_compare_artifact(art: dict) -> dict:
    if not isinstance(art, dict):
        return {}
    out = dict(art.get("outputs") or {})
    cons = art.get("constraints")
    if (not cons) and out:
        try:
            from ui_nicegui.lib.verdict_core import constraint_table_rows

            cons = [
                {
                    "name": r["name"],
                    "residual": r["residual"],
                    "passed": r["passed"],
                    "value": r["value"],
                    "limit": r["limit"],
                }
                for r in constraint_table_rows(out)
            ]
        except Exception:
            cons = []
    inputs = art.get("inputs") if isinstance(art.get("inputs"), dict) else {}
    ih = art.get("inputs_hash")
    if not ih and inputs:
        ih = hashlib.sha256(
            json.dumps(inputs, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
    return {
        "outputs": out,
        "inputs": inputs,
        "constraints": list(cons or []),
        "inputs_hash": ih,
        "label": art.get("label") or art.get("deck") or "artifact",
        "kpis": art.get("kpis") if isinstance(art.get("kpis"), dict) else {},
        "scenario_delta": art.get("scenario_delta"),
        "model_cards": art.get("model_cards") if isinstance(art.get("model_cards"), dict) else {},
        "schema_version": art.get("schema_version"),
    }


def artifact_from_point(session) -> Optional[dict]:
    from ui_nicegui.lib.artifact_access import get_point_artifact_triple

    art, inp, out = get_point_artifact_triple(session)
    if not isinstance(out, dict) or not out:
        return None
    base = dict(art) if isinstance(art, dict) else {}
    base.setdefault("inputs", inp or dict(session.inputs))
    base.setdefault("outputs", out)
    base["label"] = "Point Designer"
    return normalize_compare_artifact(base)


def slot_meta(art: dict, *, label: str) -> dict:
    norm = normalize_compare_artifact(art)
    return {
        "ts_unix": float(time.time()),
        "inputs_hash": str(norm.get("inputs_hash") or ""),
        "label": label,
    }


def store_compare_slot(session, art: dict, slot: str, *, label: str, refresh: bool = True) -> None:
    """Store a normalized artifact in Compare slot A or B."""
    norm = normalize_compare_artifact(art)
    meta = slot_meta(norm, label=label)
    if str(slot).upper() == "A":
        session.cmp_slot_a = norm
        session.cmp_slot_a_meta = meta
        session.cmp_use_slot_a = True
    else:
        session.cmp_slot_b = norm
        session.cmp_slot_b_meta = meta
        session.cmp_use_slot_b = True
    if refresh:
        refresh_compare_if_active(session)


def refresh_compare_if_active(session) -> None:
    if getattr(session, "active_deck", None) == "Compare":
        from ui_nicegui.lib.navigation import refresh_active_deck

        refresh_active_deck()


def clear_compare_slots(session, *, refresh: bool = True) -> None:
    """Reset Compare slots and use flags; optionally refresh if Compare is active."""
    session.cmp_slot_a = None
    session.cmp_slot_b = None
    session.cmp_slot_a_meta = {}
    session.cmp_slot_b_meta = {}
    session.cmp_use_slot_a = False
    session.cmp_use_slot_b = False
    if refresh:
        refresh_compare_if_active(session)


def swap_compare_slots(session, *, refresh: bool = True) -> None:
    """Swap Compare slots A↔B including meta and use flags."""
    session.cmp_slot_a, session.cmp_slot_b = session.cmp_slot_b, session.cmp_slot_a
    session.cmp_slot_a_meta, session.cmp_slot_b_meta = (
        session.cmp_slot_b_meta,
        session.cmp_slot_a_meta,
    )
    session.cmp_use_slot_a, session.cmp_use_slot_b = (
        session.cmp_use_slot_b,
        session.cmp_use_slot_a,
    )
    if refresh:
        refresh_compare_if_active(session)


def open_compare_deck(session) -> None:
    """Navigate to Compare tab 1 after a cross-deck slot handoff."""
    session.cmp_workflow_step = "1 · Load A & B"
    from ui_nicegui.lib.navigation import switch_deck

    switch_deck("Compare", force=True)


def send_row_to_compare_slot(session, row: dict, slot: str, *, label: str) -> dict:
    """Evaluate a study row through frozen truth and store in a Compare slot."""
    art = build_compare_artifact(session, dict(row), label=label)
    store_compare_slot(session, art, slot, label=label)
    return art


def send_scan_probe_to_compare(
    session,
    rep: dict,
    cell: dict,
    slot: str,
    *,
    label: str = "Scan Lab probe",
) -> dict:
    """Build a Compare artifact from a Scan Lab probed cell."""
    from ui_nicegui.lib.scan_workbench_helpers import probe_promote_inputs

    cand = probe_promote_inputs(rep, cell)
    art = build_compare_artifact(session, cand, label=label)
    store_compare_slot(session, art, slot, label=label)
    return art


def bridge_cr_to_compare_slots(session) -> tuple[bool, bool]:
    """Copy Control Room scenario artifacts into Compare slots A (baseline) / B (variant)."""
    ok_a = ok_b = False
    base = getattr(session, "cr_scenario_base", None)
    var = getattr(session, "cr_scenario_variant", None)
    # refresh=False — caller may open_compare_deck (single remount)
    if isinstance(base, dict):
        store_compare_slot(session, base, "A", label="Control Room baseline", refresh=False)
        ok_a = True
    if isinstance(var, dict):
        store_compare_slot(session, var, "B", label="Control Room scenario", refresh=False)
        ok_b = True
    return ok_a, ok_b


def bridge_compare_slots_to_cr(session) -> tuple[bool, bool]:
    """Load Compare slots into Control Room scenario delta upload state."""
    ok_a = ok_b = False
    if isinstance(getattr(session, "cmp_slot_a", None), dict):
        session.cr_scenario_base = normalize_compare_artifact(session.cmp_slot_a)
        ok_a = True
    if isinstance(getattr(session, "cmp_slot_b", None), dict):
        session.cr_scenario_variant = normalize_compare_artifact(session.cmp_slot_b)
        ok_b = True
    return ok_a, ok_b


def metric_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table
    from ui_nicegui.lib.verdict_core import verdict_summary

    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    out_a = na.get("outputs") or {}
    out_b = nb.get("outputs") or {}
    feas_a = bool(verdict_summary(out_a).get("feasible"))
    feas_b = bool(verdict_summary(out_b).get("feasible"))
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for k in COMPARE_METRICS:
        if k in seen:
            continue
        a = _pick_output(out_a, k)
        b = _pick_output(out_b, k)
        if a != a and b != b:
            continue
        seen.add(k)
        a_disp = format_claim_kpi_for_table(k, a, feasible=feas_a, point_out=out_a)
        b_disp = format_claim_kpi_for_table(k, b, feasible=feas_b, point_out=out_b)
        d: Any = ""
        if feas_a and feas_b:
            try:
                d = float(b) - float(a)
            except (TypeError, ValueError):
                d = ""
        else:
            d = "— (diagnostic)"
        rows.append({"metric": k, "A": a_disp, "B": b_disp, "B-A": d})
    return rows


def constraint_rows(art: dict, *, limit: int = 20) -> List[Dict[str, Any]]:
    cons = normalize_compare_artifact(art).get("constraints") or []
    rows = [c for c in cons if isinstance(c, dict)]
    rows.sort(key=lambda r: float(r.get("residual", float("-inf")) if r.get("residual") == r.get("residual") else -1e30), reverse=True)
    return rows[:limit]


def subsystem_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    from ui_nicegui.lib.verdict_core import subsystem_status

    sa = subsystem_status(normalize_compare_artifact(art_a).get("outputs") or {})
    sb = subsystem_status(normalize_compare_artifact(art_b).get("outputs") or {})
    groups = sorted(set(sa.keys()) | set(sb.keys()))
    rows: List[Dict[str, Any]] = []
    for g in groups:
        a = str(sa.get(g, "pass"))
        b = str(sb.get(g, "pass"))
        changed = a != b
        rows.append({"subsystem": g, "A": a, "B": b, "changed": changed})
    rows.sort(key=lambda r: (0 if r.get("changed") else 1, str(r.get("subsystem"))))
    return rows


def apply_artifact_inputs(session, art: dict) -> int:
    """Copy PointInputs from a compare artifact into session.inputs."""
    inp = normalize_compare_artifact(art).get("inputs") or {}
    n = 0
    for k, v in inp.items():
        if k not in session.inputs:
            continue
        try:
            session.inputs[k] = float(v)
            n += 1
        except (TypeError, ValueError):
            pass
    return n


def build_compare_artifact(session, inputs_patch: dict, *, label: str) -> dict:
    """Evaluate inputs_patch through frozen truth and return a compare artifact.

    Acquires the global run lock so handoffs cannot overlap other truth evals.
    Mutates ``session.inputs`` only inside a try/finally restore window.
    """
    from dataclasses import asdict

    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.run_lock import (
        acquire as runlock_acquire,
        release as runlock_release,
        status as runlock_status,
        current_lease,
        lease_valid,
    )

    locked, task, is_owner = runlock_status("CompareHandoff")
    if locked:
        # Same-owner re-acquire is allowed by run_lock — refuse to prevent overlapping handoffs.
        raise RuntimeError(
            f"Busy: {task or 'evaluation'} — wait or force-clear from Helm."
            if not is_owner
            else "Compare handoff already in progress."
        )
    if not runlock_acquire(f"Compare handoff: {label}", "CompareHandoff"):
        raise RuntimeError("Could not acquire run lock — another evaluation is active.")
    lease = current_lease()

    saved = dict(session.inputs)
    try:
        for k, v in inputs_patch.items():
            if k in session.inputs and v is not None:
                try:
                    session.inputs[k] = float(v)
                except (TypeError, ValueError):
                    pass
        inp = session.build_point_inputs()
        out = ui_evaluate(inp, origin=f"NiceGUI:{label}")
        if not lease_valid(lease):
            raise RuntimeError("Run was force-cleared — discarding results.")
        return normalize_compare_artifact({"inputs": asdict(inp), "outputs": out, "label": label})
    finally:
        session.inputs = saved
        if lease_valid(lease):
            runlock_release("CompareHandoff", lease)


def summarize_comparison(art_a: dict, art_b: dict) -> Dict[str, Any]:
    from ui_nicegui.lib.verdict_core import verdict_summary

    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    sa = verdict_summary(na.get("outputs") or {})
    sb = verdict_summary(nb.get("outputs") or {})
    diffs = metric_diff_rows(art_a, art_b)
    top_delta = "-"
    top_val = 0.0
    for row in diffs:
        d = row.get("B-A")
        if isinstance(d, (int, float)) and d == d:
            if abs(float(d)) >= abs(top_val):
                top_val = float(d)
                top_delta = f"{row.get('metric')} ({top_val:+.3g})"
    return {
        "loaded": True,
        "verdict_a": sa.get("verdict", "n/a"),
        "verdict_b": sb.get("verdict", "n/a"),
        "feasible_a": bool(sa.get("feasible")),
        "feasible_b": bool(sb.get("feasible")),
        "dominant_a": sa.get("dominant", "-"),
        "dominant_b": sb.get("dominant", "-"),
        "q_a": sa.get("q_label", "-") if bool(sa.get("feasible")) else "— (diagnostic)",
        "q_b": sb.get("q_label", "-") if bool(sb.get("feasible")) else "— (diagnostic)",
        "h98_a": (
            _fmt_kpi((na.get("outputs") or {}).get("H98"))
            if bool(sa.get("feasible"))
            else "— (diagnostic)"
        ),
        "h98_b": (
            _fmt_kpi((nb.get("outputs") or {}).get("H98"))
            if bool(sb.get("feasible"))
            else "— (diagnostic)"
        ),
        "pfus_a": (
            _fmt_kpi(_pick_output(na.get("outputs") or {}, "Pfus_total_MW"))
            if bool(sa.get("feasible"))
            else "— (diagnostic)"
        ),
        "pfus_b": (
            _fmt_kpi(_pick_output(nb.get("outputs") or {}, "Pfus_total_MW"))
            if bool(sb.get("feasible"))
            else "— (diagnostic)"
        ),
        "mirage_a": bool((na.get("outputs") or {}).get("mirage_flag_v402")),
        "mirage_b": bool((nb.get("outputs") or {}).get("mirage_flag_v402")),
        "subsystems_a": sa.get("subsystems") or {},
        "subsystems_b": sb.get("subsystems") or {},
        "subsystem_diff": subsystem_diff_rows(art_a, art_b),
        "top_delta": top_delta,
        "n_metrics": len(diffs),
    }


def _fmt_kpi(v: Any) -> str:
    try:
        f = float(v)
        if f != f:
            return "-"
        return f"{f:.3g}"
    except (TypeError, ValueError):
        return "-"


def comparison_markdown(art_a: dict, art_b: dict) -> str:
    summary = summarize_comparison(art_a, art_b)
    rows = metric_diff_rows(art_a, art_b)
    lines = ["# SHAMS Artifact Comparison", "", "## Key metrics", ""]
    if not summary.get("feasible_a") or not summary.get("feasible_b"):
        lines.append(
            "> PHYS-KPI-001: Q / H98 / Pfus / P_net shown as diagnostic on INFEASIBLE slots — not design claims."
        )
        lines.append("")
    lines.append("| metric | A | B | B-A |")
    lines.append("| --- | --- | --- | --- |")
    for r in rows:
        lines.append(f"| {r.get('metric')} | {r.get('A')} | {r.get('B')} | {r.get('B-A')} |")
    lines.extend(["", "## Worst constraints (A)", ""])
    for c in constraint_rows(art_a):
        lines.append(f"- {c.get('name')}: residual={c.get('residual')}")
    lines.extend(["", "## Worst constraints (B)", ""])
    for c in constraint_rows(art_b):
        lines.append(f"- {c.get('name')}: residual={c.get('residual')}")
    inp = input_diff_rows(art_a, art_b)
    if inp:
        lines.extend(["", "## Changed inputs", ""])
        for r in inp:
            lines.append(f"- {r.get('field')}: A={r.get('A')} → B={r.get('B')}")
    return "\n".join(lines)


def _as_float(x: Any) -> float | None:
    try:
        v = float(x)
        if v != v:
            return None
        return v
    except (TypeError, ValueError):
        return None


def input_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    ia = na.get("inputs") or {}
    ib = nb.get("inputs") or {}
    rows: List[Dict[str, Any]] = []
    for k in sorted(set(ia.keys()) | set(ib.keys())):
        va = ia.get(k)
        vb = ib.get(k)
        if va != vb:
            rows.append({"field": k, "A": va, "B": vb})
    return rows


def numeric_output_diff_rows(
    art_a: dict, art_b: dict, *, limit: int = 60
) -> List[Dict[str, Any]]:
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key
    from ui_nicegui.lib.verdict_core import verdict_summary

    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    out_a = na.get("outputs") or {}
    out_b = nb.get("outputs") or {}
    feas_a = bool(verdict_summary(out_a).get("feasible"))
    feas_b = bool(verdict_summary(out_b).get("feasible"))
    keys = sorted(set(out_a.keys()) | set(out_b.keys()))
    rows: List[Dict[str, Any]] = []
    for k in keys:
        a = _as_float(out_a.get(k))
        b = _as_float(out_b.get(k))
        if a is None or b is None:
            continue
        d = b - a
        if abs(d) < 1e-12:
            continue
        frac = (d / a) if abs(a) > 1e-12 else None
        if is_claim_kpi_key(k):
            a_disp = format_claim_kpi_for_table(k, a, feasible=feas_a, point_out=out_a)
            b_disp = format_claim_kpi_for_table(k, b, feasible=feas_b, point_out=out_b)
            d_disp: Any = d if (feas_a and feas_b) else "— (diagnostic)"
            frac_disp: Any = frac if (feas_a and feas_b) else "— (diagnostic)"
            rows.append({"metric": k, "A": a_disp, "B": b_disp, "B-A": d_disp, "frac": frac_disp})
        else:
            rows.append({"metric": k, "A": a, "B": b, "B-A": d, "frac": frac})
    rows.sort(
        key=lambda r: abs(float(r.get("B-A", 0))) if isinstance(r.get("B-A"), (int, float)) else 0.0,
        reverse=True,
    )
    return rows[:limit]


def _constraint_severity(c: Mapping[str, Any]) -> str:
    sev = str(c.get("severity", "hard") or "hard").strip().lower()
    return sev or "hard"


def _constraint_any_failed(c: Mapping[str, Any]) -> bool:
    if not c:
        return False
    return bool(c.get("failed") or c.get("passed") is False)


def _constraint_hard_failed(c: Mapping[str, Any]) -> bool:
    """Hard fail only — soft/diagnostic fails must not read as hard new_failure."""
    return _constraint_any_failed(c) and _constraint_severity(c) == "hard"


def constraint_margin_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    ca = {c.get("name"): c for c in constraint_rows(art_a, limit=500) if c.get("name")}
    cb = {c.get("name"): c for c in constraint_rows(art_b, limit=500) if c.get("name")}
    names = sorted(set(ca.keys()) | set(cb.keys()))
    rows: List[Dict[str, Any]] = []
    for n in names:
        a = ca.get(n, {})
        b = cb.get(n, {})
        sev_a = _constraint_severity(a) if a else ""
        sev_b = _constraint_severity(b) if b else ""
        fa_any = _constraint_any_failed(a)
        fb_any = _constraint_any_failed(b)
        fa = _constraint_hard_failed(a)
        fb = _constraint_hard_failed(b)
        ma = a.get("margin", a.get("residual")) if a else None
        mb = b.get("margin", b.get("residual")) if b else None
        md = None
        try:
            if ma is not None and mb is not None:
                md = float(mb) - float(ma)
        except (TypeError, ValueError):
            md = None
        rows.append(
            {
                "name": n,
                "severity_A": sev_a or None,
                "severity_B": sev_b or None,
                "failed_A": fa,
                "failed_B": fb,
                "soft_failed_A": fa_any and not fa,
                "soft_failed_B": fb_any and not fb,
                "margin_A": ma,
                "margin_B": mb,
                "margin_delta": md,
                # Only hard→hard transitions count as new_failure (PHYS / feasibility honesty).
                "new_failure": fb and not fa,
            }
        )
    rows.sort(
        key=lambda r: (
            0 if r.get("new_failure") else 1,
            -(abs(float(r["margin_delta"])) if r.get("margin_delta") is not None else 0),
        )
    )
    return rows


def new_hard_failures_caption(
    *,
    feas_a: bool,
    feas_b: bool,
    n_new_fail: int,
) -> tuple[str, str]:
    """Compare constraints header: message + NiceGUI classes.

    Dual-INFEASIBLE with identical hard fails must not read as a green PASS-adjacent win.
    """
    if int(n_new_fail or 0) > 0:
        return (
            f"{int(n_new_fail)} new hard failure(s) in B relative to A.",
            "text-subtitle2 text-negative q-mb-sm",
        )
    if feas_a and feas_b:
        return (
            "No new hard constraint failures in B relative to A.",
            "text-caption text-positive q-mb-sm",
        )
    if not feas_a and not feas_b:
        return (
            "No new hard failures in B vs A — both slots remain INFEASIBLE (not a PASS).",
            "text-caption text-orange q-mb-sm",
        )
    return (
        "No new hard failures in B vs A — at least one slot is INFEASIBLE (not a PASS).",
        "text-caption text-orange q-mb-sm",
    )


def kpi_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key
    from ui_nicegui.lib.verdict_core import verdict_summary

    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    ka = na.get("kpis") or {}
    kb = nb.get("kpis") or {}
    if not isinstance(ka, dict):
        ka = {}
    if not isinstance(kb, dict):
        kb = {}
    feas_a = bool(verdict_summary(na.get("outputs") or {}).get("feasible"))
    feas_b = bool(verdict_summary(nb.get("outputs") or {}).get("feasible"))
    rows: List[Dict[str, Any]] = []
    for k in sorted(set(ka.keys()) | set(kb.keys())):
        a = ka.get(k)
        b = kb.get(k)
        if is_claim_kpi_key(k):
            a_disp = format_claim_kpi_for_table(k, a, feasible=feas_a, point_out=na.get("outputs") or {})
            b_disp = format_claim_kpi_for_table(k, b, feasible=feas_b, point_out=nb.get("outputs") or {})
            d: Any = "— (diagnostic)" if not (feas_a and feas_b) else ""
            if feas_a and feas_b:
                try:
                    d = float(b) - float(a)
                except (TypeError, ValueError):
                    d = ""
            rows.append({"kpi": k, "A": a_disp, "B": b_disp, "B-A": d})
        else:
            d = ""
            try:
                d = float(b) - float(a)
            except (TypeError, ValueError):
                pass
            rows.append({"kpi": k, "A": a, "B": b, "B-A": d})
    return rows


def embedded_scenario_delta(art_b: dict) -> Any:
    nb = normalize_compare_artifact(art_b)
    raw = art_b if isinstance(art_b, dict) else {}
    return raw.get("scenario_delta") or nb.get("scenario_delta")


def structural_diff_report(art_a: dict, art_b: dict) -> dict | None:
    try:
        from shams_io.structural_diff import structural_diff

        return structural_diff(
            new_artifact=normalize_compare_artifact(art_b),
            old_artifact=normalize_compare_artifact(art_a),
        )
    except Exception:
        return None


def comparison_json_bundle(art_a: dict, art_b: dict) -> dict:
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_scenario_delta_export

    summary = summarize_comparison(art_a, art_b)
    # Row builders already watermark claim KPI cells per-slot feasibility.
    key_metrics = metric_diff_rows(art_a, art_b)
    kpi_diff = kpi_diff_rows(art_a, art_b)
    all_deltas = numeric_output_diff_rows(art_a, art_b, limit=200)
    note = None
    if not summary.get("feasible_a") or not summary.get("feasible_b"):
        note = (
            "PHYS-KPI-001: claim KPI values in key_metrics / kpi_diff / all_output_deltas "
            "on INFEASIBLE slots are — (diagnostic) — not design claims."
        )
    sd = embedded_scenario_delta(art_b)
    if isinstance(sd, dict):
        sd = watermark_scenario_delta_export(
            sd,
            feasible_base=bool(summary.get("feasible_a")),
            feasible_scenario=bool(summary.get("feasible_b")),
        )
    return {
        "summary": summary,
        "phys_kpi_note": note,
        "key_metrics": key_metrics,
        "all_output_deltas": all_deltas,
        "constraint_margins": constraint_margin_diff_rows(art_a, art_b),
        "subsystem_diff": subsystem_diff_rows(art_a, art_b),
        "input_changes": input_diff_rows(art_a, art_b),
        "kpi_diff": kpi_diff,
        "scenario_delta": sd,
        "structural_diff": structural_diff_report(art_a, art_b),
    }
