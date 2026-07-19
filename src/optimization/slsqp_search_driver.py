"""SLSQP / SQP-style SearchDriver — Certified Optimizer Phase 2.1–2.3.

Bound-constrained continuous search **outside** L0. The driver:

* Proposes ``PointInputs`` only (never mutates ``Evaluator`` / ``hot_ion``).
* Scores FoM from a hashed ``ObjectiveContract`` (never inside physics truth).
* Treats hard constraints as SHAMS-evaluated filters / inequalities
  (governance hard-feasible). **No soft negotiation**, no VaryRun-in-L0.
* Uses SciPy ``SLSQP`` when available; otherwise a deterministic pure-Python
  coordinate-descent fallback (``slsqp_fallback``).
* Emits a stamp-ready shortlist + CCFS hooks.
* Phase 2.2: ``certify_best_and_neighborhood`` always re-certifies the
  reported best **and** a seeded local neighborhood through CCFS
  (``opt_run_stamp.v1`` attached; REJECTED rows carry ``no_solution_atlas.v1``).
* Phase 2.3 float policy: SciPy SLSQP may be platform-sensitive; publication
  locks prefer ``force_fallback=True`` + seeded neighborhood + stamp/shortlist
  identity (8 dp knobs). See ``docs/CERTIFIED_OPTIMIZER.md`` and
  ``tests/test_slsqp_determinism.py``.

Driver ids: ``slsqp`` | ``slsqp_fallback``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from src.optimization.objective_contract import (
    ObjectiveContract,
    ObjectiveContractError,
    SENSE_MAX,
    SENSE_MIN,
    parse_objective_contract,
)
from src.optimization.opt_run_stamp import (
    DRIVER_SLSQP,
    DRIVER_SLSQP_FALLBACK,
    build_opt_run_stamp,
)

SCHEMA = "slsqp_search_result.v1"
NEIGHBORHOOD_CERTIFY_SCHEMA = "neighborhood_certify.v1"

# Large finite barrier for hard-infeasible proposals (never softens limits).
_HARD_INFEASIBLE_PENALTY = 1.0e12

# Default continuous knobs (PROCESS-familiar single-obj studies).
DEFAULT_VARIABLE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "Ip_MA": (4.0, 12.0),
    "fG": (0.4, 1.1),
    "Paux_MW": (5.0, 80.0),
}

# Phase 2.2 — local neighborhood around reported best (deterministic, seeded).
DEFAULT_NEIGHBORHOOD_SIZE = 8
DEFAULT_NEIGHBORHOOD_STEP_FRAC = 0.05


class SlsqpSearchDriverError(ValueError):
    """Invalid SLSQP SearchDriver configuration or result."""


def scipy_optimize_available() -> bool:
    """True when ``scipy.optimize.minimize`` can be imported."""
    try:
        from scipy.optimize import minimize  # noqa: F401

        return True
    except Exception:
        return False


def _as_contract(
    contract: Union[ObjectiveContract, Mapping[str, Any]],
) -> ObjectiveContract:
    if isinstance(contract, ObjectiveContract):
        return contract
    if isinstance(contract, Mapping):
        return parse_objective_contract(contract)
    raise SlsqpSearchDriverError("objective_contract must be ObjectiveContract or mapping")


def _normalize_bounds(
    variables: Optional[Mapping[str, Tuple[float, float]]],
) -> Dict[str, Tuple[float, float]]:
    raw = dict(variables) if variables is not None else dict(DEFAULT_VARIABLE_BOUNDS)
    if not raw:
        raise SlsqpSearchDriverError("variables must be a non-empty bounds map")
    out: Dict[str, Tuple[float, float]] = {}
    for name, pair in raw.items():
        key = str(name).strip()
        if not key:
            raise SlsqpSearchDriverError("variable names must be non-empty")
        try:
            lo, hi = float(pair[0]), float(pair[1])
        except Exception as exc:
            raise SlsqpSearchDriverError(
                f"bounds for {key!r} must be (lo, hi) floats; got {pair!r}"
            ) from exc
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise SlsqpSearchDriverError(f"bounds for {key!r} must be finite")
        if hi < lo:
            raise SlsqpSearchDriverError(f"bounds for {key!r}: hi < lo ({hi} < {lo})")
        out[key] = (lo, hi)
    return out


def _point_to_dict(inp: Any) -> Dict[str, Any]:
    if hasattr(inp, "__dict__"):
        return dict(inp.__dict__)
    if isinstance(inp, Mapping):
        return dict(inp)
    raise SlsqpSearchDriverError("base must be PointInputs or a mapping")


def _as_point_inputs(base: Any):
    try:
        from models.inputs import PointInputs  # type: ignore
    except ImportError:
        from src.models.inputs import PointInputs  # type: ignore

    if isinstance(base, PointInputs):
        return base
    if isinstance(base, Mapping):
        return PointInputs(**dict(base))
    raise SlsqpSearchDriverError("base must be PointInputs or a mapping of fields")


def _apply_x(base: Any, names: Sequence[str], x: Sequence[float]) -> Any:
    updates = {name: float(val) for name, val in zip(names, x)}
    return replace(base, **updates)


_EVALUATOR = None


def _evaluate_outputs(inp: Any, *, origin: str) -> Dict[str, Any]:
    """Frozen choke-point eval for search guidance (propose-only; not CCFS)."""
    global _EVALUATOR
    try:
        from evaluator.core import Evaluator  # type: ignore
    except ImportError:
        from src.evaluator.core import Evaluator  # type: ignore

    if _EVALUATOR is None:
        _EVALUATOR = Evaluator(label=str(origin), cache_enabled=True)
    res = _EVALUATOR.evaluate(inp)
    out = getattr(res, "out", None)
    return dict(out) if isinstance(out, dict) else {}


def _hard_feasible(out: Mapping[str, Any]) -> bool:
    """SHAMS-evaluated hard filter — no soft negotiation."""
    try:
        from constraints.unified import build_all_constraints  # type: ignore
    except ImportError:
        from src.constraints.unified import build_all_constraints  # type: ignore

    bundle = build_all_constraints(dict(out))
    return bool(getattr(bundle, "governance_feasible", False))


def _hard_margins(out: Mapping[str, Any]) -> List[float]:
    """Inequality residuals for SciPy: margin_frac for each hard constraint (>= 0 feasible).

    Uses constraint objects when available; empty list if undecidable (caller
    falls back to binary feasible filter).
    """
    try:
        from constraints.unified import build_all_constraints  # type: ignore
        from constraints.constraints import constraint_is_hard  # type: ignore
    except ImportError:
        from src.constraints.unified import build_all_constraints  # type: ignore
        from src.constraints.constraints import constraint_is_hard  # type: ignore

    bundle = build_all_constraints(dict(out))
    margins: List[float] = []
    for c in list(getattr(bundle, "governance", []) or []):
        if not constraint_is_hard(c):
            continue
        mf = getattr(c, "margin_frac", None)
        if mf is None:
            # Binary: passed → +1, failed → -1
            margins.append(1.0 if bool(getattr(c, "passed", False)) else -1.0)
        else:
            try:
                margins.append(float(mf))
            except Exception:
                margins.append(1.0 if bool(getattr(c, "passed", False)) else -1.0)
    return margins


def _metric_value(out: Mapping[str, Any], contract: ObjectiveContract) -> float:
    key = contract.primary_metric_key()
    raw = out.get(key)
    if raw is None and len(contract.metric_keys) > 1:
        for k in contract.metric_keys[1:]:
            if out.get(k) is not None:
                raw = out.get(k)
                break
    try:
        v = float(raw)  # type: ignore[arg-type]
    except Exception:
        return float("nan")
    if not math.isfinite(v):
        return float("nan")
    return v


def _minimize_score(metric: float, sense: str) -> float:
    """Map FoM to lower-is-better score for the numerical driver."""
    if not math.isfinite(metric):
        return _HARD_INFEASIBLE_PENALTY
    if sense == SENSE_MAX:
        return -float(metric)
    if sense == SENSE_MIN:
        return float(metric)
    raise SlsqpSearchDriverError(f"unsupported sense {sense!r}")


@dataclass(frozen=True)
class ProposedCandidate:
    """One propose-only candidate (not yet CCFS-certified)."""

    id: str
    inputs: Dict[str, Any]
    proposed_metric: Optional[float]
    hard_feasible_filter: bool
    minimize_score: float
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inputs": dict(self.inputs),
            "proposed_metric": self.proposed_metric,
            "hard_feasible_filter": bool(self.hard_feasible_filter),
            "minimize_score": float(self.minimize_score),
            "rank": int(self.rank),
            "certification": "propose_only",
        }


@dataclass(frozen=True)
class SlsqpSearchResult:
    """Stamp-ready SearchDriver result (Phase 2.1)."""

    search_driver_id: str
    objective_contract: Dict[str, Any]
    objective_contract_hash: str
    seed: int
    n_evals: int
    scipy_used: bool
    variable_names: Tuple[str, ...]
    bounds: Dict[str, Tuple[float, float]]
    candidates: Tuple[ProposedCandidate, ...]
    best: Optional[ProposedCandidate]
    schema: str = SCHEMA
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "search_driver_id": self.search_driver_id,
            "objective_contract": dict(self.objective_contract),
            "objective_contract_hash": self.objective_contract_hash,
            "seed": int(self.seed),
            "n_evals": int(self.n_evals),
            "scipy_used": bool(self.scipy_used),
            "variable_names": list(self.variable_names),
            "bounds": {k: [float(lo), float(hi)] for k, (lo, hi) in self.bounds.items()},
            "candidates": [c.to_dict() for c in self.candidates],
            "best": self.best.to_dict() if self.best is not None else None,
            "notes": self.notes,
            "propose_only": True,
            "certification_required": "CCFS",
        }

    def to_ccfs_bundle(self) -> Dict[str, Any]:
        """CandidateBatch as ``ccfs_bundle.v1`` for Phase 2.2 / light certify."""
        cands = []
        for c in self.candidates:
            cands.append(
                {
                    "id": c.id,
                    "inputs": dict(c.inputs),
                    "claims": {
                        "proposed_metric": c.proposed_metric,
                        "hard_feasible_filter": c.hard_feasible_filter,
                        "search_driver_id": self.search_driver_id,
                        "status": "PROPOSED",  # must never become VERIFIED from claims
                    },
                }
            )
        if not cands and self.best is not None:
            cands.append(
                {
                    "id": self.best.id,
                    "inputs": dict(self.best.inputs),
                    "claims": {
                        "proposed_metric": self.best.proposed_metric,
                        "status": "PROPOSED",
                    },
                }
            )
        return {
            "schema_version": "ccfs_bundle.v1",
            "candidates": cands,
            "opt_run": {
                "objective_contract": dict(self.objective_contract),
                "objective_contract_hash": self.objective_contract_hash,
                "seed": int(self.seed),
                "search_driver_id": self.search_driver_id,
            },
        }

    def stamp_ready(
        self,
        *,
        n_verified: int = 0,
        n_rejected: int = 0,
        shams_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build ``opt_run_stamp.v1`` for the proposal shortlist (pre-CCFS counts)."""
        n_cand = len(self.candidates) if self.candidates else (1 if self.best else 0)
        stamp = build_opt_run_stamp(
            search_driver_id=self.search_driver_id,
            n_candidates=n_cand,
            n_verified=n_verified,
            n_rejected=n_rejected,
            objective_contract=self.objective_contract,
            seed=self.seed,
            shams_version=shams_version,
        )
        return stamp.to_dict()


def _clip(x: Sequence[float], bounds: Sequence[Tuple[float, float]]) -> List[float]:
    return [min(hi, max(lo, float(xi))) for xi, (lo, hi) in zip(x, bounds)]


def _run_scipy_slsqp(
    *,
    x0: List[float],
    bound_pairs: List[Tuple[float, float]],
    names: Sequence[str],
    base: Any,
    contract: ObjectiveContract,
    maxiter: int,
    origin: str,
    eval_counter: List[int],
    archive: List[Dict[str, Any]],
) -> Tuple[List[float], bool]:
    from scipy.optimize import minimize

    def _obj(x):
        xc = _clip(x, bound_pairs)
        inp = _apply_x(base, names, xc)
        out = _evaluate_outputs(inp, origin=origin)
        eval_counter[0] += 1
        feas = _hard_feasible(out)
        metric = _metric_value(out, contract)
        score = _minimize_score(metric, contract.sense)
        if not feas:
            score = _HARD_INFEASIBLE_PENALTY + abs(score)
        archive.append(
            {
                "x": list(xc),
                "inputs": _point_to_dict(inp),
                "metric": metric if math.isfinite(metric) else None,
                "feasible": feas,
                "score": float(score),
            }
        )
        return float(score)

    def _cons_factory(idx: int):
        def _c(x):
            xc = _clip(x, bound_pairs)
            inp = _apply_x(base, names, xc)
            out = _evaluate_outputs(inp, origin=origin + "_cons")
            eval_counter[0] += 1
            margins = _hard_margins(out)
            if not margins:
                return 1.0 if _hard_feasible(out) else -1.0
            if idx >= len(margins):
                return float(min(margins))
            return float(margins[idx])

        return _c

    # Probe one eval for constraint count.
    probe_out = _evaluate_outputs(_apply_x(base, names, x0), origin=origin + "_probe")
    eval_counter[0] += 1
    n_hard = max(1, len(_hard_margins(probe_out)) or 1)
    constraints = [{"type": "ineq", "fun": _cons_factory(i)} for i in range(min(n_hard, 8))]

    res = minimize(
        _obj,
        x0=list(x0),
        method="SLSQP",
        bounds=list(bound_pairs),
        constraints=constraints,
        options={"maxiter": int(max(1, maxiter)), "ftol": 1e-9, "disp": False},
    )
    x_best = _clip(list(res.x) if res is not None and hasattr(res, "x") else x0, bound_pairs)
    return x_best, True


def _run_fallback_coordinate(
    *,
    x0: List[float],
    bound_pairs: List[Tuple[float, float]],
    names: Sequence[str],
    base: Any,
    contract: ObjectiveContract,
    maxiter: int,
    seed: int,
    origin: str,
    eval_counter: List[int],
    archive: List[Dict[str, Any]],
) -> Tuple[List[float], bool]:
    """Deterministic pure-Python local search (no SciPy).

    Multi-start + coordinate descent. Same seed → same proposal trajectory
    (within float eval noise of the frozen evaluator).
    """
    rng = random.Random(int(seed))
    dim = len(x0)

    def _eval_x(x: Sequence[float]) -> Dict[str, Any]:
        xc = _clip(x, bound_pairs)
        inp = _apply_x(base, names, xc)
        out = _evaluate_outputs(inp, origin=origin)
        eval_counter[0] += 1
        feas = _hard_feasible(out)
        metric = _metric_value(out, contract)
        score = _minimize_score(metric, contract.sense)
        if not feas:
            score = _HARD_INFEASIBLE_PENALTY + abs(score)
        row = {
            "x": list(xc),
            "inputs": _point_to_dict(inp),
            "metric": metric if math.isfinite(metric) else None,
            "feasible": feas,
            "score": float(score),
        }
        archive.append(row)
        return row

    best = _eval_x(x0)
    best_x = list(best["x"])

    # Seeded restarts inside bounds.
    n_restarts = max(1, min(5, int(maxiter) // 3 + 1))
    starts = [list(x0)]
    for _ in range(n_restarts - 1):
        starts.append(
            [
                lo + (hi - lo) * rng.random()
                for (lo, hi) in bound_pairs
            ]
        )

    steps_budget = max(1, int(maxiter))
    steps_done = 0
    for start in starts:
        x = _clip(start, bound_pairs)
        cur = _eval_x(x)
        if cur["score"] < best["score"]:
            best, best_x = cur, list(cur["x"])
        # Coordinate descent with shrinking step.
        span = [hi - lo for (lo, hi) in bound_pairs]
        step_frac = 0.2
        while steps_done < steps_budget:
            improved = False
            for j in range(dim):
                if steps_done >= steps_budget:
                    break
                delta = span[j] * step_frac
                if delta <= 0.0:
                    continue
                for sign in (+1.0, -1.0):
                    trial = list(x)
                    trial[j] = trial[j] + sign * delta
                    row = _eval_x(trial)
                    steps_done += 1
                    if row["score"] < cur["score"]:
                        cur, x = row, list(row["x"])
                        improved = True
                        if row["score"] < best["score"]:
                            best, best_x = row, list(row["x"])
                        break
                if steps_done >= steps_budget:
                    break
            if not improved:
                step_frac *= 0.5
                if step_frac < 1e-4:
                    break
            else:
                # Count one outer cycle toward budget even if inner already counted.
                pass

    return best_x, False


def run_slsqp_search(
    base: Any,
    objective_contract: Union[ObjectiveContract, Mapping[str, Any]],
    *,
    variables: Optional[Mapping[str, Tuple[float, float]]] = None,
    seed: Optional[int] = None,
    maxiter: int = 25,
    shortlist_k: int = 5,
    force_fallback: bool = False,
    prefer_feasible: bool = True,
    origin: str = "slsqp_search_driver",
) -> SlsqpSearchResult:
    """Run bound-constrained SLSQP-style search; return propose-only shortlist.

    Parameters
    ----------
    base:
        Baseline ``PointInputs`` (or field mapping). Search variables are
        overlaid via ``dataclasses.replace``.
    objective_contract:
        Hashed FoM contract (``objective_contract.v1``).
    variables:
        ``{name: (lo, hi)}`` continuous bounds. Defaults to Ip/fG/Paux band.
    seed:
        Reproducibility seed (required when contract ``seed_policy`` is
        ``required`` / ``fixed``).
    maxiter:
        SciPy ``maxiter`` or fallback local-search budget (evals ~ O(maxiter)).
    shortlist_k:
        Number of distinct proposals retained for CCFS.
    force_fallback:
        If True, skip SciPy even when installed (lock-tests the fallback path).
    prefer_feasible:
        Prefer hard-feasible archive rows when building the shortlist.
    """
    contract = _as_contract(objective_contract)
    bounds = _normalize_bounds(variables)
    names = tuple(sorted(bounds.keys()))
    bound_pairs = [bounds[n] for n in names]
    base_inp = _as_point_inputs(base)

    # Resolve seed from arg or contract.
    if seed is None:
        seed = contract.seed
    if seed is None:
        if contract.seed_policy in ("required", "fixed"):
            raise SlsqpSearchDriverError(
                f"seed required by objective_contract seed_policy={contract.seed_policy!r}"
            )
        seed = 0
    seed = int(seed)

    # Initial point: clip baseline into bounds (deterministic).
    x0: List[float] = []
    for n, (lo, hi) in zip(names, bound_pairs):
        try:
            v = float(getattr(base_inp, n))
        except Exception:
            v = 0.5 * (lo + hi)
        x0.append(min(hi, max(lo, v)))

    eval_counter = [0]
    archive: List[Dict[str, Any]] = []
    use_scipy = (not force_fallback) and scipy_optimize_available()

    if use_scipy:
        try:
            x_best, scipy_used = _run_scipy_slsqp(
                x0=x0,
                bound_pairs=bound_pairs,
                names=names,
                base=base_inp,
                contract=contract,
                maxiter=maxiter,
                origin=origin,
                eval_counter=eval_counter,
                archive=archive,
            )
        except Exception:
            # Robustness: any SciPy failure → deterministic fallback.
            x_best, scipy_used = _run_fallback_coordinate(
                x0=x0,
                bound_pairs=bound_pairs,
                names=names,
                base=base_inp,
                contract=contract,
                maxiter=maxiter,
                seed=seed,
                origin=origin + "_fallback",
                eval_counter=eval_counter,
                archive=archive,
            )
            scipy_used = False
    else:
        x_best, scipy_used = _run_fallback_coordinate(
            x0=x0,
            bound_pairs=bound_pairs,
            names=names,
            base=base_inp,
            contract=contract,
            maxiter=maxiter,
            seed=seed,
            origin=origin,
            eval_counter=eval_counter,
            archive=archive,
        )

    # Ensure final best is archived.
    final_inp = _apply_x(base_inp, names, x_best)
    final_out = _evaluate_outputs(final_inp, origin=origin + "_final")
    eval_counter[0] += 1
    final_feas = _hard_feasible(final_out)
    final_metric = _metric_value(final_out, contract)
    final_score = _minimize_score(final_metric, contract.sense)
    if not final_feas:
        final_score = _HARD_INFEASIBLE_PENALTY + abs(final_score)
    archive.append(
        {
            "x": list(x_best),
            "inputs": _point_to_dict(final_inp),
            "metric": final_metric if math.isfinite(final_metric) else None,
            "feasible": final_feas,
            "score": float(final_score),
        }
    )

    # Deduplicate shortlist by rounded x-vector.
    def _key(row: Mapping[str, Any]) -> Tuple[float, ...]:
        return tuple(round(float(v), 8) for v in row.get("x", []))

    ranked = sorted(archive, key=lambda r: (not bool(r.get("feasible")) if prefer_feasible else False, float(r["score"])))
    seen = set()
    picked: List[Dict[str, Any]] = []
    for row in ranked:
        k = _key(row)
        if k in seen:
            continue
        seen.add(k)
        picked.append(row)
        if len(picked) >= max(1, int(shortlist_k)):
            break

    candidates: List[ProposedCandidate] = []
    for i, row in enumerate(picked):
        candidates.append(
            ProposedCandidate(
                id=f"slsqp_{i:04d}",
                inputs=dict(row["inputs"]),
                proposed_metric=row.get("metric"),
                hard_feasible_filter=bool(row.get("feasible")),
                minimize_score=float(row["score"]),
                rank=i,
            )
        )

    best = candidates[0] if candidates else None
    driver_id = DRIVER_SLSQP if scipy_used else DRIVER_SLSQP_FALLBACK
    notes = (
        "Propose-only SLSQP/SQP-style SearchDriver. Scores are uncertified; "
        "run CCFS / frozen Evaluator for VERIFIED vs REJECTED. "
        "Hard constraints used as SHAMS-evaluated filters/inequalities only."
    )
    return SlsqpSearchResult(
        search_driver_id=driver_id,
        objective_contract=contract.to_dict(),
        objective_contract_hash=contract.hash_sha256(),
        seed=seed,
        n_evals=int(eval_counter[0]),
        scipy_used=bool(scipy_used),
        variable_names=names,
        bounds=bounds,
        candidates=tuple(candidates),
        best=best,
        notes=notes,
    )


def lightly_certify_shortlist(
    result: SlsqpSearchResult,
    *,
    attach_opt_run_stamp: bool = True,
) -> Dict[str, Any]:
    """Light CCFS pass on the proposal shortlist (no neighborhood expansion).

    Prefer ``certify_best_and_neighborhood`` for Phase 2.2 publication paths.
    Returns the ``ccfs_verified.v1`` dict from ``verify_ccfs_bundle``.
    """
    bundle = result.to_ccfs_bundle()
    if not bundle.get("candidates"):
        raise SlsqpSearchDriverError("no candidates to certify")
    try:
        from extopt.certified_solve import verify_ccfs_bundle  # type: ignore
    except ImportError:
        from src.extopt.certified_solve import verify_ccfs_bundle  # type: ignore

    return verify_ccfs_bundle(
        bundle,
        opt_run=bundle.get("opt_run"),
        attach_opt_run_stamp=attach_opt_run_stamp,
    )


def _x_from_inputs(
    inputs: Mapping[str, Any],
    names: Sequence[str],
    bounds: Mapping[str, Tuple[float, float]],
) -> List[float]:
    x: List[float] = []
    for n in names:
        lo, hi = bounds[n]
        try:
            v = float(inputs[n])  # type: ignore[index]
        except Exception:
            v = 0.5 * (lo + hi)
        x.append(min(hi, max(lo, v)))
    return x


def _inputs_key(inputs: Mapping[str, Any], names: Sequence[str]) -> Tuple[float, ...]:
    vals: List[float] = []
    for n in names:
        try:
            vals.append(round(float(inputs[n]), 8))  # type: ignore[index]
        except Exception:
            vals.append(float("nan"))
    return tuple(vals)


def build_neighborhood_proposals(
    result: SlsqpSearchResult,
    *,
    neighborhood_size: int = DEFAULT_NEIGHBORHOOD_SIZE,
    step_frac: float = DEFAULT_NEIGHBORHOOD_STEP_FRAC,
    seed: Optional[int] = None,
) -> Tuple[ProposedCandidate, ...]:
    """Deterministic local perturbations of the reported best (propose-only).

    Policy
    ------
    * Center = ``result.best`` (required).
    * Continuous vars = ``result.variable_names`` clipped to ``result.bounds``.
    * Always include axis-aligned ± ``step_frac * span`` steps (when span > 0).
    * Fill remaining slots with seeded random offsets in ``[-step_frac, +step_frac]``
      of each span (``random.Random(seed)`` — same seed → same neighbors).
    * Deduplicate by rounded x-vector; never softens bounds.

    Returns neighbors **excluding** the center (caller adds best separately).
    """
    if result.best is None:
        raise SlsqpSearchDriverError("result.best is required for neighborhood proposals")
    names = tuple(result.variable_names)
    if not names:
        raise SlsqpSearchDriverError("result.variable_names must be non-empty")
    bounds = dict(result.bounds)
    for n in names:
        if n not in bounds:
            raise SlsqpSearchDriverError(f"missing bounds for variable {n!r}")

    n_want = max(0, int(neighborhood_size))
    if n_want == 0:
        return tuple()

    frac = float(step_frac)
    if not math.isfinite(frac) or frac <= 0.0:
        raise SlsqpSearchDriverError("step_frac must be a positive finite float")

    seed_i = int(result.seed if seed is None else seed)
    rng = random.Random(seed_i)

    center_inputs = dict(result.best.inputs)
    x0 = _x_from_inputs(center_inputs, names, bounds)
    bound_pairs = [bounds[n] for n in names]
    spans = [hi - lo for (lo, hi) in bound_pairs]

    # Template base: best inputs, then overlay continuous knobs.
    try:
        base_pt = _as_point_inputs(center_inputs)
    except Exception as exc:
        raise SlsqpSearchDriverError(
            f"best.inputs must map to PointInputs: {exc}"
        ) from exc

    seen = {_inputs_key(center_inputs, names)}
    neighbors: List[ProposedCandidate] = []

    def _try_add(x_trial: Sequence[float], tag: str) -> None:
        if len(neighbors) >= n_want:
            return
        xc = _clip(x_trial, bound_pairs)
        inp = _apply_x(base_pt, names, xc)
        d = _point_to_dict(inp)
        key = _inputs_key(d, names)
        if key in seen:
            return
        seen.add(key)
        neighbors.append(
            ProposedCandidate(
                id=f"nbr_{len(neighbors):04d}_{tag}",
                inputs=d,
                proposed_metric=None,
                hard_feasible_filter=False,
                minimize_score=_HARD_INFEASIBLE_PENALTY,
                rank=len(neighbors),
            )
        )

    # Axis-aligned ± steps first (deterministic, seed-independent order).
    for j, span in enumerate(spans):
        if len(neighbors) >= n_want:
            break
        delta = span * frac
        if delta <= 0.0:
            continue
        for sign, tag in ((+1.0, f"p{j}"), (-1.0, f"m{j}")):
            trial = list(x0)
            trial[j] = trial[j] + sign * delta
            _try_add(trial, tag)
            if len(neighbors) >= n_want:
                break

    # Seeded random fill for remaining slots.
    guard = 0
    while len(neighbors) < n_want and guard < n_want * 40:
        guard += 1
        trial = list(x0)
        for j, span in enumerate(spans):
            if span <= 0.0:
                continue
            trial[j] = trial[j] + (2.0 * rng.random() - 1.0) * span * frac
        _try_add(trial, f"r{guard}")

    return tuple(neighbors)


def best_and_neighborhood_bundle(
    result: SlsqpSearchResult,
    *,
    neighborhood_size: int = DEFAULT_NEIGHBORHOOD_SIZE,
    step_frac: float = DEFAULT_NEIGHBORHOOD_STEP_FRAC,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Build ``ccfs_bundle.v1`` with reported best + local neighborhood proposals."""
    if result.best is None:
        raise SlsqpSearchDriverError("result.best is required for neighborhood certify")

    neighbors = build_neighborhood_proposals(
        result,
        neighborhood_size=neighborhood_size,
        step_frac=step_frac,
        seed=seed,
    )
    cands: List[Dict[str, Any]] = [
        {
            "id": result.best.id,
            "inputs": dict(result.best.inputs),
            "claims": {
                "role": "best",
                "proposed_metric": result.best.proposed_metric,
                "hard_feasible_filter": result.best.hard_feasible_filter,
                "search_driver_id": result.search_driver_id,
                "status": "PROPOSED",
            },
        }
    ]
    for nbr in neighbors:
        cands.append(
            {
                "id": nbr.id,
                "inputs": dict(nbr.inputs),
                "claims": {
                    "role": "neighborhood",
                    "proposed_metric": nbr.proposed_metric,
                    "search_driver_id": result.search_driver_id,
                    "status": "PROPOSED",
                },
            }
        )
    return {
        "schema_version": "ccfs_bundle.v1",
        "candidates": cands,
        "opt_run": {
            "objective_contract": dict(result.objective_contract),
            "objective_contract_hash": result.objective_contract_hash,
            "seed": int(result.seed if seed is None else seed),
            "search_driver_id": result.search_driver_id,
        },
        "neighborhood_policy": {
            "schema": NEIGHBORHOOD_CERTIFY_SCHEMA,
            "neighborhood_size": int(neighborhood_size),
            "step_frac": float(step_frac),
            "n_neighbors_emitted": len(neighbors),
            "variable_names": list(result.variable_names),
            "deterministic": True,
        },
    }


def certify_best_and_neighborhood(
    result: SlsqpSearchResult,
    *,
    neighborhood_size: int = DEFAULT_NEIGHBORHOOD_SIZE,
    step_frac: float = DEFAULT_NEIGHBORHOOD_STEP_FRAC,
    seed: Optional[int] = None,
    attach_opt_run_stamp: bool = True,
) -> Dict[str, Any]:
    """CCFS-certify reported best **and** a local neighborhood (Phase 2.2).

    Every proposal goes through ``verify_ccfs_bundle`` (frozen ``Evaluator``).
    REJECTED rows carry ``no_solution_atlas.v1`` via existing CCFS paths.
    ``opt_run_stamp.v1`` is attached by default.

    Returns ``ccfs_verified.v1`` plus ``neighborhood_certify`` summary meta
    (not a parallel firewall — CCFS remains the sole certifier).
    """
    bundle = best_and_neighborhood_bundle(
        result,
        neighborhood_size=neighborhood_size,
        step_frac=step_frac,
        seed=seed,
    )
    policy = dict(bundle.get("neighborhood_policy") or {})
    try:
        from extopt.certified_solve import verify_ccfs_bundle  # type: ignore
    except ImportError:
        from src.extopt.certified_solve import verify_ccfs_bundle  # type: ignore

    verified = verify_ccfs_bundle(
        bundle,
        opt_run=bundle.get("opt_run"),
        attach_opt_run_stamp=attach_opt_run_stamp,
    )
    rows = list(verified.get("verified") or [])
    best_id = result.best.id if result.best is not None else None
    best_row = next((r for r in rows if r.get("id") == best_id), None)
    n_rej = int(verified.get("n_status_rejected") or 0)
    atlas_on_rejects = all(
        isinstance(r.get("no_solution_atlas"), Mapping)
        and str((r.get("no_solution_atlas") or {}).get("schema", "")).startswith(
            "no_solution_atlas"
        )
        for r in rows
        if r.get("status") == "REJECTED"
    )
    verified["neighborhood_certify"] = {
        "schema": NEIGHBORHOOD_CERTIFY_SCHEMA,
        "best_id": best_id,
        "best_status": None if best_row is None else best_row.get("status"),
        "n_certified": len(rows),
        "n_neighbors": int(policy.get("n_neighbors_emitted") or 0),
        "neighborhood_size_requested": int(neighborhood_size),
        "step_frac": float(step_frac),
        "atlas_on_all_rejects": bool(atlas_on_rejects) if n_rej > 0 else True,
        "opt_run_stamp_attached": "opt_run_stamp" in verified,
        "propose_only_search": True,
        "certifier": "CCFS",
        "policy": policy,
    }
    return verified


# Re-export contract builder for callers that want a one-liner FoM setup.
def contract_from_registry(
    name: str,
    *,
    seed: int,
    notes: str = "",
) -> ObjectiveContract:
    """Bridge registry FoM → ``objective_contract.v1`` with fixed seed."""
    from src.optimization.objective_contract import from_registry_name

    try:
        return from_registry_name(
            name,
            seed_policy="fixed",
            seed=int(seed),
            notes=notes or f"SLSQP SearchDriver FoM={name}",
            provenance={"source": "slsqp_search_driver", "role": "propose_only"},
        )
    except ObjectiveContractError as exc:
        raise SlsqpSearchDriverError(str(exc)) from exc
