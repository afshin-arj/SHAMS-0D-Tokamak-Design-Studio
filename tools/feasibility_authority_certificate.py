from __future__ import annotations
"""Feasibility Authority Certificate (v160)

Downstream-only certificate builder. In this upgrade, v160 certificates can be issued
from a v156 feasibility field (dense sampling basis). Future versions may incorporate
boundary extraction + interval certification to strengthen claims.

Schema:
kind: shams_feasibility_authority_certificate, version: v160
"""

from typing import Any, Dict, Optional
from pathlib import Path
import json, time, hashlib, copy, math

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def issue_certificate_from_field(
    *,
    field: Dict[str, Any],
    claim_type: str,
    statement: str,
    confidence_level: float = 0.95,
    confidence_grade: str = "B",
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(field, dict) and field.get("kind")=="shams_feasibility_field"):
        raise ValueError("field kind mismatch")
    pts = (((field.get("payload") or {}).get("field") or {}).get("points") or [])
    if not isinstance(pts, list):
        pts=[]
    n=len(pts)
    n_feas=sum(1 for p in pts if isinstance(p, dict) and p.get("status")=="feasible")
    n_infeas=sum(1 for p in pts if isinstance(p, dict) and p.get("status")=="infeasible")
    feas_frac = (n_feas/float(n)) if n else 0.0

    basis="dense_sampling"
    grade=str(confidence_grade or "B")

    # conservative claim checks
    ok_claim=False
    dominant=""
    if claim_type=="feasible_region":
        ok_claim = (n>0 and n_infeas==0 and feas_frac==1.0)
        basis = "dense_sampling_all_feasible"
    elif claim_type=="excluded_region":
        ok_claim = (n>0 and n_feas==0 and feas_frac==0.0)
        basis = "dense_sampling_all_infeasible"
        # dominant constraint consensus (best-effort)
        doms=[]
        for p in pts[:5000]:
            d=((p.get("margin") or {}).get("dominant_constraint") if isinstance(p, dict) else "")
            if d: doms.append(str(d))
        if doms:
            dominant=max(set(doms), key=lambda x: doms.count(x))
    elif claim_type=="completion_existence":
        # can't be certified from field alone; issue as informational unless policy explicitly allows
        ok_claim = False
        basis = "insufficient_evidence"
        grade = "C"
    elif claim_type=="boundary_surface":
        ok_claim = False
        basis = "requires_v157_boundary"
        grade = "C"
    else:
        raise ValueError("unknown claim_type")

    cert={
        "kind":"shams_feasibility_authority_certificate",
        "version":"v160",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(field.get("study_id") or ""),
        "provenance": {
            "generator": "ui",
            "methods": ["v156_sampling", "v160_certificate"],
        },
        "assumptions": field.get("assumptions") or {},
        "integrity": {"object_sha256": ""},
        "payload": {
            "claim": {
                "type": claim_type,
                "statement": statement,
                "confidence": {"level": float(confidence_level), "grade": grade, "basis": basis},
                "claim_ok_under_basis": bool(ok_claim),
            },
            "object": {
                "representation": {"type":"feasibility_field_ref", "data_ref": {"kind":"shams_feasibility_field","sha256": str((field.get("integrity") or {}).get("object_sha256") or "")}},
                "summary": {"n_points": n, "feasible_fraction": feas_frac, "dominant_constraint_consensus": dominant},
            },
            "policy": policy or {},
        },
    }
    tmp=copy.deepcopy(cert)
    tmp["integrity"]={"object_sha256": ""}
    cert["integrity"]["object_sha256"]=_sha_obj(tmp)
    return cert
