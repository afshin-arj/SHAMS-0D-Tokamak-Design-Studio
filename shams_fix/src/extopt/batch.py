"""Firewalled external-optimization batch evaluation helpers.

Import discipline: this module must be import-safe both when SHAMS is executed
as a package (``import src``) and when invoked from repo root via scripts.
Therefore, we use relative imports within the ``src`` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    # Preferred when SHAMS is imported as a package (`import src.*`)
    from ..evaluator.core import Evaluator  # type: ignore
    from ..models.inputs import PointInputs  # type: ignore
    from ..constraints.system import build_constraints_from_outputs  # type: ignore
    from ..shams_io.run_artifact import build_run_artifact  # type: ignore
except Exception:
    # Back-compat when `<repo>/src` is on sys.path (so `evaluator`, `models`, ... are top-level)
    from evaluator.core import Evaluator  # type: ignore
    from models.inputs import PointInputs  # type: ignore
    from constraints.system import build_constraints_from_outputs  # type: ignore
    from shams_io.run_artifact import build_run_artifact  # type: ignore

from .cache import DiskCache
from .family import ConceptFamily
from .utils import stable_sha256


def _merge_inputs(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for k, v in (overrides or {}).items():
        merged[k] = v
    return merged


def _annotate_summary_fields(art: Dict[str, Any], *, intent: str) -> Dict[str, Any]:
    """Add lightweight top-level fields used by evidence packs and the cockpit."""
    kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
    constraints = art.get("constraints", []) if isinstance(art.get("constraints"), list) else []

    feasible = bool(kpis.get("feasible_hard", False))
    verdict = "PASS" if feasible else "FAIL"

    # worst hard margin
    worst = None
    try:
        worst = float(kpis.get("min_hard_margin"))
    except Exception:
        worst = None

    dom_constraint = ""
    dom_mech = ""
    try:
        ledger = art.get("constraint_ledger", {}) if isinstance(art.get("constraint_ledger"), dict) else {}
        top = ledger.get("top_blockers", []) if isinstance(ledger.get("top_blockers"), list) else []
        if top:
            t0 = top[0] if isinstance(top[0], dict) else {}
            dom_constraint = str(t0.get("name", ""))
            dom_mech = str(t0.get("mechanism_group", t0.get("mechanism", "")) or "")
    except Exception:
        pass

    art["intent"] = str(intent)
    art["verdict"] = verdict
    art["dominant_constraint"] = dom_constraint
    art["dominant_mechanism"] = dom_mech
    art["worst_hard_margin"] = worst
    return art


@dataclass(frozen=True)
class BatchEvalConfig:
    """Configuration for batch evaluation."""

    evaluator_label: str = "hot_ion_point"
    cache_dir: Optional[Path] = None
    cache_enabled: bool = True


@dataclass(frozen=True)
class CandidateResult:
    cid: str
    inputs: Dict[str, Any]
    feasible_hard: bool
    artifact: Dict[str, Any]
    cache_hit: bool


@dataclass(frozen=True)
class BatchEvalResult:
    family_name: str
    intent: str
    n_total: int
    n_feasible: int
    pass_rate: float
    results: List[CandidateResult]
    summary: Dict[str, Any]


def evaluate_concept_family(
    family: ConceptFamily,
    *,
    config: Optional[BatchEvalConfig] = None,
    repo_root: Optional[Path] = None,
) -> BatchEvalResult:
    """Evaluate a concept family deterministically.

    Returns per-candidate artifacts plus a compact summary for UI.
    """
    cfg = config or BatchEvalConfig()

    cache: Optional[DiskCache] = None
    if cfg.cache_enabled and cfg.cache_dir is not None:
        cache = DiskCache(Path(cfg.cache_dir))

    ev = Evaluator(label=str(cfg.evaluator_label), cache_enabled=True)

    results: List[CandidateResult] = []
    n_feas = 0

    for cand in family.candidates:
        merged = _merge_inputs(family.base_inputs, cand.overrides)
        payload = {
            "schema": "extopt_cache_key.v1",
            "intent": family.intent,
        "evaluator_label": str(cfg.evaluator_label),
            "evaluator_label": cfg.evaluator_label,
            "inputs": merged,
        }
        key = stable_sha256(payload)

        art: Optional[Dict[str, Any]] = None
        cache_hit = False
        if cache is not None:
            art = cache.get_json(key)
            if isinstance(art, dict):
                cache_hit = True

        if art is None:
            # Build PointInputs (strict)
            pi = PointInputs(**merged)
            evr = ev.evaluate(pi)
            if not evr.ok:
                # Build minimal artifact with exception
                art = {
                    "schema_version": "shams_run_artifact.v1",
                    "kind": "shams_run_artifact",
                    "inputs": merged,
                    "outputs": {},
                    "constraints": [],
                    "kpis": {"feasible_hard": False, "min_hard_margin": float("nan")},
                    "error": evr.message,
                }
            else:
                out = evr.out
                cons = build_constraints_from_outputs(out, design_intent=family.intent)
                art = build_run_artifact(inputs=merged, outputs=out, constraints=cons)
            art = _annotate_summary_fields(art, intent=family.intent)
            if cache is not None and isinstance(art, dict):
                cache.put_json(key, art)

        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
        feas = bool(kpis.get("feasible_hard", False))
        if feas:
            n_feas += 1

        results.append(CandidateResult(cid=cand.cid, inputs=merged, feasible_hard=feas, artifact=art, cache_hit=cache_hit))

    n_total = len(results)
    pass_rate = float(n_feas) / float(n_total) if n_total > 0 else 0.0

    # Aggregate mechanism histogram (for cockpit)
    mech_hist: Dict[str, int] = {}
    for r in results:
        mech = str(r.artifact.get("dominant_mechanism", ""))
        if not mech:
            mech = "(none)"
        mech_hist[mech] = int(mech_hist.get(mech, 0)) + 1

    summary = {
        "schema": "extopt_batch_summary.v1",
        "family": family.name,
        "intent": family.intent,
        "evaluator_label": str(cfg.evaluator_label),
        "n_total": n_total,
        "n_feasible": n_feas,
        "pass_rate": pass_rate,
        "dominant_mechanism_hist": mech_hist,
    }

    return BatchEvalResult(
        family_name=family.name,
        intent=family.intent,
        n_total=n_total,
        n_feasible=n_feas,
        pass_rate=pass_rate,
        results=results,
        summary=summary,
    )
