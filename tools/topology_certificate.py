from __future__ import annotations
"""Topology Certificate (v145)

Scientific authority object that certifies and summarizes the topology of the feasible set
(islands / connected components) within a declared bounded subspace and sampling protocol.

Inputs:
- baseline_run_artifact: dict (kind=shams_run_artifact) used to tie certificate to a design context
- deepdive_dataset: dict (kind=shams_deepdive_dataset, version=v142) OR None
- feasible_topology: dict (kind=shams_feasible_topology, version=v142)

Optional:
- policy: dict with publication policy meta
- method_meta: dict with k/eps and sampling params

Outputs:
- shams_topology_certificate (v145) JSON suitable for citation/audit.
"""

import time, uuid, json, hashlib
from typing import Any, Dict, Optional

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def generate_topology_certificate(
    baseline_run_artifact: Dict[str, Any],
    feasible_topology: Dict[str, Any],
    deepdive_dataset: Optional[Dict[str, Any]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(baseline_run_artifact, dict) and baseline_run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("baseline_run_artifact kind mismatch")
    if not (isinstance(feasible_topology, dict) and feasible_topology.get("kind") == "shams_feasible_topology"):
        raise ValueError("feasible_topology kind mismatch")

    policy = dict(policy or {})
    created = _utc()

    # Extract config summary from dataset if present
    ds_cfg = {}
    if isinstance(deepdive_dataset, dict):
        ds_cfg = (deepdive_dataset.get("config") or {}) if isinstance(deepdive_dataset.get("config"), dict) else {}

    islands = feasible_topology.get("islands") or []
    n_islands = len(islands)
    n_feasible = feasible_topology.get("n_feasible_points")
    if n_feasible is None:
        n_feasible = sum(int(i.get("size") or 0) for i in islands if isinstance(i, dict))

    # Compute simple topology metrics
    sizes = [int(i.get("size") or 0) for i in islands if isinstance(i, dict)]
    largest = max(sizes) if sizes else 0
    second = sorted(sizes, reverse=True)[1] if len(sizes) >= 2 else 0
    fragmentation = None
    if n_feasible and n_feasible > 0:
        fragmentation = float(1.0 - (largest / float(n_feasible)))

    cert = {
        "kind": "shams_topology_certificate",
        "version": "v145",
        "certificate_id": str(uuid.uuid4()),
        "issued_utc": created,

        "references": {
            "baseline_run_inputs_sha256": _sha(baseline_run_artifact.get("inputs", {})),
            "feasible_topology_sha256": _sha(feasible_topology),
            "deepdive_dataset_sha256": _sha(deepdive_dataset) if isinstance(deepdive_dataset, dict) else None,
        },

        "domain": {
            "vars": feasible_topology.get("vars") or ds_cfg.get("vars") or [],
            "bounds": ds_cfg.get("bounds") or {},
            "n_samples": ds_cfg.get("n_samples"),
            "seed": ds_cfg.get("seed"),
            "k": feasible_topology.get("k"),
            "eps": feasible_topology.get("eps"),
        },

        "topology_summary": {
            "n_feasible_points": n_feasible,
            "n_islands": n_islands,
            "largest_island_size": largest,
            "second_island_size": second,
            "fragmentation_index": fragmentation,  # 0 means single dominant island, ->1 means highly fragmented
        },

        "islands": islands[:50],  # cap for brevity

        "policy": policy,

        "hashes": {
            "certificate_sha256": "",  # filled below
        },
    }
    cert["hashes"]["certificate_sha256"] = _sha(cert)
    return cert
