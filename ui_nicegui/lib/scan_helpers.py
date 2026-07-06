"""Scan Lab helpers — cartography runner and report summaries."""
from __future__ import annotations

import json
import time
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple

SCAN_VARS_2D: List[Tuple[str, str]] = [
    ("R0_m", "R0 (m)"),
    ("a_m", "a (m)"),
    ("Bt_T", "B0 (T)"),
    ("Ip_MA", "Ip (MA)"),
    ("fG", "fG (-)"),
    ("Paux_MW", "Paux (MW)"),
    ("kappa", "kappa (-)"),
    ("Ti_keV", "Ti (keV)"),
]

SCAN_VAR_KEYS = [k for k, _ in SCAN_VARS_2D]
SCAN_VAR_LABELS = {k: v for k, v in SCAN_VARS_2D}


def _attr(base, key: str, default: float) -> float:
    try:
        return float(getattr(base, key))
    except Exception:
        return float(default)


def estimate_eval_count(nx: int, ny: int) -> int:
    return max(1, int(nx)) * max(1, int(ny))


def baseline_axis_values(base, x_key: str, y_key: str) -> dict:
    return {
        "x_key": x_key,
        "y_key": y_key,
        "x_val": _attr(base, x_key, float("nan")),
        "y_val": _attr(base, y_key, float("nan")),
    }


def default_scan_bounds(base, x_key: str, y_key: str) -> Tuple[float, float, float, float]:
    bx = _attr(base, x_key, 1.0)
    by = _attr(base, y_key, 1.0)
    return 0.7 * bx, 1.3 * bx, 0.7 * by, 1.3 * by


def summarize_scan_report(rep: dict, *, intent: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(rep, dict):
        return {"loaded": False}
    intents = rep.get("intents") or ["Reactor"]
    it = str(intent or intents[0])
    nar_all = rep.get("narrative") or {}
    nar_int = (nar_all.get("intents") or {}) if isinstance(nar_all, dict) else {}
    n0 = nar_int.get(it, {}) if isinstance(nar_int, dict) else {}
    feasible = float(n0.get("blocking_feasible_rate", 0.0)) if isinstance(n0, dict) else 0.0
    top = (n0.get("dominance_ranked") or []) if isinstance(n0, dict) else []
    dom = (top[0].get("constraint") if top else None) or "(none)"
    cliff = float(n0.get("cliffiness_proxy", 0.0)) if isinstance(n0, dict) else 0.0
    if feasible >= 0.85:
        robustness = "Robust"
    elif feasible >= 0.55:
        robustness = "Balanced"
    elif feasible >= 0.25:
        robustness = "Brittle"
    else:
        robustness = "Knife-edge"
    return {
        "loaded": True,
        "intent": it,
        "dominant": str(dom),
        "feasible_rate": feasible,
        "feasible_pct": f"{feasible * 100:.0f}%",
        "robustness": robustness,
        "cliffiness": cliff,
        "n_points": int(rep.get("n_points") or 0),
        "x_key": str(rep.get("x_key") or ""),
        "y_key": str(rep.get("y_key") or ""),
        "dominance_ranked": top[:10] if isinstance(top, list) else [],
    }


def run_cartography_scan(
    base,
    *,
    x_key: str,
    y_key: str,
    x_lo: float,
    x_hi: float,
    y_lo: float,
    y_hi: float,
    nx: int,
    ny: int,
    intents: List[str],
    include_outputs: bool = False,
    base_override: Optional[dict] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict:
    import numpy as np

    try:
        from src.evaluator.core import Evaluator
        from tools.scan_cartography import build_cartography_report
    except ImportError:
        from evaluator.core import Evaluator  # type: ignore
        from tools.scan_cartography import build_cartography_report  # type: ignore

    base2 = base
    if isinstance(base_override, dict) and base_override:
        try:
            valid = set(getattr(base2, "__dict__", {}).keys())
            base2 = replace(base2, **{k: base_override[k] for k in base_override if k in valid})
        except Exception:
            pass

    ev = Evaluator(label="NiceGUI:Scan", cache_enabled=True, cache_max=4096)
    x_vals = list(np.linspace(float(x_lo), float(x_hi), int(nx)))
    y_vals = list(np.linspace(float(y_lo), float(y_hi), int(ny)))

    t0 = time.time()

    def _cb(done: int, total: int) -> None:
        if progress_cb:
            progress_cb(done, total)

    rep = build_cartography_report(
        evaluator=ev,
        base_inputs=base2,
        x_key=str(x_key),
        y_key=str(y_key),
        x_vals=x_vals,
        y_vals=y_vals,
        intents=list(intents or ["Reactor"]),
        include_outputs=bool(include_outputs),
        progress_cb=_cb,
    )
    rep["run_seconds"] = float(time.time() - t0)
    return rep


def build_scan_artifact_if_available(report: dict, settings: dict) -> Optional[dict]:
    try:
        from tools.scan_artifact_schema import build_scan_artifact, SCAN_SCHEMA_VERSION
    except ImportError:
        return None
    try:
        return build_scan_artifact(
            report=report,
            settings=settings,
            metadata=dict(report.get("metadata") or {}),
            reason_code="run_ok",
            freeze_statement=f"Scan Lab frozen (schema v{int(SCAN_SCHEMA_VERSION or 1)})",
        )
    except Exception:
        return None


def report_to_json_bytes(report: dict) -> bytes:
    return json.dumps(report, indent=2, default=str).encode("utf-8")


def dominance_table_rows(rep: dict, *, intent: Optional[str] = None) -> List[Dict[str, Any]]:
    summary = summarize_scan_report(rep, intent=intent)
    rows: List[Dict[str, Any]] = []
    for item in summary.get("dominance_ranked") or []:
        if not isinstance(item, dict):
            continue
        rows.append({
            "constraint": str(item.get("constraint") or ""),
            "fraction": item.get("fraction"),
            "count": item.get("count"),
        })
    return rows
