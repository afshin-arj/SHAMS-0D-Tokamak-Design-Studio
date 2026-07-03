"""Verdict-first UI components (UI Phases A & D)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

try:
    from constraints.unified import build_all_constraints, dominant_failing_constraint
    from constraints.constraints import constraint_is_hard
except ImportError:
    from src.constraints.unified import build_all_constraints, dominant_failing_constraint
    from src.constraints.constraints import constraint_is_hard

# Dark-mode-safe verdict palette
_VERDICT_COLORS = {
    "pass": "#1b7f3a",
    "warn": "#b8860b",
    "fail": "#c0392b",
    "neutral": "#5c6b7a",
}

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
    grp = str(getattr(name, "group", "") or "").lower()
    for group in _SUBSYSTEM_GROUPS:
        if group in grp:
            return group
    return "other"


def _subsystem_status(bundle) -> Dict[str, str]:
    status: Dict[str, str] = {k: "pass" for k in _SUBSYSTEM_GROUPS}
    status["other"] = "pass"
    for c in bundle.governance:
        if not constraint_is_hard(c):
            continue
        if bool(getattr(c, "passed", True)):
            continue
        sub = _classify_subsystem(str(getattr(c, "name", "")))
        status[sub] = "fail"
    for c in bundle.governance:
        if not constraint_is_hard(c):
            continue
        if bool(getattr(c, "passed", True)):
            continue
        sub = _classify_subsystem(str(getattr(c, "name", "")))
        if status.get(sub) != "fail":
            status[sub] = "warn"
    return status


def _chip_html(label: str, status: str) -> str:
    color = _VERDICT_COLORS.get(status, _VERDICT_COLORS["neutral"])
    return (
        f'<span style="display:inline-block;padding:4px 10px;margin:2px 4px;border-radius:12px;'
        f'background:{color}22;border:1px solid {color};color:{color};font-size:0.85rem;">'
        f'{label}</span>'
    )


def render_feasibility_strip(out: Dict[str, Any], *, key_prefix: str = "feas") -> None:
    """Horizontal subsystem feasibility chips (Phase A)."""
    if not out:
        st.caption("No evaluation outputs — run Point Designer first.")
        return
    bundle = build_all_constraints(out)
    status = _subsystem_status(bundle)
    chips = "".join(
        _chip_html(name.replace("_", " ").title(), status.get(name, "pass"))
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant")
    )
    st.markdown(f'<div style="line-height:2.2">{chips}</div>', unsafe_allow_html=True)
    if not bundle.parity.get("pipelines_aligned", True):
        st.caption(
            f"Constraint pipeline parity: {bundle.parity.get('n_pass_mismatch', 0)} pass mismatches "
            f"({bundle.parity.get('n_governance')} gov / {bundle.parity.get('n_ledger')} ledger)."
        )


def render_overlay_failure_panel(out: Dict[str, Any], *, key_prefix: str = "ovl") -> None:
    """Surface overlay *_error keys and disabled include_* flags (Phase A)."""
    if not isinstance(out, dict):
        return
    errors = {k: out[k] for k in sorted(out) if k.endswith("_error") and out.get(k)}
    disabled = [
        k for k in sorted(out)
        if k.startswith("include_") and out.get(k) in (0, 0.0, False) and f"{k.replace('include_', '')}" 
    ]
    warnings = out.get("_authority_warnings") or []
    if not errors and not warnings:
        return
    with st.expander("Overlay authority status", expanded=bool(errors)):
        if errors:
            st.markdown("**Overlay errors**")
            for k, v in errors.items():
                st.error(f"`{k}`: {v}")
        if warnings:
            st.markdown("**Authority warnings**")
            for w in warnings:
                st.warning(str(w))


def _tier_badges(out: Dict[str, Any]) -> Tuple[str, str]:
    q = out.get("Q_DT_eqv", out.get("Q", float("nan")))
    n20 = out.get("ne20", out.get("ne_bar_1e20_m3", float("nan")))
    ti = out.get("Ti_keV", float("nan"))
    try:
        qf = float(q)
        q_s = f"Q={qf:.2f}" if qf == qf else "Q=n/a"
    except (TypeError, ValueError):
        q_s = "Q=n/a"
    try:
        nt = float(n20) * float(ti) if n20 == n20 and ti == ti else float("nan")
        nt_s = f"nτE≈{nt:.2e}" if nt == nt else "nτE=n/a"
    except (TypeError, ValueError):
        nt_s = "nτE=n/a"
    return q_s, nt_s


def render_verdict_hero_strip(
    out: Dict[str, Any],
    *,
    run_summary: Optional[Dict[str, Any]] = None,
    key_prefix: str = "hero",
) -> None:
    """Point Designer verdict-first hero strip (Phase A)."""
    if not isinstance(out, dict) or not out:
        st.info("No evaluation loaded. Click **Evaluate Point** in Configure.")
        return

    bundle = build_all_constraints(out)
    dom = dominant_failing_constraint(bundle, use_governance=True)
    feasible = dom is None and bundle.governance_feasible
    color = _VERDICT_COLORS["pass"] if feasible else _VERDICT_COLORS["fail"]
    verdict = "FEASIBLE" if feasible else "INFEASIBLE"
    q_s, nt_s = _tier_badges(out)

    c1, c2, c3, c4 = st.columns([1.2, 1.5, 1.2, 1.2])
    with c1:
        st.markdown(
            f'<div style="font-size:1.4rem;font-weight:700;color:{color}">{verdict}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.metric("Dominant hard constraint", dom or "(none)")
    with c3:
        st.metric("Performance", q_s)
    with c4:
        st.metric("Triple product proxy", nt_s)

    render_feasibility_strip(out, key_prefix=f"{key_prefix}_feas")
    render_overlay_failure_panel(out, key_prefix=f"{key_prefix}_ovl")

    if run_summary and isinstance(run_summary, dict):
        pc = run_summary.get("power_closure_MW")
        if pc is not None:
            st.caption(f"Power closure (MW): {pc}")


def render_constraint_table_sorted(
    constraints: List[Any],
    *,
    use_governance: bool = True,
    key_prefix: str = "ctab",
) -> None:
    """Expandable constraint table sorted by residual (Phase D)."""
    rows = []
    for c in constraints:
        if use_governance:
            name = str(getattr(c, "name", ""))
            val = float(getattr(c, "value", float("nan")))
            lim = float(getattr(c, "limit", float("nan")))
            passed = bool(getattr(c, "passed", True))
            sense = str(getattr(c, "sense", "<="))
            residual = (val - lim) if sense == ">=" else (lim - val)
        else:
            name = str(c.name)
            val = float(c.value)
            lo, hi = c.lo, c.hi
            lim = hi if hi is not None else lo
            passed = bool(c.ok)
            residual = float(c.residual()) if hasattr(c, "residual") else 0.0
        rows.append(
            {
                "name": name,
                "value": val,
                "limit": lim,
                "residual": residual,
                "passed": passed,
            }
        )
    rows.sort(key=lambda r: (r["passed"], -abs(r["residual"])))
    if rows:
        import pandas as pd

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
