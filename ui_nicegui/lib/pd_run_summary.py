"""Deterministic run summary for Point Designer artifacts (Streamlit parity)."""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from constraints.constraints import evaluate_constraints
except ImportError:
    from src.constraints.constraints import evaluate_constraints


def compute_run_summary_from_out(out: Dict[str, Any]) -> Dict[str, Any]:
    """UI-safe run summary from evaluator outputs — independent of active Telemetry view."""
    try:
        cons = evaluate_constraints(out or {})
    except Exception:
        cons = []

    hard = []
    for c in cons or []:
        try:
            if str(getattr(c, "severity", "hard")).strip().lower() == "hard":
                hard.append(c)
        except Exception:
            pass

    try:
        hard_sorted = sorted(hard, key=lambda c: float(getattr(c, "margin", float("inf"))))
    except Exception:
        hard_sorted = list(hard)

    tight: List[Dict[str, Any]] = []
    for c in hard_sorted[:8]:
        try:
            tight.append(
                {
                    "name": str(getattr(c, "name", "")),
                    "passed": bool(getattr(c, "passed", False)),
                    "margin_frac": float(getattr(c, "margin", float("nan"))),
                    "value": getattr(c, "value", None),
                    "limit": getattr(c, "limit", None),
                    "units": getattr(c, "units", None),
                    "sense": getattr(c, "sense", None),
                    "group": getattr(c, "group", "general"),
                }
            )
        except Exception:
            pass

    closure = float("nan")
    try:
        pin = float(out.get("Pin_MW", float("nan")))
        ploss = float(out.get("Ploss_MW", float("nan")))
        if pin == pin and ploss == ploss:
            closure = pin - ploss
    except Exception:
        pass

    return {
        "headline": {
            "Q_DT_eqv": float(out.get("Q_DT_eqv", float("nan"))) if isinstance(out, dict) else float("nan"),
            "H98": float(out.get("H98", float("nan"))) if isinstance(out, dict) else float("nan"),
            "P_net_e_MW": float(out.get("P_net_e_MW", float("nan"))) if isinstance(out, dict) else float("nan"),
        },
        "power_closure_MW": closure,
        "tightest_hard_constraints": tight,
    }
