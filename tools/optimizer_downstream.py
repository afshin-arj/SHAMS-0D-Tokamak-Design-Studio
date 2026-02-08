from __future__ import annotations
"""Optimizer Downstream Report (v118)

Goal:
- Accept multiple external optimizer proposals (points)
- SHAMS re-evaluates each proposal (v115) -> run artifacts
- Optionally run tolerance envelopes (v117) per feasible candidate (bounded samples)
- Build design candidates (v113) from feasible proposals
- Apply preferences + Pareto sets (v114)
- Export a single report zip that makes external optimizers downstream of SHAMS.

No optimization occurs in SHAMS. SHAMS only evaluates, annotates, filters, and packages.
"""

from typing import Any, Dict, List, Optional, Tuple
import time, json, hashlib, zipfile
from io import BytesIO

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def template_batch_response(version: str = "v118") -> Dict[str, Any]:
    return {
        "kind": "shams_optimizer_batch_response",
        "version": version,
        "created_utc": _created_utc(),
        "proposals": [
            {
                "kind": "shams_optimizer_response",
                "version": "v115",
                "created_utc": _created_utc(),
                "proposed_inputs": {
                    "R0_m": 2.0, "a_m": 0.65, "kappa": 1.8,
                    "Bt_T": 12.0, "Ip_MA": 8.0,
                    "Ti_keV": 15.0, "fG": 0.8, "Paux_MW": 20.0,
                },
                "confidence": None,
                "assumptions": ["Batch example; SHAMS will validate."],
                "violations": [],
                "notes": [],
            }
        ],
        "notes": ["Batch wrapper for multiple optimizer proposals."],
    }

def evaluate_optimizer_batch(
    *,
    batch_payload: Dict[str, Any],
    tolerance_spec: Optional[Dict[str, Any]] = None,
    max_envelope_samples: int = 24,
    max_candidates: int = 12,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a downstream report object including artifacts, candidates, preferences, and packs."""
    if not (isinstance(batch_payload, dict) and batch_payload.get("kind") == "shams_optimizer_batch_response"):
        raise ValueError("expected shams_optimizer_batch_response dict")

    proposals = batch_payload.get("proposals", [])
    if not isinstance(proposals, list):
        proposals = []

    from tools.optimizer_interface import evaluate_optimizer_proposal
    from tools.tolerance_envelope import evaluate_tolerance_envelope, template_tolerance_spec
    from tools.design_decision_layer import build_design_candidates, build_design_decision_pack
    from tools.preference_layer import template_preferences, annotate_candidates_with_preferences, pareto_sets_from_annotations

    # 1) evaluate all proposals via v115
    evaluated = []
    contexts = []
    for p in proposals:
        if not isinstance(p, dict) or p.get("kind") != "shams_optimizer_response":
            continue
        out = evaluate_optimizer_proposal(p, meta={"mode":"optimizer_batch_v118"})
        evaluated.append(out["artifact"])
        contexts.append(out["context"])

    # 2) filter feasible artifacts
    feasible_artifacts = []
    for art in evaluated:
        cs = art.get("constraints_summary", {})
        feas = cs.get("feasible") if isinstance(cs, dict) else None
        if feas is True:
            feasible_artifacts.append(art)

    # 3) tolerance envelopes (optional; only for feasible artifacts)
    spec = tolerance_spec if isinstance(tolerance_spec, dict) else template_tolerance_spec()
    envelopes = []
    for art in feasible_artifacts[:max_candidates]:
        try:
            rep = evaluate_tolerance_envelope(baseline_artifact=art, tolerance_spec=spec, version="v117", max_samples=int(max_envelope_samples))
            envelopes.append(rep)
        except Exception:
            # If envelope fails (rare), skip rather than fail the whole report
            continue

    # 4) build design candidates from feasible run artifacts (v113)
    candidates = build_design_candidates(artifacts=feasible_artifacts[:max_candidates], max_candidates=max_candidates)

    # 5) preferences + Pareto (v114)
    prefs = preferences if isinstance(preferences, dict) else template_preferences()
    ann = annotate_candidates_with_preferences(candidates, prefs)
    pareto = pareto_sets_from_annotations(ann)

    # 6) decision pack with justification
    justification = {
        "kind":"shams_decision_justification_v118",
        "created_utc": ann.get("created_utc"),
        "preferences": prefs,
        "pareto_sets": pareto,
        "n_candidates": len(candidates),
        "n_proposals": len(evaluated),
        "n_feasible": len(feasible_artifacts),
        "tolerance_spec": spec,
        "n_envelopes": len(envelopes),
        "disclaimer": "External optimizer proposals are downstream. SHAMS re-evaluates and annotates; no optimization occurs in SHAMS.",
    }
    decision_pack = build_design_decision_pack(candidates=candidates, version="v118", decision_justification=justification)

    report = {
        "kind": "shams_optimizer_downstream_report_v118",
        "created_utc": _created_utc(),
        "batch_meta": {
            "n_proposals_in": len(proposals),
            "n_evaluated": len(evaluated),
            "n_feasible": len(feasible_artifacts),
        },
        "evaluated_artifacts": evaluated,
        "import_contexts": contexts,
        "tolerance_envelopes": envelopes,
        "candidates": candidates,
        "preferences": prefs,
        "pareto_sets": pareto,
        "decision_justification": justification,
        "decision_pack_manifest": decision_pack["manifest"],
        "notes": ["v118 downstream report: optimizers propose; SHAMS validates and decides."],
    }

    return {"report": report, "decision_pack_zip_bytes": decision_pack["zip_bytes"]}

def build_downstream_report_zip(
    *,
    report_obj: Dict[str, Any],
    decision_pack_zip_bytes: bytes,
) -> Dict[str, Any]:
    created = _created_utc()
    rep_bytes = json.dumps(report_obj, indent=2, sort_keys=True).encode("utf-8")
    pack_bytes = bytes(decision_pack_zip_bytes)

    manifest = {
        "kind":"shams_optimizer_downstream_zip_manifest_v118",
        "created_utc": created,
        "files": {
            "optimizer_downstream_report_v118.json": {"sha256": _sha256_bytes(rep_bytes), "bytes": len(rep_bytes)},
            "design_decision_pack_v118.zip": {"sha256": _sha256_bytes(pack_bytes), "bytes": len(pack_bytes)},
        },
        "notes":[
            "Single export: evaluated proposals + envelopes + candidates + preferences + Pareto + decision pack.",
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest["files"]["manifest.json"] = {"sha256": _sha256_bytes(manifest_bytes), "bytes": len(manifest_bytes)}

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("optimizer_downstream_report_v118.json", rep_bytes)
        z.writestr("design_decision_pack_v118.zip", pack_bytes)
        z.writestr("manifest.json", manifest_bytes)

    return {
        "kind":"shams_optimizer_downstream_zip_v118",
        "created_utc": created,
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
    }
