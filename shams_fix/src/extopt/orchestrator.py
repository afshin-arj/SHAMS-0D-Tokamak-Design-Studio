from __future__ import annotations

"""Certified Optimization Orchestrator (v325).

This module wraps *external* optimizers and converts their output into a
certificate-carrying, reviewer-safe bundle.

Key guarantees
--------------
- Frozen truth is never modified.
- External optimizers run out-of-process.
- SHAMS re-verifies all proposed candidates deterministically.
- Outputs are stored with hash manifests for replay.

v325 upgrades
-------------
- Stronger firewall: repo mutation guard (detects any changes to frozen areas).
- Explicit objective contracts: a contract is persisted and referenced by hash.
- Evidence-integrated optimizer dossier: links kit runs, evidence packs, and verification.

The orchestrator is intentionally conservative: it verifies a small set of
candidate designs (typically the best designs reported by external runs) and
then constructs a feasible-only non-dominated set.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


FROZEN_GUARDED_PATHS = (
    "src",
    "constraints",
    "physics",
    "models",
    "profiles",
    "schemas",
)


def _repo_guard_manifest(repo_root: Path) -> Dict[str, str]:
    """Hash critical (frozen) areas of the repository.

    This is a *firewall detection* mechanism: external subprocesses are allowed
    to write only under runs/. Any mutation of frozen areas is treated as a
    certification failure.
    """
    man: Dict[str, str] = {}
    for rel_root in FROZEN_GUARDED_PATHS:
        root = (repo_root / rel_root).resolve()
        if not root.exists():
            continue
        for fp in sorted([p for p in root.rglob("*") if p.is_file()]):
            rel = fp.relative_to(repo_root).as_posix()
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            man[rel] = h.hexdigest()
    return man


def _repo_guard_check(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, Any]:
    changed = []
    removed = []
    added = []
    for k, hv in before.items():
        if k not in after:
            removed.append(k)
        elif after[k] != hv:
            changed.append(k)
    for k in after.keys():
        if k not in before:
            added.append(k)
    ok = (len(changed) == 0 and len(removed) == 0 and len(added) == 0)
    return {
        "ok": bool(ok),
        "n_changed": int(len(changed)),
        "n_removed": int(len(removed)),
        "n_added": int(len(added)),
        "changed": changed[:200],
        "removed": removed[:200],
        "added": added[:200],
    }


def _now_utc_fs() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _manifest_sha256(run_dir: Path) -> Dict[str, str]:
    """Return a sha256 manifest for files under run_dir (relative paths)."""
    man: Dict[str, str] = {}
    for fp in sorted([p for p in run_dir.rglob("*") if p.is_file()]):
        rel = fp.relative_to(run_dir).as_posix()
        h = hashlib.sha256()
        with open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        man[rel] = h.hexdigest()
    return man


def _dominates(a: Dict[str, Any], b: Dict[str, Any], objective_senses: Dict[str, str]) -> bool:
    """Return True if point a dominates b under objective senses."""
    better_or_equal_all = True
    strictly_better = False
    for k, sense in objective_senses.items():
        try:
            va = float(a.get(k))
            vb = float(b.get(k))
        except Exception:
            return False
        if sense.lower().startswith("max"):
            if va < vb:
                better_or_equal_all = False
            if va > vb:
                strictly_better = True
        else:
            if va > vb:
                better_or_equal_all = False
            if va < vb:
                strictly_better = True
    return bool(better_or_equal_all and strictly_better)


def pareto_front(points: Sequence[Dict[str, Any]], objective_senses: Dict[str, str]) -> List[Dict[str, Any]]:
    pts = list(points)
    keep: List[Dict[str, Any]] = []
    for i, p in enumerate(pts):
        dominated = False
        for j, q in enumerate(pts):
            if i == j:
                continue
            if _dominates(q, p, objective_senses):
                dominated = True
                break
        if not dominated:
            keep.append(p)
    return keep


def _validate_objective_contract(contract: Dict[str, Any]) -> Tuple[List[str], Dict[str, str]]:
    """Validate objective_contract schema and return (objectives, senses).

    Supported schemas:
      - objective_contract.v2 (legacy)
      - objective_contract.v3 (v325)

    Required semantics:
      - one or more objectives each with key and sense (min/max)
      - keys are unique
    """
    if not isinstance(contract, dict):
        raise TypeError("objective_contract must be a dict")
    schema = str(contract.get("schema", "")).strip()
    if schema not in ("objective_contract.v2", "objective_contract.v3"):
        raise ValueError(f"Unsupported objective_contract schema: {schema}")

    # v3 canonical: contract["objectives"] = [{"key":..., "sense":...}, ...]
    # v2 legacy: contract["primary"] + optional contract["secondary"]
    objs: List[Dict[str, Any]] = []
    if schema == "objective_contract.v3":
        raw = contract.get("objectives")
        if not isinstance(raw, list) or not raw:
            raise ValueError("objective_contract.v3 requires non-empty objectives list")
        for o in raw:
            if not isinstance(o, dict):
                continue
            key = str(o.get("key", "")).strip()
            sense = str(o.get("sense", "min")).strip().lower()
            if not key:
                continue
            if sense not in ("min", "max"):
                raise ValueError(f"Invalid objective sense for {key}: {sense}")
            objs.append({"key": key, "sense": sense})
    else:
        prim = contract.get("primary")
        if isinstance(prim, dict):
            key = str(prim.get("key", "")).strip()
            sense = str(prim.get("sense", "min")).strip().lower()
            if key:
                objs.append({"key": key, "sense": ("min" if sense not in ("min", "max") else sense)})
        sec = contract.get("secondary")
        if isinstance(sec, list):
            for o in sec:
                if not isinstance(o, dict):
                    continue
                key = str(o.get("key", "")).strip()
                sense = str(o.get("sense", "min")).strip().lower()
                if key:
                    objs.append({"key": key, "sense": ("min" if sense not in ("min", "max") else sense)})
    if not objs:
        raise ValueError("objective_contract has no valid objectives")
    keys = [str(o["key"]) for o in objs]
    if len(set(keys)) != len(keys):
        raise ValueError("objective_contract objective keys must be unique")
    senses = {str(o["key"]): str(o["sense"]) for o in objs}
    return keys, senses


@dataclass(frozen=True)
class OptimizerJob:
    """Hash-stable optimizer job spec."""

    schema_version: str
    kit: str
    seed: int
    n: int
    # v325: objective contract is the authoritative description.
    # Legacy fields objectives/objective_senses are kept for UI compatibility and
    # will be cross-validated.
    objective_contract: Dict[str, Any]
    objectives: List[str]
    objective_senses: Dict[str, str]
    bounds: Dict[str, List[float]]
    base_inputs: Dict[str, Any]
    verify_request: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kit": self.kit,
            "seed": int(self.seed),
            "n": int(self.n),
            "objective_contract": dict(self.objective_contract),
            "objectives": list(self.objectives),
            "objective_senses": dict(self.objective_senses),
            "bounds": dict(self.bounds),
            "base_inputs": dict(self.base_inputs),
            "verify_request": dict(self.verify_request),
        }

    def stable_id(self) -> str:
        b = json.dumps(self.to_dict(), sort_keys=True, indent=2).encode("utf-8")
        return _sha256_bytes(b)[:16]


def run_optimizer_job(
    repo_root: Path,
    job: OptimizerJob,
    *,
    orchestrator_root: Optional[Path] = None,
    keep_only_best_per_subrun: bool = True,
) -> Path:
    """Run an external optimizer kit and produce a certified bundle.

    Returns the orchestrator run directory.
    """
    repo_root = repo_root.resolve()
    orchestrator_root = (orchestrator_root or (repo_root / "runs" / "orchestrator")).resolve()
    _ensure_dir(orchestrator_root)

    ts = _now_utc_fs()
    jid = job.stable_id()
    run_id = f"{ts}_job{jid}_{str(job.kit).replace(' ', '_')}"
    run_dir = orchestrator_root / run_id
    _ensure_dir(run_dir)

    # Write immutable job spec
    job_dict = job.to_dict()
    _write_json(run_dir / "optimizer_job.json", job_dict)

    # Validate objective contract and cross-check legacy fields
    oc_keys, oc_senses = _validate_objective_contract(dict(job.objective_contract or {}))
    if list(job.objectives or []) and list(job.objectives) != list(oc_keys):
        raise ValueError("objectives list must match objective_contract keys")
    if dict(job.objective_senses or {}) and dict(job.objective_senses) != dict(oc_senses):
        raise ValueError("objective_senses must match objective_contract senses")

    # Persist the contract separately for reviewer clarity
    _write_json(run_dir / "objective_contract.json", dict(job.objective_contract or {}))

    # Run external kit
    kit_cfg = {
        "kit": job.kit,
        "seed": int(job.seed),
        "n": int(job.n),
        "objectives": list(oc_keys),
        "objective_senses": dict(oc_senses),
        "bounds": dict(job.bounds),
        "base_inputs": dict(job.base_inputs),
        "objective_contract": dict(job.objective_contract or {}),
        "orchestrator_job_id": jid,
    }
    kit_cfg_path = run_dir / "kit_config.json"
    _write_json(kit_cfg_path, kit_cfg)

    kit_runner = repo_root / "clients" / "optimizer_kits" / "run_kit.py"
    if not kit_runner.exists():
        raise FileNotFoundError(f"Missing optimizer kit runner: {kit_runner}")

    # Firewall: hash frozen areas before external run
    start_epoch = time.time()
    before_guard = _repo_guard_manifest(repo_root)
    import subprocess

    cmd = ["python", str(kit_runner), "--repo-root", str(repo_root), "--config", str(kit_cfg_path)]
    rc = subprocess.call(cmd, cwd=str(repo_root))
    _write_json(run_dir / "kit_returncode.json", {"returncode": int(rc)})

    after_guard = _repo_guard_manifest(repo_root)
    guard = _repo_guard_check(before_guard, after_guard)
    _write_json(run_dir / "repo_mutation_guard.json", guard)
    if not guard.get("ok"):
        raise RuntimeError(
            "Certification failure: repo mutation guard detected changes to frozen areas. "
            "See repo_mutation_guard.json in orchestrator run directory."
        )

    # Find kit run dirs that match this config (evidence-integrated dossier).
    kit_runs_root = repo_root / "runs" / "optimizer_kits"
    kit_run_dirs: List[str] = []
    cfg_hash = _sha256_bytes(json.dumps(kit_cfg, sort_keys=True, indent=2).encode("utf-8"))
    if kit_runs_root.exists():
        for d in sorted([p for p in kit_runs_root.iterdir() if p.is_dir()]):
            try:
                kc = d / "kit_config.json"
                if not kc.exists():
                    continue
                h = _sha256_bytes(kc.read_bytes())
                # run_kit writes the exact config; compare by hash
                if h == cfg_hash:
                    kit_run_dirs.append(d.name)
            except Exception:
                continue

    # Collect candidate best designs from feasible_opt evidence packs tagged with this orchestrator_job_id.
    opt_runs_root = repo_root / "runs" / "optimizer"
    candidates: List[Dict[str, Any]] = []
    evidence_packs: List[Dict[str, Any]] = []
    if opt_runs_root.exists():
        for d in sorted([p for p in opt_runs_root.iterdir() if p.is_dir()]):
            try:
                rcfg = d / "run_config.json"
                if not rcfg.exists():
                    continue
                cfg = _load_json(rcfg)
                if str(cfg.get("orchestrator_job_id", "")) != str(jid):
                    continue
                best_p = d / "best.json"
                if not best_p.exists():
                    continue
                best = _load_json(best_p)
                if not isinstance(best, dict):
                    continue
                inp = best.get("inputs")
                if not isinstance(inp, dict):
                    continue
                cand = {
                    "evidence_pack": d.name,
                    "objective": best.get("objective"),
                    "objective_key": best.get("objective_key") or (cfg.get("objective_contract", {}) or {}).get("primary", {}).get("key"),
                    "objective_direction": best.get("objective_direction"),
                    "inputs": inp,
                }
                candidates.append(cand)

                ep = {
                    "evidence_pack": d.name,
                    "tag": cfg.get("tag"),
                    "objective": cfg.get("objective"),
                    "objective_direction": cfg.get("objective_direction"),
                    "n": cfg.get("n"),
                    "seed": cfg.get("seed"),
                    "manifest_sha256": (d / "manifest.sha256").read_text(encoding="utf-8") if (d / "manifest.sha256").exists() else None,
                }
                evidence_packs.append(ep)
            except Exception:
                continue

    # Optional: unique by evidence_pack
    if keep_only_best_per_subrun:
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for c in candidates:
            k = str(c.get("evidence_pack"))
            if k in seen:
                continue
            seen.add(k)
            uniq.append(c)
        candidates = uniq

    _write_json(run_dir / "proposed_candidates.json", {"n": len(candidates), "candidates": candidates})

    # Verify against frozen truth using CCFS verifier.
    from .certified_solve import verify_ccfs_bundle

    ccfs_bundle = {
        "schema_version": "ccfs_bundle.v1",
        "candidates": [
            {
                "id": f"cand_{i:04d}",
                "inputs": dict(c.get("inputs") or {}),
                "claims": {
                    "objective": c.get("objective"),
                    "source": "optimizer_evidence_pack",
                    "evidence_pack": c.get("evidence_pack"),
                },
                "request": dict(job.verify_request or {}),
            }
            for i, c in enumerate(candidates)
        ],
    }
    verified = verify_ccfs_bundle(ccfs_bundle, default_request=dict(job.verify_request or {}))
    _write_json(run_dir / "ccfs_verified.json", verified)

    # Build feasible-only frontier over verified candidates.
    vlist = list(verified.get("verified") or [])
    feas: List[Dict[str, Any]] = []
    for v in vlist:
        if str(v.get("status")) != "VERIFIED":
            continue
        out = dict(v.get("outputs") or {})
        row = {
            "id": str(v.get("id")),
            "evidence_pack": (v.get("claims") or {}).get("evidence_pack"),
            "worst_hard_margin": ((v.get("constraints_summary") or {}).get("worst_hard_margin")),
        }
        # attach objective values from outputs where present
        for k in oc_keys:
            if k in out:
                row[k] = out.get(k)
        row["inputs"] = dict(v.get("inputs") or {})
        feas.append(row)

    front = pareto_front(feas, dict(oc_senses)) if feas else []
    _write_json(run_dir / "certified_feasible.json", {"feasible": feas, "pareto": front})

    # Evidence-integrated dossier
    dossier = {
        "schema_version": "optimizer_dossier.v1",
        "created_utc": ts,
        "job_id": jid,
        "kit": str(job.kit),
        "kit_returncode": int(rc),
        "objective_contract_sha256": _sha256_bytes(json.dumps(dict(job.objective_contract or {}), sort_keys=True, indent=2).encode("utf-8")),
        "kit_config_sha256": cfg_hash,
        "kit_run_dirs": kit_run_dirs,
        "evidence_packs": evidence_packs,
        "n_proposed": int(len(candidates)),
        "n_verified": int(len(list(verified.get("verified") or []))),
        "n_feasible": int(len(feas)),
        "n_pareto": int(len(front)),
        "repo_mutation_guard": guard,
    }
    _write_json(run_dir / "optimizer_dossier.json", dossier)

    # Write manifest
    man = _manifest_sha256(run_dir)
    _write_json(run_dir / "manifest.sha256.json", man)

    return run_dir
