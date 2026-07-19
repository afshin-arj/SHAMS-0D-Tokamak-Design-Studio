"""Framework-agnostic verdict helpers (ported from ui/verdict_ui.py logic)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from constraints.unified import build_all_constraints, dominant_failing_constraint
    from constraints.constraints import constraint_is_hard
except ImportError:
    from src.constraints.unified import build_all_constraints, dominant_failing_constraint
    from src.constraints.constraints import constraint_is_hard

_SUBSYSTEM_GROUPS = {
    "magnets": ("magnet", "tf", "hts", "b_peak", "quench", "v400", "v288"),
    "exhaust": ("exhaust", "div", "detachment", "sol", "prad", "v399", "v380"),
    "neutronics": ("neutronics", "tbr", "dpa", "v403", "v401", "v407", "v392"),
    "control": ("control", "vs_", "vde", "rwm", "v398", "v374", "stability"),
    "transport": ("transport", "confinement", "h98", "tau", "v396", "v397"),
    "plant": ("plant", "economics", "availability", "v384", "v391", "capex"),
}


def _classify_subsystem(name: str) -> str:
    low = str(name).lower()
    for group, tokens in _SUBSYSTEM_GROUPS.items():
        if any(t in low for t in tokens):
            return group
    return "other"


def _subsystem_status_from_bundle(bundle) -> Dict[str, str]:
    status: Dict[str, str] = {k: "pass" for k in _SUBSYSTEM_GROUPS}
    status["other"] = "pass"
    for c in bundle.governance:
        if bool(getattr(c, "passed", True)):
            continue
        sub = _classify_subsystem(str(getattr(c, "name", "")))
        if constraint_is_hard(c):
            status[sub] = "fail"
        elif status.get(sub) != "fail":
            status[sub] = "warn"
    return status


def subsystem_status(out: Dict[str, Any]) -> Dict[str, str]:
    return _subsystem_status_from_bundle(build_all_constraints(out))


def tier_badges(out: Dict[str, Any]) -> Tuple[str, str]:
    q = out.get("Q_DT_eqv", out.get("Q", float("nan")))
    n20 = out.get("ne20", out.get("ne_bar_1e20_m3", float("nan")))
    ti = out.get("Ti_keV", float("nan"))
    try:
        qf = float(q)
        q_s = f"Q={qf:.2f}" if qf == qf else "Q=n/a"
    except (TypeError, ValueError):
        q_s = "Q=n/a"
    try:
        # n·T pressure proxy only — NOT Lawson n·T·τE (no τE in this product).
        nt = float(n20) * float(ti) if n20 == n20 and ti == ti else float("nan")
        nt_s = f"n·T≈{nt:.2e}" if nt == nt else "n·T=n/a"
    except (TypeError, ValueError):
        nt_s = "n·T=n/a"
    return q_s, nt_s


def verdict_summary(out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(out, dict) or not out:
        return {"loaded": False}
    bundle = build_all_constraints(out)
    dom = dominant_failing_constraint(bundle, use_governance=True)
    feasible = dom is None and bundle.governance_feasible
    q_s, nt_s = tier_badges(out)
    parity = bundle.parity if isinstance(bundle.parity, dict) else {}
    return {
        "loaded": True,
        "feasible": feasible,
        "verdict": "FEASIBLE" if feasible else "INFEASIBLE",
        "dominant": dom or "(none)",
        "q_label": q_s,
        "nt_label": nt_s,
        # Reuse the same bundle — avoid a second full constraint rebuild on every deck switch/helm refresh.
        "subsystems": _subsystem_status_from_bundle(bundle),
        "parity_aligned": bool(parity.get("pipelines_aligned", True)),
        "parity_n_mismatch": int(parity.get("n_pass_mismatch") or 0),
        "parity_n_gov": int(parity.get("n_governance") or 0),
        "parity_n_ledger": int(parity.get("n_ledger") or 0),
    }


def constraint_table_rows(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    bundle = build_all_constraints(out)
    rows: List[Dict[str, Any]] = []
    for c in bundle.governance:
        name = str(getattr(c, "name", ""))
        val = float(getattr(c, "value", float("nan")))
        lim = float(getattr(c, "limit", float("nan")))
        passed = bool(getattr(c, "passed", True))
        sense = str(getattr(c, "sense", "<="))
        residual = (val - lim) if sense == ">=" else (lim - val)
        rows.append({
            "name": name,
            "value": val,
            "limit": lim,
            "sense": sense,
            "passed": passed,
            "residual": residual,
        })
    rows.sort(key=lambda r: (r["passed"], -abs(r["residual"]) if r["residual"] == r["residual"] else 0))
    return rows
