"""Transport & confinement credibility certification (v376.0.0).

This module is *governance-only*: it derives a deterministic certification summary
from an already-produced Systems artifact (inputs/outputs). It performs **no
truth evaluation**, no iteration, and no solver work.

Scope
-----
Certifies that the reported/required confinement performance is within a
conservative credibility envelope.

Primary metric:
  - H98: confinement multiplier relative to IPB98(y,2).

If H98 is absent, we attempt to reconstruct it from optional tauE terms when
available:
  - H98 ≈ tauE_req_s / tauE_98_s

Intent policy (conservative, explicit):
  - Reactor intent: tighter credibility envelope
  - Research intent: looser (still bounded) envelope

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple


def _f(d: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(d.get(key, default))
    except Exception:
        return float(default)


def _s(d: Dict[str, Any], key: str, default: str = "") -> str:
    try:
        v = d.get(key, default)
        return "" if v is None else str(v)
    except Exception:
        return str(default)


def _design_intent(inputs: Dict[str, Any]) -> str:
    # Systems artifacts often store human label in inputs['design_intent'].
    v = _s(inputs, "design_intent", "").strip().lower()
    if not v:
        return "unknown"
    if "react" in v:
        return "reactor"
    if "research" in v:
        return "research"
    return v


def _reconstruct_H98(outputs: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    meta: Dict[str, Any] = {}

    H98 = _f(outputs, "H98", float("nan"))
    if math.isfinite(H98):
        meta["source"] = "outputs.H98"
        return H98, meta

    # Optional tauE terms (v376 release notes): tauE_req_s and tauE_98_s.
    tau_req = _f(outputs, "tauE_req_s", float("nan"))
    tau_98 = _f(outputs, "tauE_98_s", float("nan"))
    if math.isfinite(tau_req) and math.isfinite(tau_98) and tau_98 > 0:
        meta["source"] = "outputs.tauE_req_s/outputs.tauE_98_s"
        return float(tau_req / tau_98), meta

    # Fall back: legacy naming if present.
    tau_eff = _f(outputs, "tauE_eff_s", _f(outputs, "tauE_s", float("nan")))
    tau_ipb = _f(outputs, "tauIPB98_s", float("nan"))
    if math.isfinite(tau_eff) and math.isfinite(tau_ipb) and tau_ipb > 0:
        meta["source"] = "outputs.tauE_eff_s/outputs.tauIPB98_s"
        return float(tau_eff / tau_ipb), meta

    meta["source"] = "unavailable"
    return float("nan"), meta


@dataclass(frozen=True)
class CredibilityEnvelope:
    intent: str
    H98_max: float
    H98_warn_frac: float


def _envelope_for_intent(intent: str) -> CredibilityEnvelope:
    """Return conservative credibility envelope.

    Notes:
      - Values are explicit policy defaults (not empirical fits).
      - Tighten/loosen only via explicit future governance.
    """
    intent = (intent or "unknown").strip().lower()
    if intent == "reactor":
        return CredibilityEnvelope(intent="reactor", H98_max=1.30, H98_warn_frac=0.90)
    if intent == "research":
        return CredibilityEnvelope(intent="research", H98_max=1.60, H98_warn_frac=0.90)
    # Unknown: choose the tighter envelope for safety.
    return CredibilityEnvelope(intent="unknown", H98_max=1.30, H98_warn_frac=0.90)


def _classify(H98: float, env: CredibilityEnvelope) -> str:
    if not math.isfinite(H98):
        return "UNKNOWN"
    if H98 <= env.H98_max * env.H98_warn_frac:
        return "credible"
    if H98 <= env.H98_max:
        return "near-edge"
    return "super-credible-viol"


def certify_transport_confinement(
    *,
    outputs: Dict[str, Any],
    inputs: Dict[str, Any],
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
    probe_frac: float = 0.01,
) -> Dict[str, Any]:
    """Create a deterministic certification object.

    probe_frac is used for a tiny perturbation fragility probe:
      - evaluate whether +/- probe_frac on H98 changes the classification.

    Purely algebraic; does not re-run truth.
    """
    probe_frac = float(probe_frac)
    if not (0.0 <= probe_frac <= 0.1):
        probe_frac = 0.01

    intent = _design_intent(inputs)
    env = _envelope_for_intent(intent)
    H98, Hmeta = _reconstruct_H98(outputs)

    cls0 = _classify(H98, env)

    frag = {
        "probe_frac": probe_frac,
        "H98_minus": float("nan"),
        "H98_plus": float("nan"),
        "class_minus": "UNKNOWN",
        "class_plus": "UNKNOWN",
        "class_flips": False,
    }
    if math.isfinite(H98) and H98 > 0:
        Hm = H98 * (1.0 - probe_frac)
        Hp = H98 * (1.0 + probe_frac)
        cm = _classify(Hm, env)
        cp = _classify(Hp, env)
        frag.update(
            {
                "H98_minus": float(Hm),
                "H98_plus": float(Hp),
                "class_minus": str(cm),
                "class_plus": str(cp),
                "class_flips": bool((cm != cls0) or (cp != cls0)),
            }
        )

    cert: Dict[str, Any] = {
        "authority": {
            "name": "Transport & Confinement Credibility Certification",
            "version": "v376.0.0",
            "scope": "governance-only; no truth execution",
        },
        "provenance": {
            "run_id": (run_id or ""),
            "inputs_hash": (inputs_hash or ""),
        },
        "intent": intent,
        "policy": {
            "H98_max": float(env.H98_max),
            "H98_warn_frac": float(env.H98_warn_frac),
            "note": "Explicit conservative credibility envelope (intent-aware).",
        },
        "metrics": {
            "H98": float(H98),
            "H98_source": str(Hmeta.get("source", "")),
            "tauE_req_s": float(_f(outputs, "tauE_req_s", float("nan"))),
            "tauE_98_s": float(_f(outputs, "tauE_98_s", float("nan"))),
            "tauE_eff_s": float(_f(outputs, "tauE_eff_s", float("nan"))),
            "tauIPB98_s": float(_f(outputs, "tauIPB98_s", float("nan"))),
        },
        "classification": {
            "H98_class": str(cls0),
        },
        "fragility_probe": frag,
    }
    return cert


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[List[List[Any]], List[str]]:
    """Rows for reviewer-friendly UI tables."""
    m = cert.get("metrics") if isinstance(cert.get("metrics"), dict) else {}
    p = cert.get("policy") if isinstance(cert.get("policy"), dict) else {}
    c = cert.get("classification") if isinstance(cert.get("classification"), dict) else {}
    f = cert.get("fragility_probe") if isinstance(cert.get("fragility_probe"), dict) else {}

    rows: List[List[Any]] = []
    rows.append(["Intent", cert.get("intent", "")])
    rows.append(["H98", m.get("H98", float("nan"))])
    rows.append(["H98 source", m.get("H98_source", "")])
    rows.append(["H98 max (policy)", p.get("H98_max", float("nan"))])
    rows.append(["H98 class", c.get("H98_class", "UNKNOWN")])
    rows.append(["Probe frac", f.get("probe_frac", float("nan"))])
    rows.append(["Class flips under probe", bool(f.get("class_flips", False))])
    return rows, ["Field", "Value"]
