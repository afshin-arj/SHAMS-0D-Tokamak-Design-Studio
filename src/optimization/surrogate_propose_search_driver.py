"""Surrogate propose-only SearchDriver — Certified Optimizer Phase 4.1.

Surrogate ranking lives **outside** L0. The driver:

* Fits / ranks with ``extopt.surrogate_accel`` (ridge acquisition) and may use
  ``optimization.surrogates`` helpers for overlay predictions.
* Emits ``PointInputs`` proposals only — **never** certifies from surrogate scores.
* Every shortlist point must re-eval via frozen ``Evaluator`` / CCFS
  (``lightly_certify_shortlist`` → ``verify_ccfs_bundle``).
* Wires hashed ``ObjectiveContract`` + ``opt_run_stamp.v1`` (driver id
  ``surrogate_propose``).

Honesty: surrogate scores are untrusted guidance. VERIFIED requires CCFS.
L0 risk: none — does not import or mutate ``hot_ion``.
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
    DRIVER_SURROGATE_PROPOSE,
    build_opt_run_stamp,
)

SCHEMA = "surrogate_propose_search_result.v1"
SURROGATE_META_SCHEMA = "surrogate_propose.v1"

# Default continuous knobs (aligned with SLSQP Opt Lab band).
DEFAULT_VARIABLE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "Ip_MA": (4.0, 12.0),
    "fG": (0.4, 1.1),
    "Paux_MW": (5.0, 80.0),
}

DEFAULT_TRAIN_SAMPLES = 48
DEFAULT_POOL = 800
DEFAULT_SHORTLIST_K = 8


class SurrogateProposeSearchDriverError(ValueError):
    """Invalid surrogate propose SearchDriver configuration or result."""


def _as_contract(
    contract: Union[ObjectiveContract, Mapping[str, Any]],
) -> ObjectiveContract:
    if isinstance(contract, ObjectiveContract):
        return contract
    if isinstance(contract, Mapping):
        return parse_objective_contract(contract)
    raise SurrogateProposeSearchDriverError(
        "objective_contract must be ObjectiveContract or mapping"
    )


def _normalize_bounds(
    variables: Optional[Mapping[str, Tuple[float, float]]],
) -> Dict[str, Tuple[float, float]]:
    raw = dict(variables) if variables is not None else dict(DEFAULT_VARIABLE_BOUNDS)
    if not raw:
        raise SurrogateProposeSearchDriverError("variables must be a non-empty bounds map")
    out: Dict[str, Tuple[float, float]] = {}
    for name, pair in raw.items():
        key = str(name).strip()
        if not key:
            raise SurrogateProposeSearchDriverError("variable names must be non-empty")
        try:
            lo, hi = float(pair[0]), float(pair[1])
        except Exception as exc:
            raise SurrogateProposeSearchDriverError(
                f"bounds for {key!r} must be (lo, hi) floats; got {pair!r}"
            ) from exc
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise SurrogateProposeSearchDriverError(f"bounds for {key!r} must be finite")
        if hi < lo:
            raise SurrogateProposeSearchDriverError(
                f"bounds for {key!r}: hi < lo ({hi} < {lo})"
            )
        out[key] = (lo, hi)
    return out


def _point_to_dict(inp: Any) -> Dict[str, Any]:
    if hasattr(inp, "__dict__"):
        return dict(inp.__dict__)
    if isinstance(inp, Mapping):
        return dict(inp)
    raise SurrogateProposeSearchDriverError("base must be PointInputs or a mapping")


def _as_point_inputs(base: Any):
    try:
        from models.inputs import PointInputs  # type: ignore
    except ImportError:
        from src.models.inputs import PointInputs  # type: ignore

    if isinstance(base, PointInputs):
        return base
    if isinstance(base, Mapping):
        return PointInputs(**dict(base))
    raise SurrogateProposeSearchDriverError("base must be PointInputs or a mapping of fields")


def _apply_knobs(base: Any, knobs: Mapping[str, float]) -> Any:
    updates = {str(k): float(v) for k, v in knobs.items()}
    return replace(base, **updates)


_EVALUATOR = None


def _get_evaluator(*, origin: str):
    global _EVALUATOR
    try:
        from evaluator.core import Evaluator  # type: ignore
    except ImportError:
        from src.evaluator.core import Evaluator  # type: ignore

    if _EVALUATOR is None:
        _EVALUATOR = Evaluator(label=str(origin), cache_enabled=True)
    return _EVALUATOR


def _evaluate_outputs(inp: Any, *, origin: str) -> Dict[str, Any]:
    """Frozen choke-point eval for training / guidance (propose-only; not CCFS)."""
    ev = _get_evaluator(origin=origin)
    res = ev.evaluate(inp)
    out = getattr(res, "out", None)
    return dict(out) if isinstance(out, dict) else {}


def _hard_feasible(out: Mapping[str, Any]) -> bool:
    try:
        from constraints.unified import build_all_constraints  # type: ignore
    except ImportError:
        from src.constraints.unified import build_all_constraints  # type: ignore

    bundle = build_all_constraints(dict(out))
    return bool(getattr(bundle, "governance_feasible", False))


def _min_margin_frac(out: Mapping[str, Any]) -> float:
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
            margins.append(1.0 if bool(getattr(c, "passed", False)) else -1.0)
        else:
            try:
                margins.append(float(mf))
            except Exception:
                margins.append(1.0 if bool(getattr(c, "passed", False)) else -1.0)
    if not margins:
        return 1.0 if _hard_feasible(out) else -1.0
    return float(min(margins))


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


def _lhs_sample(
    bounds: Mapping[str, Tuple[float, float]],
    *,
    n: int,
    seed: int,
) -> List[Dict[str, float]]:
    """Deterministic Latin-hypercube-ish samples in bounds (seeded)."""
    names = tuple(sorted(bounds.keys()))
    n_i = max(1, int(n))
    rng = random.Random(int(seed))
    # Stratified grid per dim, then random permute columns.
    strata = list(range(n_i))
    cols: Dict[str, List[float]] = {}
    for name in names:
        lo, hi = bounds[name]
        order = strata[:]
        rng.shuffle(order)
        vals: List[float] = []
        for i, slot in enumerate(order):
            u = (float(slot) + rng.random()) / float(n_i)
            vals.append(float(lo + u * (hi - lo)))
        cols[name] = vals
    return [{name: cols[name][i] for name in names} for i in range(n_i)]


def build_training_records(
    base: Any,
    contract: ObjectiveContract,
    bounds: Mapping[str, Tuple[float, float]],
    *,
    n_samples: int = DEFAULT_TRAIN_SAMPLES,
    seed: int = 0,
    origin: str = "surrogate_propose_train",
) -> Tuple[List[Dict[str, Any]], int]:
    """Seeded LHS + frozen Evaluator → tabular rows for surrogate fit (propose-only)."""
    metric_key = contract.primary_metric_key()
    samples = _lhs_sample(bounds, n=n_samples, seed=seed)
    base_inp = _as_point_inputs(base)
    records: List[Dict[str, Any]] = []
    n_evals = 0
    for knobs in samples:
        inp = _apply_knobs(base_inp, knobs)
        out = _evaluate_outputs(inp, origin=origin)
        n_evals += 1
        metric = _metric_value(out, contract)
        feas = _hard_feasible(out)
        mrg = _min_margin_frac(out)
        row: Dict[str, Any] = dict(knobs)
        row[metric_key] = float(metric) if math.isfinite(metric) else float("nan")
        row["is_feasible"] = bool(feas)
        row["min_margin_frac"] = float(mrg)
        records.append(row)
    return records, n_evals


@dataclass(frozen=True)
class ProposedCandidate:
    """One propose-only candidate (not yet CCFS-certified)."""

    id: str
    inputs: Dict[str, Any]
    proposed_metric: Optional[float]
    surrogate_score: Optional[float]
    hard_feasible_filter: bool
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inputs": dict(self.inputs),
            "proposed_metric": self.proposed_metric,
            "surrogate_score": self.surrogate_score,
            "hard_feasible_filter": bool(self.hard_feasible_filter),
            "rank": int(self.rank),
            "certification": "propose_only",
            "surrogate_uncertified": True,
        }


@dataclass(frozen=True)
class SurrogateProposeSearchResult:
    """Stamp-ready SearchDriver result (Phase 4.1)."""

    search_driver_id: str
    objective_contract: Dict[str, Any]
    objective_contract_hash: str
    seed: int
    n_evals: int
    n_train: int
    variable_names: Tuple[str, ...]
    bounds: Dict[str, Tuple[float, float]]
    candidates: Tuple[ProposedCandidate, ...]
    best: Optional[ProposedCandidate]
    schema: str = SCHEMA
    notes: str = ""
    surrogate_meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "search_driver_id": self.search_driver_id,
            "objective_contract": dict(self.objective_contract),
            "objective_contract_hash": self.objective_contract_hash,
            "seed": int(self.seed),
            "n_evals": int(self.n_evals),
            "n_train": int(self.n_train),
            "variable_names": list(self.variable_names),
            "bounds": {k: [float(lo), float(hi)] for k, (lo, hi) in self.bounds.items()},
            "candidates": [c.to_dict() for c in self.candidates],
            "best": self.best.to_dict() if self.best is not None else None,
            "notes": self.notes,
            "propose_only": True,
            "certification_required": "CCFS",
            "surrogate_never_certifies": True,
            "surrogate_meta": dict(self.surrogate_meta or {}),
        }

    def to_ccfs_bundle(self) -> Dict[str, Any]:
        """CandidateBatch as ``ccfs_bundle.v1`` — claims stay PROPOSED (never VERIFIED)."""
        cands = []
        for c in self.candidates:
            cands.append(
                {
                    "id": c.id,
                    "inputs": dict(c.inputs),
                    "claims": {
                        "proposed_metric": c.proposed_metric,
                        "surrogate_score": c.surrogate_score,
                        "hard_feasible_filter": c.hard_feasible_filter,
                        "search_driver_id": self.search_driver_id,
                        "status": "PROPOSED",  # must never become VERIFIED from claims
                        "surrogate_uncertified": True,
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
                        "surrogate_score": self.best.surrogate_score,
                        "status": "PROPOSED",
                        "surrogate_uncertified": True,
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


def _overlay_predict_optional(
    records: Sequence[Mapping[str, Any]],
    knobs: Mapping[str, float],
    *,
    feature_names: Sequence[str],
    target_key: str,
) -> Optional[float]:
    """Optional overlay via ``optimization.surrogates`` (never authoritative)."""
    try:
        from src.optimization.surrogates import fit_ridge_surrogate, predict_surrogate
    except Exception:
        return None
    samples: List[Dict[str, float]] = []
    targets: List[float] = []
    for r in records:
        try:
            row = {f: float(r[f]) for f in feature_names}
            y = float(r[target_key])
        except Exception:
            continue
        if not all(math.isfinite(v) for v in row.values()) or not math.isfinite(y):
            continue
        samples.append(row)
        targets.append(y)
    if len(samples) < max(4, len(feature_names) + 1):
        return None
    try:
        model = fit_ridge_surrogate(samples, targets, list(feature_names))
        yhat, _unc = predict_surrogate(model, dict(knobs))
        return float(yhat) if math.isfinite(yhat) else None
    except Exception:
        return None


def run_surrogate_propose_search(
    base: Any,
    objective_contract: Union[ObjectiveContract, Mapping[str, Any]],
    *,
    variables: Optional[Mapping[str, Tuple[float, float]]] = None,
    seed: Optional[int] = None,
    training_records: Optional[Sequence[Mapping[str, Any]]] = None,
    n_train: int = DEFAULT_TRAIN_SAMPLES,
    n_pool: int = DEFAULT_POOL,
    shortlist_k: int = DEFAULT_SHORTLIST_K,
    kappa: float = 0.5,
    origin: str = "surrogate_propose_search_driver",
) -> SurrogateProposeSearchResult:
    """Rank candidates with a surrogate, return propose-only shortlist.

    Parameters
    ----------
    base:
        Baseline ``PointInputs`` (or field mapping).
    objective_contract:
        Hashed FoM contract (``objective_contract.v1``).
    variables:
        Continuous bounds ``{name: (lo, hi)}``.
    seed:
        Reproducibility seed.
    training_records:
        Optional pre-built tabular rows (must include knob columns + metric +
        ``min_margin_frac`` / ``is_feasible``). When omitted, a seeded LHS +
        frozen Evaluator builds the training set.
    n_train / n_pool / shortlist_k:
        Training size, acquisition pool, and shortlist length.
    kappa:
        Acquisition exploration weight (``imp + kappa * uncertainty``).

    Notes
    -----
    Surrogate scores **never** set VERIFIED. Call ``lightly_certify_shortlist``
    (or CCFS) for certification.
    """
    contract = _as_contract(objective_contract)
    bounds = _normalize_bounds(variables)
    names = tuple(sorted(bounds.keys()))
    base_inp = _as_point_inputs(base)

    if seed is None:
        seed = contract.seed
    if seed is None:
        if contract.seed_policy in ("required", "fixed"):
            raise SurrogateProposeSearchDriverError(
                f"seed required by objective_contract seed_policy={contract.seed_policy!r}"
            )
        seed = 0
    seed = int(seed)

    metric_key = contract.primary_metric_key()
    sense = contract.sense
    if sense not in (SENSE_MIN, SENSE_MAX):
        raise SurrogateProposeSearchDriverError(f"unsupported sense {sense!r}")

    n_evals = 0
    if training_records is not None:
        records = [dict(r) for r in training_records]
        train_n = len(records)
    else:
        records, n_evals = build_training_records(
            base_inp,
            contract,
            bounds,
            n_samples=max(16, int(n_train)),
            seed=seed,
            origin=origin + "_train",
        )
        train_n = len(records)

    if len(records) < 8:
        raise SurrogateProposeSearchDriverError(
            f"insufficient training records for surrogate propose: {len(records)}"
        )

    try:
        from extopt.surrogate_accel import propose_candidates  # type: ignore
    except ImportError:
        from src.extopt.surrogate_accel import propose_candidates  # type: ignore

    k_want = max(1, int(shortlist_k))
    try:
        proposed_knobs = propose_candidates(
            records=records,
            bounds=bounds,
            objective_key=metric_key,
            objective_sense=sense,
            feasibility_margin_key="min_margin_frac",
            n_pool=max(50, int(n_pool)),
            n_propose=k_want,
            seed=seed,
            kappa=float(kappa),
        )
    except Exception as exc:
        # Deterministic mid-bounds fallback so CCFS path still exercises.
        mid = {n: 0.5 * (lo + hi) for n, (lo, hi) in bounds.items()}
        proposed_knobs = [dict(mid)]
        notes_extra = f"surrogate_fit_failed:{type(exc).__name__}; mid_bounds_fallback"
    else:
        notes_extra = ""

    if not proposed_knobs:
        mid = {n: 0.5 * (lo + hi) for n, (lo, hi) in bounds.items()}
        proposed_knobs = [dict(mid)]
        notes_extra = (notes_extra + ";empty_pool_mid_bounds").lstrip(";")

    candidates: List[ProposedCandidate] = []
    for i, knobs in enumerate(proposed_knobs[:k_want]):
        inp = _apply_knobs(base_inp, knobs)
        # Guidance eval for proposed_metric display only — not certification.
        out = _evaluate_outputs(inp, origin=origin + "_shortlist")
        n_evals += 1
        metric = _metric_value(out, contract)
        feas = _hard_feasible(out)
        overlay = _overlay_predict_optional(
            records, knobs, feature_names=names, target_key=metric_key
        )
        candidates.append(
            ProposedCandidate(
                id=f"surr_{i:04d}",
                inputs=_point_to_dict(inp),
                proposed_metric=metric if math.isfinite(metric) else None,
                surrogate_score=overlay,
                hard_feasible_filter=bool(feas),
                rank=i,
            )
        )

    best = candidates[0] if candidates else None
    meta = {
        "schema": SURROGATE_META_SCHEMA,
        "role": "propose_only",
        "certifier": "CCFS",
        "surrogate_never_sets_verified": True,
        "n_train": int(train_n),
        "n_pool": int(n_pool),
        "kappa": float(kappa),
        "objective_metric_key": metric_key,
        "accel_module": "extopt.surrogate_accel",
        "overlay_module": "optimization.surrogates",
        "notes_extra": notes_extra,
    }
    notes = (
        "Propose-only surrogate SearchDriver. Surrogate ranks candidates; "
        "scores are uncertified. Every shortlist point must re-eval with frozen "
        "L0 / CCFS — never treat surrogate scores as VERIFIED."
    )
    if notes_extra:
        notes = notes + f" ({notes_extra})"

    return SurrogateProposeSearchResult(
        search_driver_id=DRIVER_SURROGATE_PROPOSE,
        objective_contract=contract.to_dict(),
        objective_contract_hash=contract.hash_sha256(),
        seed=seed,
        n_evals=int(n_evals),
        n_train=int(train_n),
        variable_names=names,
        bounds=bounds,
        candidates=tuple(candidates),
        best=best,
        notes=notes,
        surrogate_meta=meta,
    )


def lightly_certify_shortlist(
    result: SurrogateProposeSearchResult,
    *,
    attach_opt_run_stamp: bool = True,
) -> Dict[str, Any]:
    """CCFS pass on the proposal shortlist — sole path to VERIFIED/REJECTED.

    Surrogate scores in claims are ignored by the firewall
    (``claims_never_set_status``).
    """
    bundle = result.to_ccfs_bundle()
    if not bundle.get("candidates"):
        raise SurrogateProposeSearchDriverError("no candidates to certify")
    try:
        from extopt.certified_solve import verify_ccfs_bundle  # type: ignore
    except ImportError:
        from src.extopt.certified_solve import verify_ccfs_bundle  # type: ignore

    return verify_ccfs_bundle(
        bundle,
        opt_run=bundle.get("opt_run"),
        attach_opt_run_stamp=attach_opt_run_stamp,
    )


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
            notes=notes or f"Surrogate propose SearchDriver FoM={name}",
            provenance={"source": "surrogate_propose_search_driver", "role": "propose_only"},
        )
    except ObjectiveContractError as exc:
        raise SurrogateProposeSearchDriverError(str(exc)) from exc
