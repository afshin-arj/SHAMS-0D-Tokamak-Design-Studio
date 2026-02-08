from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

from benchmarks.constitutional.constitutions import intent_to_constitution

# Epoch-based feasibility is a SHAMS-safe extension: it does NOT modify physics truth.
# It reclassifies feasibility semantics across a small set of lifecycle epochs, using
# deterministic constitutions and the already-produced constraint ledger.

EPOCHS = ("Startup", "Nominal", "End-of-Life")

def _epoch_constitution(base_intent: str, epoch: str) -> Dict[str, str]:
    """Return a constitution clause map for a given intent and epoch.

    Clause values: required | hard | diagnostic | ignored
    """
    base = intent_to_constitution(base_intent)
    ep = epoch.strip().lower()

    # Default: epoch does not change semantics
    c = dict(base)

    # Reactor intent: allow staged requirements without time-marching.
    if str(base_intent).strip().lower().startswith("reactor"):
        if ep.startswith("startup"):
            # Startup: allow plant/fuel/lifetime gates to be diagnostic (not blocking).
            c.update({
                "net_electric": "diagnostic",
                "tritium_self_sufficiency": "diagnostic",
                "availability": "ignored",
                "lifetime_margin": "diagnostic",
                "detachment": "diagnostic",
            })
        elif ep.startswith("nominal"):
            # Nominal: full reactor constitution (base)
            c = dict(base)
        elif "end" in ep or "eol" in ep:
            # End-of-life: keep reactor requirements; emphasize durability.
            c.update({
                "lifetime_margin": "required",
                "availability": "required",
            })

    # Research intent: staged discipline is softer; EOL can still emphasize durability.
    else:
        if "end" in ep or "eol" in ep:
            c.update({
                "lifetime_margin": "hard",
            })

    return c

def _map_clause_to_constraint_names(clause_key: str) -> List[str]:
    """Map a constitution clause key to constraint name(s) as used in artifacts."""
    k = clause_key.strip().lower()
    if k == "q95":
        return ["q95", "q95_min"]
    if k == "greenwald":
        return ["fG"]
    if k == "beta_n":
        return ["betaN", "beta_N"]
    if k == "net_electric":
        return ["P_net", "Annual net"]
    if k == "tritium_self_sufficiency":
        return ["TBR", "T_inventory"]
    if k == "lifetime_margin":
        return ["FW dpa/y", "HTS lifetime"]
    if k == "availability":
        return ["Annual net"]
    # Detachment currently has no canonical constraint name across all models
    return []

def _apply_constitution_to_constraints(constraints: List[Dict[str, Any]], constitution: Dict[str, str]) -> List[Dict[str, Any]]:
    """Return a modified constraint list (JSON dicts) reflecting constitution semantics.

    - required/hard -> severity='hard'
    - diagnostic -> severity='soft'
    - ignored -> keep entry but mark severity='ignored' and exclude from feasibility accounting
    """
    out: List[Dict[str, Any]] = []
    # Build a lookup map name->clause_value for fast application
    name_to_clause: Dict[str, str] = {}
    for ck, cv in constitution.items():
        for nm in _map_clause_to_constraint_names(ck):
            name_to_clause[nm] = cv

    for c in constraints:
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name", ""))
        cc = dict(c)
        clause = name_to_clause.get(nm, None)
        if clause is None:
            out.append(cc)
            continue
        v = str(clause).strip().lower()
        if v in ("required", "hard"):
            cc["severity"] = "hard"
        elif v == "diagnostic":
            cc["severity"] = "soft"
        elif v == "ignored":
            cc["severity"] = "ignored"
        else:
            cc["severity"] = cc.get("severity", "hard")
        out.append(cc)
    return out

def _classify_constraints(constraints: List[Dict[str, Any]]) -> Tuple[List[str], List[str], Optional[float], str, str]:
    blocking: List[str] = []
    diagnostic: List[str] = []
    worst_hard: Optional[float] = None
    dom_constraint = ""
    dom_mech = ""

    # Determine tightest hard margin and capture first violated constraint as dominant.
    for c in constraints:
        if not isinstance(c, dict):
            continue
        sev = str(c.get("severity", "hard")).strip().lower()
        if sev == "ignored":
            continue
        nm = str(c.get("name", ""))
        ok = bool(c.get("ok", True))
        # margin may be None or non-numeric
        m = None
        try:
            m = float(c.get("margin")) if c.get("margin") is not None else None
        except Exception:
            m = None

        if sev == "hard":
            if (m is not None) and (m == m):
                worst_hard = m if worst_hard is None else min(worst_hard, m)
            if not ok:
                blocking.append(nm)
                if not dom_constraint:
                    dom_constraint = nm
                    dom_mech = str(c.get("mechanism_group", c.get("mechanism", "")) or "")
        elif sev == "soft":
            if not ok:
                diagnostic.append(nm)
                if not dom_constraint:
                    dom_constraint = nm
                    dom_mech = str(c.get("mechanism_group", c.get("mechanism", "")) or "")

    # If no violations, choose the tightest hard constraint as dominant.
    if not dom_constraint:
        tight_nm = ""
        tight_mech = ""
        tight_m = None
        for c in constraints:
            if not isinstance(c, dict):
                continue
            sev = str(c.get("severity", "hard")).strip().lower()
            if sev != "hard":
                continue
            nm = str(c.get("name", ""))
            try:
                m = float(c.get("margin")) if c.get("margin") is not None else None
            except Exception:
                m = None
            if m is None or not (m == m):
                continue
            if tight_m is None or m < tight_m:
                tight_m = m
                tight_nm = nm
                tight_mech = str(c.get("mechanism_group", c.get("mechanism", "")) or "")
        dom_constraint = tight_nm
        dom_mech = tight_mech

    return blocking, diagnostic, worst_hard, dom_constraint, dom_mech

def epoch_feasibility_from_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Build an epoch feasibility report derived from the artifact."""
    art = artifact if isinstance(artifact, dict) else {}
    intent = str((art.get("inputs") or {}).get("design_intent") or (art.get("meta") or {}).get("design_intent") or "").strip()
    if not intent:
        # fallback to 'Research' to be conservative about staged requirements
        intent = "Research"

    constraints = art.get("constraints") or []
    if not isinstance(constraints, list):
        constraints = []

    epochs: List[Dict[str, Any]] = []
    for ep in EPOCHS:
        const = _epoch_constitution(intent, ep)
        c2 = _apply_constitution_to_constraints(constraints, const)
        blocking, diagnostic, worst_hard, dom_c, dom_m = _classify_constraints(c2)
        verdict = "PASS"
        if blocking:
            verdict = "FAIL"
        elif diagnostic:
            verdict = "PASS+DIAG"
        epochs.append({
            "epoch": ep,
            "selected_intent": intent,
            "constitution": const,
            "verdict": verdict,
            "blocking": blocking,
            "diagnostic": diagnostic,
            "dominant_constraint": dom_c,
            "dominant_mechanism": dom_m,
            "worst_hard_margin_frac": worst_hard,
        })

    # Overall summary: worst epoch verdict ordering FAIL > PASS+DIAG > PASS
    order = {"FAIL": 2, "PASS+DIAG": 1, "PASS": 0}
    overall = max((e.get("verdict","PASS") for e in epochs), key=lambda v: order.get(v,0))
    return {
        "schema_version": "epoch_feasibility.v1",
        "overall": overall,
        "epochs": epochs,
    }
