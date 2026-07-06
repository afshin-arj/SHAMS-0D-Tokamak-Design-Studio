"""Human-readable summaries for Scan Lab insight tools."""

from __future__ import annotations

from typing import Any, Dict, List


def format_causality_trace(tr: dict) -> str:
    if not isinstance(tr, dict):
        return ""
    if tr.get("status") == "skipped":
        return str(tr.get("reason") or "Skipped.")
    lines: List[str] = []
    cname = tr.get("constraint") or tr.get("constraint_name")
    if cname:
        lines.append(f"**Constraint:** {cname}")
    m0 = tr.get("margin_baseline")
    if m0 is not None:
        lines.append(f"**Baseline margin:** {m0}")
    drivers = tr.get("drivers") or tr.get("knob_sensitivities") or []
    if isinstance(drivers, list) and drivers:
        lines.append("**Most influential knobs (local FD):**")
        for d in drivers[:8]:
            if not isinstance(d, dict):
                continue
            knob = d.get("knob") or d.get("param")
            dm = d.get("dmargin_dknob") or d.get("sensitivity")
            lines.append(f"- {knob}: d(margin)/d(knob) ≈ {dm}")
    note = tr.get("note") or tr.get("summary")
    if note:
        lines.append(str(note))
    return "\n".join(lines) if lines else ""


def format_insight_dict(out: dict, *, title: str = "") -> str:
    if not isinstance(out, dict):
        return ""
    if out.get("status") == "skipped":
        return str(out.get("reason") or "Skipped.")
    lines: List[str] = []
    if title:
        lines.append(f"**{title}**")
    for key in ("summary", "headline", "verdict", "regime", "label", "explanation"):
        if out.get(key):
            lines.append(f"**{key.replace('_', ' ').title()}:** {out[key]}")
    ranked = out.get("ranked") or out.get("drivers") or out.get("hotspots")
    if isinstance(ranked, list) and ranked:
        lines.append("**Ranked findings:**")
        for item in ranked[:10]:
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else ""


def format_projection_stability(out: dict) -> str:
    if not isinstance(out, dict) or not out.get("ok"):
        return str(out.get("reason") or "Off-plane check failed.")
    lines = [
        f"**Off-plane axis:** {out.get('z_key')} (z₀ ≈ {out.get('z0')})",
        f"**Dominance mode:** {out.get('mode_dominant')}",
        f"**Stability:** {float(out.get('dominant_stability', 0)):.0%} of samples share the same dominant limiter",
    ]
    if out.get("note"):
        lines.append(str(out["note"]))
    doms = out.get("dominant") or []
    if isinstance(doms, list) and doms:
        lines.append("**Dominant limiter along z sweep:** " + " → ".join(str(d) for d in doms[:7]))
    return "\n".join(lines)
