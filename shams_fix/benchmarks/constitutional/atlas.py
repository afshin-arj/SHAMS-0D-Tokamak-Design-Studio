from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List
import json
import hashlib

from src.models.reference_machines import reference_catalog
from benchmarks.publication import run_point_designer_benchmarks as _pdbench

from .constitutions import intent_to_constitution, constitution_diff

@dataclass(frozen=True)
class AtlasResult:
    schema: str
    preset_key: str
    preset_label: str
    selected_intent: str
    native_intent: str
    constitution_selected: Dict[str, str]
    constitution_native: Dict[str, str]
    constitution_diff: List[Dict[str, str]]
    run: Dict[str, Any]
    stamp_sha256: str

def _stable_sha256(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def _design_intent_label(intent: str) -> str:
    return "Research" if intent.strip().lower().startswith("research") else "Reactor"

def evaluate_atlas_case(preset_key: str, selected_intent: str) -> AtlasResult:
    cat = reference_catalog()
    if preset_key not in cat:
        raise KeyError(f"Unknown preset_key: {preset_key}")
    ent = cat[preset_key]
    native_intent = str(ent.get("intent","")).strip() or "Research"
    preset_label = str(ent.get("label", preset_key))

    const_sel = intent_to_constitution(selected_intent)
    const_nat = intent_to_constitution(native_intent)
    diff = constitution_diff(const_sel, const_nat)

    case_id = f"ATLAS|{_design_intent_label(selected_intent).upper()}|{preset_key}"
    # Build PointInputs deterministically from preset + overrides (none)
    case_dict = {
        "title": case_id,
        "design_intent": _design_intent_label(selected_intent),
        "preset_key": preset_key,
        "inputs": {},
    }
    inp = _pdbench._build_inputs(case_dict)
    res = _pdbench.run_one(case_id, inp, design_intent=_design_intent_label(selected_intent))

    # Normalize runner output into an atlas-friendly run dict.
    # We keep this deterministic and purely derived from the benchmark artifact.
    art = (res.get("artifact") or {}) if isinstance(res, dict) else {}
    classified = (art.get("classification") or {}) if isinstance(art, dict) else {}
    blocking = list(classified.get("blocking") or [])
    diagnostic = list(classified.get("diagnostic") or [])
    verdict = "PASS"
    if blocking:
        verdict = "FAIL"
    elif diagnostic:
        verdict = "PASS+DIAG"

    cons_list = art.get("constraints") or []
    cdict: Dict[str, Any] = {}
    dom_constraint = ""
    dom_mech = ""
    worst_hard = None
    # Deterministic dominance: first blocking constraint if any, else first diagnostic, else tightest_hard.
    dom_candidate = (blocking[0] if blocking else (diagnostic[0] if diagnostic else ""))
    for c in cons_list:
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name", ""))
        if not nm:
            continue
        sev = str(c.get("severity", "hard"))
        margin = c.get("margin")
        try:
            m = float(margin) if margin is not None else None
        except Exception:
            m = None
        if sev.lower() == "hard" and isinstance(m, (int, float)):
            worst_hard = m if worst_hard is None else min(worst_hard, m)
        cdict[nm] = {
            "severity": sev,
            "margin": margin,
            "units": c.get("units", ""),
            "ok": bool(c.get("ok", True)),
            "mechanism_group": c.get("mechanism_group", c.get("mechanism", "")),
        }
        if nm == dom_candidate and not dom_constraint:
            dom_constraint = nm
            dom_mech = str(c.get("mechanism_group", c.get("mechanism", "")) or "")

    # Fallback dominance if no candidate picked
    if not dom_constraint:
        th = art.get("tightest_hard") or []
        if isinstance(th, list) and th:
            try:
                dom_constraint = str(th[0].get("name", ""))
            except Exception:
                dom_constraint = ""
        dom_mech = dom_mech or "GENERAL"

    run = {
        "schema": "atlas_run.v1",
        "verdict": verdict,
        "dominant_mechanism": dom_mech,
        "dominant_constraint": dom_constraint,
        "worst_hard_margin": worst_hard,
        "constraints": cdict,
        "artifact": art,
    }

    payload = {
        "preset_key": preset_key,
        "selected_intent": selected_intent,
        "native_intent": native_intent,
        "constitution_selected": const_sel,
        "constitution_native": const_nat,
        "constitution_diff": diff,
        "run": run,
    }
    stamp = _stable_sha256(payload)
    return AtlasResult(
        schema="tokamak_constitutional_atlas_result.v1",
        preset_key=preset_key,
        preset_label=preset_label,
        selected_intent=selected_intent,
        native_intent=native_intent,
        constitution_selected=const_sel,
        constitution_native=const_nat,
        constitution_diff=diff,
        run=run,
        stamp_sha256=stamp,
    )

def local_fragility_scan(preset_key: str, intent: str, knobs: Dict[str, Tuple[float,float,float]]) -> Dict[str, Any]:
    """Deterministic local neighborhood scan around a preset.

    knobs: dict of knob -> (center, rel_minus, rel_plus)
    Produces a small grid (up to 3x3) and reports pass fraction, mechanism stability, worst margin stats.
    """
    if not knobs:
        return {"schema":"local_fragility_scan.v1","pass_fraction":1.0,"mechanism_stable":True,
                "worst_margin_min":None,"worst_margin_median":None,"grid":[],
                "stamp_sha256": _stable_sha256({"preset_key":preset_key,"intent":intent,"knobs":{}})}

    cat = reference_catalog()
    if preset_key not in cat:
        raise KeyError(preset_key)
    base_inputs = dict(cat[preset_key]["inputs"].to_dict())

    grid_axes = []
    for k,(c,rm,rp) in knobs.items():
        vals = [c*(1-rm), c, c*(1+rp)]
        grid_axes.append((k, vals))
    # keep it small/deterministic
    grid_axes = grid_axes[:2]

    k1, v1 = grid_axes[0]
    if len(grid_axes)==1:
        k2, v2 = None, [None]
    else:
        k2, v2 = grid_axes[1]

    results=[]
    for a in v1:
        for b in v2:
            inputs = dict(base_inputs)
            inputs[k1]=float(a)
            if k2:
                inputs[k2]=float(b)

            case_id = f"FRAG|{_design_intent_label(intent).upper()}|{preset_key}|{k1}"
            case_dict = {
                "title": case_id,
                "design_intent": _design_intent_label(intent),
                "preset_key": preset_key,
                "inputs": inputs,
            }
            inp = _pdbench._build_inputs(case_dict)
            res = _pdbench.run_one(case_id, inp, design_intent=_design_intent_label(intent))
            art = (res.get("artifact") or {}) if isinstance(res, dict) else {}
            classified = (art.get("classification") or {}) if isinstance(art, dict) else {}
            blocking = list(classified.get("blocking") or [])

            hard_ok = (len(blocking) == 0)
            worst = None
            mech = ""
            dom = blocking[0] if blocking else ""

            for c in (art.get("constraints") or []):
                if not isinstance(c, dict):
                    continue
                sev = str(c.get("severity", "hard")).lower()
                m = c.get("margin")
                if sev == "hard" and isinstance(m, (int, float)):
                    worst = m if worst is None else min(worst, m)
                if dom and str(c.get("name", "")) == dom and not mech:
                    mech = str(c.get("mechanism_group", c.get("mechanism", "")) or "")

            results.append({"ok": hard_ok, "worst_margin": worst, "mechanism": mech or "GENERAL", "dominant_constraint": dom or ""})

    pass_frac = sum(1 for r in results if r["ok"])/max(1,len(results))
    mechs = [r["mechanism"] for r in results if r.get("mechanism")]
    mech_stable = (len(set(mechs))<=1) if mechs else True
    worsts=[r["worst_margin"] for r in results if isinstance(r["worst_margin"],(int,float))]
    worst_min=min(worsts) if worsts else None
    worst_med=sorted(worsts)[len(worsts)//2] if worsts else None

    payload={"preset_key":preset_key,"intent":intent,"knobs":knobs,"results":results,"pass_fraction":pass_frac}
    return {"schema":"local_fragility_scan.v1","pass_fraction":pass_frac,"mechanism_stable":mech_stable,
            "worst_margin_min":worst_min,"worst_margin_median":worst_med,"grid":results,"stamp_sha256":_stable_sha256(payload)}
