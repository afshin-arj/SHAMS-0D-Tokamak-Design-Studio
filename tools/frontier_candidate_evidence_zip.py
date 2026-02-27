from __future__ import annotations

"""Deterministic frontier-candidate evidence pack builder (v405.0.0).

This module builds per-candidate reviewer packs for Certified Search Orchestrator 3.0.

Design laws:
- No truth mutation.
- Deterministic contents and file ordering.
- No wall-clock timestamps embedded (audit/replay safe).

Author: © 2026 Afshin Arjhangmehr
"""

import io
import json
import zipfile
from typing import Any, Dict, Optional


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def build_frontier_candidate_evidence_zip_bytes(
    *,
    orchestrator_artifact: Dict[str, Any],
    candidate_id: str,
    basename: Optional[str] = None,
) -> bytes:
    """Build a deterministic zip for one frontier candidate.

    Expected orchestrator_artifact shape:
      - schema_version: certified_search_orchestrator_evidence.v3
      - candidates: list of dicts, each containing:
          - id
          - run_artifact (nominal)
          - lane_optimistic (optional; uncertainty_contract artifact)
          - lane_robust (optional; uncertainty_contract artifact)

    Returns bytes (zip).
    """
    if not isinstance(orchestrator_artifact, dict):
        raise TypeError("orchestrator_artifact must be a dict")

    cands = orchestrator_artifact.get("candidates") or []
    if not isinstance(cands, list):
        raise TypeError("orchestrator_artifact.candidates must be a list")

    cand = None
    for r in cands:
        if isinstance(r, dict) and str(r.get("id", "")) == str(candidate_id):
            cand = r
            break
    if cand is None:
        raise KeyError(f"candidate_id not found: {candidate_id}")

    base = basename or f"frontier_candidate_{str(candidate_id)}"

    files: Dict[str, bytes] = {}
    files["candidate_summary.json"] = _json_bytes({
        "schema_version": "frontier_candidate_summary.v1",
        "candidate_id": str(candidate_id),
        "basename": str(base),
        "orchestrator_digest": str(orchestrator_artifact.get("digest", "")),
        "candidate": {k: v for k, v in cand.items() if k not in {"run_artifact", "lane_optimistic", "lane_robust"}},
    })

    ra = cand.get("run_artifact")
    if isinstance(ra, dict):
        files["run_artifact_nominal.json"] = _json_bytes(ra)

    lo = cand.get("lane_optimistic")
    if isinstance(lo, dict):
        files["lane_optimistic_uq.json"] = _json_bytes(lo)

    lr = cand.get("lane_robust")
    if isinstance(lr, dict):
        files["lane_robust_uq.json"] = _json_bytes(lr)

    # Always include the orchestrator artifact (full context) for traceability.
    files["orchestrator_artifact.json"] = _json_bytes(orchestrator_artifact)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files.keys()):
            z.writestr(name, files[name])
    return buf.getvalue()
