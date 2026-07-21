"""Firewalled external-optimization batch evaluation helpers.

Import discipline: this module must be import-safe both when SHAMS is executed
as a package (``import src``) and when invoked from repo root via scripts.
Therefore, we use relative imports within the ``src`` package.

NiceGUI callers should inject ``evaluator=ui_evaluator(origin=...)`` so batch
evaluation routes through the UI choke point. Bare ``Evaluator()`` is used only
when no injector is provided (CLI / SDK clients).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    _ = constraints  # retained for future ledger enrichment

    feasible = bool(kpis.get("feasible_hard", False))
    # Legacy cockpit tokens (PASS/FAIL) retained for older clients.
    verdict = "PASS" if feasible else "FAIL"
    # Honest L0-aligned tokens for NiceGUI / CCFS consumers.
    intent_verdict = "FEASIBLE" if feasible else "INFEASIBLE"

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
    art["intent_verdict"] = intent_verdict
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

    @property
    def artifacts(self) -> Dict[str, Dict[str, Any]]:
        """cid → artifact map (back-compat for reference_optimizer clients)."""
        return {str(r.cid): (r.artifact if isinstance(r.artifact, dict) else {}) for r in self.results}


def evaluate_concept_family(
    family: ConceptFamily,
    *,
    config: Optional[BatchEvalConfig] = None,
    repo_root: Optional[Path] = None,
    evaluator: Any = None,
    # --- back-compat kwargs used by clients / older UI helpers ---
    cfg: Optional[BatchEvalConfig] = None,
    evaluator_label: Optional[str] = None,
    cache_enabled: Optional[bool] = None,
    cache_dir: Optional[Path] = None,
    origin: Optional[str] = None,
    export_evidence_packs: bool = False,
    evidence_dir: Optional[Path] = None,
    **_ignored: Any,
) -> BatchEvalResult:
    """Evaluate a concept family deterministically.

    Returns per-candidate artifacts plus a compact summary for UI.

    Prefer injecting ``evaluator`` (e.g. NiceGUI ``ui_evaluator``) so evaluations
    share the UI choke point. When omitted, constructs a bare ``Evaluator``.
    """
    _ = (repo_root, origin, export_evidence_packs, evidence_dir, _ignored)

    base_cfg = config or cfg or BatchEvalConfig()
    if evaluator_label is not None or cache_enabled is not None or cache_dir is not None:
        base_cfg = BatchEvalConfig(
            evaluator_label=str(evaluator_label if evaluator_label is not None else base_cfg.evaluator_label),
            cache_dir=cache_dir if cache_dir is not None else base_cfg.cache_dir,
            cache_enabled=bool(cache_enabled) if cache_enabled is not None else bool(base_cfg.cache_enabled),
        )
    cfg_resolved = base_cfg

    cache: Optional[DiskCache] = None
    if cfg_resolved.cache_enabled and cfg_resolved.cache_dir is not None:
        cache = DiskCache(Path(cfg_resolved.cache_dir))

    if evaluator is not None:
        ev = evaluator
    else:
        ev = Evaluator(label=str(cfg_resolved.evaluator_label), cache_enabled=True)

    results: List[CandidateResult] = []
    n_feas = 0

    for cand in family.candidates:
        merged = _merge_inputs(family.base_inputs, cand.overrides)
        payload = {
            "schema": "extopt_cache_key.v1",
            "intent": family.intent,
            "evaluator_label": str(cfg_resolved.evaluator_label),
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
            if not getattr(evr, "ok", True):
                # Build minimal artifact with exception
                art = {
                    "schema_version": "shams_run_artifact.v1",
                    "kind": "shams_run_artifact",
                    "inputs": merged,
                    "outputs": {},
                    "constraints": [],
                    "kpis": {"feasible_hard": False, "min_hard_margin": float("nan")},
                    "error": getattr(evr, "message", "evaluate failed"),
                }
            else:
                out = getattr(evr, "out", None)
                if not isinstance(out, dict):
                    out = getattr(evr, "outputs", {}) or {}
                cons = build_constraints_from_outputs(out, design_intent=family.intent)
                art = build_run_artifact(inputs=merged, outputs=out, constraints=cons)
            art = _annotate_summary_fields(art, intent=family.intent)
            if cache is not None and isinstance(art, dict):
                cache.put_json(key, art)

        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
        feas = bool(kpis.get("feasible_hard", False))
        if feas:
            n_feas += 1

        results.append(
            CandidateResult(cid=cand.cid, inputs=merged, feasible_hard=feas, artifact=art, cache_hit=cache_hit)
        )

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
        "evaluator_label": str(cfg_resolved.evaluator_label),
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
