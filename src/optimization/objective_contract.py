"""ObjectiveContract (``objective_contract.v1``) — Opt Lab FoM outside L0.

Certified Optimizer Phase 0.1. SearchDrivers and Opt Lab runs stamp a hashed
contract; FoM never lives inside ``Evaluator`` / ``hot_ion``.

Pipeline role (propose-only):

    ObjectiveContract → SearchDriver → CandidateBatch → CCFS / Evaluator

This schema is the Opt Lab foundation. Extopt orchestrator still uses legacy
``objective_contract.v2`` / ``.v3`` JSON shapes; those remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from src.optimization.objectives import ObjectiveSpec, get_objective, list_objectives

SCHEMA = "objective_contract.v1"

SENSE_MIN = "min"
SENSE_MAX = "max"
ALLOWED_SENSES = frozenset({SENSE_MIN, SENSE_MAX})

# How SearchDriver obtains variable bounds for a run.
BOUNDS_FIXED = "fixed"
BOUNDS_USER_SUPPLIED = "user_supplied"
BOUNDS_DRIVER_DEFAULT = "driver_default"
ALLOWED_BOUNDS_POLICIES = frozenset(
    {BOUNDS_FIXED, BOUNDS_USER_SUPPLIED, BOUNDS_DRIVER_DEFAULT}
)

# How reproducibility seed is treated for a run.
SEED_REQUIRED = "required"
SEED_FIXED = "fixed"
SEED_OPTIONAL = "optional"
ALLOWED_SEED_POLICIES = frozenset({SEED_REQUIRED, SEED_FIXED, SEED_OPTIONAL})

# Registry FoM name → output metric keys (mirrors defaults in objectives.py).
_LEGACY_METRIC_KEYS: Dict[str, Tuple[str, ...]] = {
    "min_R0": ("R0_m",),
    "min_Bpeak": ("B_peak_T",),
    "max_Pnet": ("P_e_net_MW",),
    "min_COE": ("COE_proxy_USD_per_MWh",),
    "min_precirc": ("P_recirc_MW",),
    "max_Q": ("Q_DT_eqv", "Q"),
    "max_H98": ("H98",),
    "min_q_div": ("q_div_MW_m2",),
    "max_TBR": ("TBR",),
    "min_sigma_vm": ("sigma_vm_MPa",),
}


class ObjectiveContractError(ValueError):
    """Invalid ``objective_contract.v1`` payload."""


def _canon_for_hash(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            str(k): _canon_for_hash(v)
            for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(obj, (list, tuple)):
        return [_canon_for_hash(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if obj is None:
        return None
    return str(obj)


def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON for hashing (sorted keys, tight separators)."""
    return json.dumps(
        _canon_for_hash(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def _normalize_metric_keys(keys: Sequence[str]) -> Tuple[str, ...]:
    out: List[str] = []
    seen = set()
    for raw in keys:
        key = str(raw).strip()
        if not key:
            raise ObjectiveContractError("metric_keys entries must be non-empty strings")
        if key in seen:
            raise ObjectiveContractError(f"duplicate metric key: {key}")
        seen.add(key)
        out.append(key)
    if not out:
        raise ObjectiveContractError("metric_keys must be a non-empty list")
    return tuple(out)


def _normalize_sense(sense: str) -> str:
    s = str(sense).strip().lower()
    if s not in ALLOWED_SENSES:
        raise ObjectiveContractError(
            f"sense must be one of {sorted(ALLOWED_SENSES)}; got {sense!r}"
        )
    return s


def _normalize_bounds_policy(policy: str) -> str:
    p = str(policy).strip().lower()
    if p not in ALLOWED_BOUNDS_POLICIES:
        raise ObjectiveContractError(
            f"bounds_policy must be one of {sorted(ALLOWED_BOUNDS_POLICIES)}; got {policy!r}"
        )
    return p


def _normalize_seed_policy(policy: str) -> str:
    p = str(policy).strip().lower()
    if p not in ALLOWED_SEED_POLICIES:
        raise ObjectiveContractError(
            f"seed_policy must be one of {sorted(ALLOWED_SEED_POLICIES)}; got {policy!r}"
        )
    return p


def _normalize_seed(seed: Optional[int], seed_policy: str) -> Optional[int]:
    if seed_policy == SEED_FIXED:
        if seed is None:
            raise ObjectiveContractError("seed_policy='fixed' requires an integer seed")
        try:
            return int(seed)
        except (TypeError, ValueError) as exc:
            raise ObjectiveContractError(f"seed must be an integer; got {seed!r}") from exc
    if seed is not None:
        try:
            return int(seed)
        except (TypeError, ValueError) as exc:
            raise ObjectiveContractError(f"seed must be an integer; got {seed!r}") from exc
    return None


def _normalize_provenance(prov: Any) -> Optional[Dict[str, Any]]:
    if prov is None:
        return None
    if not isinstance(prov, Mapping):
        raise ObjectiveContractError("provenance must be a mapping or null")
    return {str(k): prov[k] for k in sorted(prov.keys(), key=str)}


@dataclass(frozen=True)
class ObjectiveContract:
    """Hashed FoM contract for Certified Optimizer / Opt Lab runs.

    Lives outside L0. Drivers propose ``PointInputs`` only; SHAMS certifies via
    CCFS / frozen evaluator.
    """

    name: str
    sense: str
    metric_keys: Tuple[str, ...]
    bounds_policy: str
    seed_policy: str
    seed: Optional[int] = None
    notes: str = ""
    provenance: Optional[Dict[str, Any]] = None
    schema: str = SCHEMA

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to stable ``objective_contract.v1`` JSON object."""
        d: Dict[str, Any] = {
            "schema": SCHEMA,
            "name": self.name,
            "sense": self.sense,
            "metric_keys": list(self.metric_keys),
            "bounds_policy": self.bounds_policy,
            "seed_policy": self.seed_policy,
            "notes": self.notes,
        }
        if self.seed is not None:
            d["seed"] = int(self.seed)
        if self.provenance is not None:
            d["provenance"] = dict(self.provenance)
        return d

    def hash_sha256(self) -> str:
        """SHA-256 of canonical JSON — stamp into opt-run artifacts."""
        return sha256_hex(self.to_dict())

    def primary_metric_key(self) -> str:
        return self.metric_keys[0]


def build_objective_contract(
    *,
    name: str,
    sense: str,
    metric_keys: Sequence[str],
    bounds_policy: str = BOUNDS_USER_SUPPLIED,
    seed_policy: str = SEED_REQUIRED,
    seed: Optional[int] = None,
    notes: str = "",
    provenance: Optional[Mapping[str, Any]] = None,
) -> ObjectiveContract:
    """Validate and construct an ``ObjectiveContract``."""
    n = str(name).strip()
    if not n:
        raise ObjectiveContractError("name must be a non-empty string")
    sense_n = _normalize_sense(sense)
    keys = _normalize_metric_keys(metric_keys)
    bp = _normalize_bounds_policy(bounds_policy)
    sp = _normalize_seed_policy(seed_policy)
    seed_n = _normalize_seed(seed, sp)
    notes_n = str(notes) if notes is not None else ""
    prov = _normalize_provenance(provenance)
    return ObjectiveContract(
        name=n,
        sense=sense_n,
        metric_keys=keys,
        bounds_policy=bp,
        seed_policy=sp,
        seed=seed_n,
        notes=notes_n,
        provenance=prov,
        schema=SCHEMA,
    )


def parse_objective_contract(payload: Mapping[str, Any]) -> ObjectiveContract:
    """Parse and validate a dict as ``objective_contract.v1``."""
    if not isinstance(payload, Mapping):
        raise ObjectiveContractError("objective contract must be a mapping")
    schema = str(payload.get("schema", "")).strip()
    if schema != SCHEMA:
        raise ObjectiveContractError(
            f"unsupported schema {schema!r}; expected {SCHEMA!r}"
        )
    raw_keys = payload.get("metric_keys")
    if not isinstance(raw_keys, (list, tuple)):
        raise ObjectiveContractError("metric_keys must be a list of strings")
    return build_objective_contract(
        name=str(payload.get("name", "")),
        sense=str(payload.get("sense", "")),
        metric_keys=list(raw_keys),
        bounds_policy=str(payload.get("bounds_policy", BOUNDS_USER_SUPPLIED)),
        seed_policy=str(payload.get("seed_policy", SEED_REQUIRED)),
        seed=payload.get("seed"),
        notes=str(payload.get("notes", "") or ""),
        provenance=payload.get("provenance"),
    )


def contract_hash(payload: Mapping[str, Any]) -> str:
    """Validate then return SHA-256 of the normalized contract."""
    return parse_objective_contract(payload).hash_sha256()


def legacy_metric_keys(objective_name: str) -> Optional[Tuple[str, ...]]:
    """Return metric keys for a registered FoM name, if known."""
    keys = _LEGACY_METRIC_KEYS.get(str(objective_name).strip())
    return keys


def from_registry_name(
    objective_name: str,
    *,
    bounds_policy: str = BOUNDS_USER_SUPPLIED,
    seed_policy: str = SEED_REQUIRED,
    seed: Optional[int] = None,
    notes: str = "",
    provenance: Optional[Mapping[str, Any]] = None,
) -> ObjectiveContract:
    """Build a contract from a legacy ``objectives.py`` registry FoM name.

    Resolves sense from ``ObjectiveSpec`` and metric keys from the Opt Lab
    legacy map (same keys the default FoM lambdas read).
    """
    name = str(objective_name).strip()
    spec: Optional[ObjectiveSpec] = get_objective(name)
    if spec is None:
        raise ObjectiveContractError(
            f"unknown registry objective {name!r}; known={sorted(list_objectives())}"
        )
    keys = legacy_metric_keys(name)
    if keys is None:
        raise ObjectiveContractError(
            f"registry objective {name!r} has no metric_keys mapping for {SCHEMA}"
        )
    note = notes or (spec.description or "")
    return build_objective_contract(
        name=spec.name,
        sense=spec.sense,
        metric_keys=keys,
        bounds_policy=bounds_policy,
        seed_policy=seed_policy,
        seed=seed,
        notes=note,
        provenance=provenance,
    )


def list_registry_contract_names() -> List[str]:
    """FoM names that can resolve via ``from_registry_name``."""
    return sorted(k for k in _LEGACY_METRIC_KEYS if get_objective(k) is not None)


# ---------------------------------------------------------------------------
# Multi-objective contract bundle (Phase 3.1 — FoM list outside L0)
# ---------------------------------------------------------------------------

MULTI_SCHEMA = "multi_objective_contract.v1"


@dataclass(frozen=True)
class MultiObjectiveContract:
    """Hashed list of ``objective_contract.v1`` FoMs for MOEA SearchDrivers.

    Lives outside L0. Metric senses stay on each child contract; the combined
    SHA-256 stamps Opt Lab / CCFS runs without putting FoM inside ``hot_ion``.
    """

    name: str
    objectives: Tuple[ObjectiveContract, ...]
    bounds_policy: str = BOUNDS_USER_SUPPLIED
    seed_policy: str = SEED_REQUIRED
    seed: Optional[int] = None
    notes: str = ""
    schema: str = MULTI_SCHEMA

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema": MULTI_SCHEMA,
            "name": self.name,
            "objectives": [o.to_dict() for o in self.objectives],
            "bounds_policy": self.bounds_policy,
            "seed_policy": self.seed_policy,
            "notes": self.notes,
        }
        if self.seed is not None:
            d["seed"] = int(self.seed)
        return d

    def hash_sha256(self) -> str:
        return sha256_hex(self.to_dict())

    def metric_senses(self) -> Dict[str, str]:
        """Map primary metric key → sense for nondominated sort / crowding."""
        out: Dict[str, str] = {}
        for oc in self.objectives:
            key = oc.primary_metric_key()
            if key in out and out[key] != oc.sense:
                raise ObjectiveContractError(
                    f"conflicting sense for metric {key!r}: {out[key]!r} vs {oc.sense!r}"
                )
            out[key] = oc.sense
        return out

    def primary_metric_keys(self) -> Tuple[str, ...]:
        return tuple(oc.primary_metric_key() for oc in self.objectives)


def build_multi_objective_contract(
    objectives: Sequence[Union[ObjectiveContract, Mapping[str, Any]]],
    *,
    name: str = "multi_objective",
    bounds_policy: str = BOUNDS_USER_SUPPLIED,
    seed_policy: str = SEED_REQUIRED,
    seed: Optional[int] = None,
    notes: str = "",
) -> MultiObjectiveContract:
    """Validate and construct a ``multi_objective_contract.v1`` bundle."""
    if not objectives:
        raise ObjectiveContractError("multi-objective contract needs >= 1 objective")
    parsed: List[ObjectiveContract] = []
    for raw in objectives:
        if isinstance(raw, ObjectiveContract):
            parsed.append(raw)
        elif isinstance(raw, Mapping):
            parsed.append(parse_objective_contract(raw))
        else:
            raise ObjectiveContractError(
                "each objective must be ObjectiveContract or objective_contract.v1 mapping"
            )
    if len(parsed) < 2:
        raise ObjectiveContractError(
            "multi-objective contract requires at least two ObjectiveContracts"
        )
    n = str(name).strip()
    if not n:
        raise ObjectiveContractError("name must be a non-empty string")
    bp = _normalize_bounds_policy(bounds_policy)
    sp = _normalize_seed_policy(seed_policy)
    seed_n = _normalize_seed(seed, sp)
    bundle = MultiObjectiveContract(
        name=n,
        objectives=tuple(parsed),
        bounds_policy=bp,
        seed_policy=sp,
        seed=seed_n,
        notes=str(notes) if notes is not None else "",
        schema=MULTI_SCHEMA,
    )
    # Validate metric sense map early (duplicate keys with conflicting sense).
    _ = bundle.metric_senses()
    return bundle


def parse_multi_objective_contract(payload: Mapping[str, Any]) -> MultiObjectiveContract:
    """Parse and validate a dict as ``multi_objective_contract.v1``."""
    if not isinstance(payload, Mapping):
        raise ObjectiveContractError("multi-objective contract must be a mapping")
    schema = str(payload.get("schema", "")).strip()
    if schema != MULTI_SCHEMA:
        raise ObjectiveContractError(
            f"unsupported schema {schema!r}; expected {MULTI_SCHEMA!r}"
        )
    raw_objs = payload.get("objectives")
    if not isinstance(raw_objs, (list, tuple)):
        raise ObjectiveContractError("objectives must be a list of contracts")
    return build_multi_objective_contract(
        list(raw_objs),
        name=str(payload.get("name", "multi_objective")),
        bounds_policy=str(payload.get("bounds_policy", BOUNDS_USER_SUPPLIED)),
        seed_policy=str(payload.get("seed_policy", SEED_REQUIRED)),
        seed=payload.get("seed"),
        notes=str(payload.get("notes", "") or ""),
    )
