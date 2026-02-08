from __future__ import annotations

"""Firewalled Optimizer Kits runner (v303.0).

This is an external proposal generator invoked by the UI. It lives outside the
frozen evaluator. It produces evidence packs under:
  <repo_root>/runs/optimizer_kits/<run_id>/

Kits provided (lite implementations, deterministic):
  - NSGA-II-lite: multi-objective batch using feasible_opt as inner worker
  - CMA-ES-lite: continuous feasible-only (feasible_opt with ...

The intent is to be an ergonomic replacement for PROCESS optimization workflows
while keeping SHAMS truth frozen.

Author: © 2026 Afshin Arjhangmehr
"""

import argparse
import json
import os
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List

import subprocess


def _now_utc_fs() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _feasible_opt_script(repo_root: Path) -> Path:
    return repo_root / "clients" / "feasible_optimizer_client" / "feasible_opt.py"


def _run_feasible_opt(repo_root: Path, cfg_path: Path) -> int:
    cmd = ["python", str(_feasible_opt_script(repo_root)), "--repo-root", str(repo_root), "--config", str(cfg_path)]
    return subprocess.call(cmd, cwd=str(repo_root))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    cfg = _load_json(Path(args.config).resolve())

    kit = str(cfg.get("kit", "")).strip()
    seed = int(cfg.get("seed", 0))
    n = int(cfg.get("n", 800))
    objectives = list(cfg.get("objectives", []) or [])
    objective_senses = dict(cfg.get("objective_senses", {}) or {})
    objective_contract = cfg.get("objective_contract", None)
    bounds = dict(cfg.get("bounds", {}) or {})
    base_inputs = dict(cfg.get("base_inputs", {}) or {})
    orchestrator_job_id = str(cfg.get("orchestrator_job_id", "")).strip()

    runs_root = repo_root / "runs" / "optimizer_kits"
    _ensure(runs_root)
    cfg_bytes = json.dumps(cfg, indent=2, sort_keys=True).encode("utf-8")
    run_id = f"{_now_utc_fs()}_seed{seed:04d}_N{n:04d}_{kit.replace(' ','_').replace('/','-')}_{_sha256_bytes(cfg_bytes)[:12]}"
    run_dir = runs_root / run_id
    _ensure(run_dir)

    _write_json(run_dir / "kit_config.json", cfg)

    print(f"[kit] {kit}")
    print(f"[run_dir] {run_dir}")

    # Strategy mapping to feasible_opt flags.
    # NOTE: still a single-objective inner worker; NSGA-lite runs multiple objectives and merges.
    base_extopt = {
        "schema": "feasible_opt.v1",
        "created_utc": _now_utc_fs(),
        "seed": seed,
        "n": n,
        "policy": "pass_plus_diag",
        "bounds": bounds,
        "fixed": {},
        "caps": {},
        "seed_inputs": base_inputs,
        "objective_contract": objective_contract,
        "orchestrator_job_id": orchestrator_job_id,
    }

    if kit.startswith("NSGA"):
        # Split budget across objectives (deterministic floor, remainder to first objective)
        m = max(1, len(objectives))
        n_each = max(50, int(n // m))
        extra = int(n - n_each * m)
        subruns: List[Dict[str, Any]] = []
        for i, obj in enumerate(objectives):
            nn = int(n_each + (extra if i == 0 else 0))
            sub = dict(base_extopt)
            sub["seed"] = int(seed + 31 * i)
            sub["n"] = int(nn)
            sub["objective"] = str(obj)
            sub["objective_dir"] = str(objective_senses.get(obj, "min"))
            sub["tag"] = f"nsga_lite_{i:02d}_{obj}"
            sub["robustness_first"] = True
            sub["multi_island"] = True
            sub["surrogate_guidance"] = True
            sub["hybrid_guidance"] = True
            cfg_p = run_dir / f"sub_{i:02d}_{obj}.json"
            _write_json(cfg_p, sub)
            print(f"[subrun] objective={obj}  n={nn}  cfg={cfg_p.name}")
            rc = _run_feasible_opt(repo_root, cfg_p)
            subruns.append({"objective": obj, "n": nn, "returncode": rc, "cfg": cfg_p.name})
            if rc != 0:
                print(f"[subrun] failed: {obj} rc={rc}")
        _write_json(run_dir / "summary.json", {"kit": kit, "subruns": subruns})
        print("[done] nsga-lite")
        return 0

    if kit.startswith("CMA"):
        sub = dict(base_extopt)
        sub["objective"] = str(objectives[0])
        sub["objective_dir"] = str(objective_senses.get(objectives[0], "min"))
        sub["tag"] = "cmaes_lite"
        sub["multi_island"] = True
        sub["constraint_aware"] = True
        sub["surrogate_guidance"] = False
        sub["hybrid_guidance"] = False
        cfg_p = run_dir / "run.json"
        _write_json(cfg_p, sub)
        print(f"[run] cmaes-lite objective={objectives[0]}")
        rc = _run_feasible_opt(repo_root, cfg_p)
        _write_json(run_dir / "summary.json", {"kit": kit, "returncode": rc, "cfg": cfg_p.name})
        return int(rc)

    # BO-lite (surrogate guided)
    sub = dict(base_extopt)
    sub["objective"] = str(objectives[0])
    sub["objective_dir"] = str(objective_senses.get(objectives[0], "min"))
    sub["tag"] = "bo_lite"
    sub["surrogate_guidance"] = True
    sub["hybrid_guidance"] = True
    sub["multi_island"] = True
    cfg_p = run_dir / "run.json"
    _write_json(cfg_p, sub)
    print(f"[run] bo-lite objective={objectives[0]}")
    rc = _run_feasible_opt(repo_root, cfg_p)
    _write_json(run_dir / "summary.json", {"kit": kit, "returncode": rc, "cfg": cfg_p.name})
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())
