"""Bridge ExtOpt wire contracts ↔ Opt Lab ObjectiveContract schemas.

Certified Optimizer Phase 3.3. External Optimizer / orchestrator still speak
``objective_contract.v3`` (and legacy ``.v2``) on the job wire. Opt Lab /
NSGA / SLSQP stamp ``objective_contract.v1`` and ``multi_objective_contract.v1``.

This module is the **only** intentional dual-schema seam:

* ExtOpt wire stays ``objective_contract.v3`` so ``OptimizerJob`` / orchestrator
  validation keeps working.
* Every ExtOpt job that feeds Opt Lab / Pareto also carries an Opt Lab contract
  (``opt_lab_contract``) plus honesty metadata — never a silent dual-truth FoM.

L0 risk: none — FoM schemas only; no evaluator or frozen-physics imports.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from src.optimization.objective_contract import (
    BOUNDS_USER_SUPPLIED,
    MULTI_SCHEMA,
    SCHEMA as OPT_LAB_SCHEMA,
    SEED_OPTIONAL,
    SEED_REQUIRED,
    MultiObjectiveContract,
    ObjectiveContract,
    ObjectiveContractError,
    build_multi_objective_contract,
    build_objective_contract,
    parse_multi_objective_contract,
    parse_objective_contract,
)

# ExtOpt / orchestrator wire schemas (must remain accepted by OptimizerJob).
EXTOPT_SCHEMA_V3 = "objective_contract.v3"
EXTOPT_SCHEMA_V2 = "objective_contract.v2"

BRIDGE_SCHEMA = "extopt_opt_lab_contract_bridge.v1"

EXTOPT_LEGACY_HONESTY = (
    "ExtOpt wire uses legacy objective_contract.v3 for OptimizerJob compatibility; "
    "Opt Lab / Pareto certification stamps objective_contract.v1 or "
    "multi_objective_contract.v1. FoM never lives in L0; Proposed — SHAMS-certified "
    "only after CCFS / frozen re-eval — not a true minimum."
)


class ExtOptContractBridgeError(ValueError):
    """Invalid ExtOpt ↔ Opt Lab contract bridge payload."""


def _norm_sense(sense: Any) -> str:
    s = str(sense or "min").strip().lower()
    if s not in ("min", "max"):
        raise ExtOptContractBridgeError(f"invalid sense {sense!r}")
    return s


def _extract_v3_objectives(payload: Mapping[str, Any]) -> List[Tuple[str, str]]:
    schema = str(payload.get("schema", "")).strip()
    out: List[Tuple[str, str]] = []
    if schema == EXTOPT_SCHEMA_V3:
        raw = payload.get("objectives")
        if not isinstance(raw, list) or not raw:
            raise ExtOptContractBridgeError(
                "objective_contract.v3 requires non-empty objectives list"
            )
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            key = str(item.get("key", "")).strip()
            if not key:
                continue
            out.append((key, _norm_sense(item.get("sense", "min"))))
    elif schema == EXTOPT_SCHEMA_V2:
        prim = payload.get("primary")
        if isinstance(prim, Mapping):
            key = str(prim.get("key", "")).strip()
            if key:
                out.append((key, _norm_sense(prim.get("sense", "min"))))
        sec = payload.get("secondary")
        if isinstance(sec, list):
            for item in sec:
                if not isinstance(item, Mapping):
                    continue
                key = str(item.get("key", "")).strip()
                if key:
                    out.append((key, _norm_sense(item.get("sense", "min"))))
    else:
        raise ExtOptContractBridgeError(
            f"unsupported ExtOpt schema {schema!r}; "
            f"expected {EXTOPT_SCHEMA_V3!r} or {EXTOPT_SCHEMA_V2!r}"
        )
    if not out:
        raise ExtOptContractBridgeError("ExtOpt contract has no valid objectives")
    keys = [k for k, _ in out]
    if len(set(keys)) != len(keys):
        raise ExtOptContractBridgeError("ExtOpt objective keys must be unique")
    return out


def metric_objectives_to_opt_lab_contracts(
    objectives: Sequence[Tuple[str, str]],
    *,
    seed: Optional[int] = None,
    seed_policy: str = SEED_OPTIONAL,
    bounds_policy: str = BOUNDS_USER_SUPPLIED,
    notes: str = "",
) -> Union[ObjectiveContract, MultiObjectiveContract]:
    """Map (metric_key, sense) pairs → Opt Lab v1 or multi_objective_contract.v1."""
    if not objectives:
        raise ExtOptContractBridgeError("need >= 1 (metric_key, sense) pair")
    children: List[ObjectiveContract] = []
    for key, sense in objectives:
        children.append(
            build_objective_contract(
                name=str(key),
                sense=sense,
                metric_keys=(str(key),),
                bounds_policy=bounds_policy,
                seed_policy=seed_policy,
                seed=seed if seed_policy != SEED_OPTIONAL else seed,
                notes=notes or EXTOPT_LEGACY_HONESTY,
                provenance={
                    "source": "extopt_wire",
                    "bridge": BRIDGE_SCHEMA,
                },
            )
        )
    if len(children) == 1:
        return children[0]
    return build_multi_objective_contract(
        children,
        name="extopt_bridged_multi",
        bounds_policy=bounds_policy,
        seed_policy=seed_policy,
        seed=seed if seed_policy != SEED_OPTIONAL else seed,
        notes=notes or EXTOPT_LEGACY_HONESTY,
    )


def extopt_v3_to_opt_lab(
    payload: Mapping[str, Any],
    *,
    seed: Optional[int] = None,
    seed_policy: str = SEED_OPTIONAL,
) -> Union[ObjectiveContract, MultiObjectiveContract]:
    """Convert ExtOpt ``objective_contract.v2|v3`` → Opt Lab hashed contract."""
    pairs = _extract_v3_objectives(payload)
    return metric_objectives_to_opt_lab_contracts(
        pairs, seed=seed, seed_policy=seed_policy
    )


def opt_lab_to_extopt_v3(
    contract: Union[
        ObjectiveContract,
        MultiObjectiveContract,
        Mapping[str, Any],
    ],
) -> Dict[str, Any]:
    """Emit orchestrator-compatible ``objective_contract.v3`` from Opt Lab contract."""
    if isinstance(contract, ObjectiveContract):
        objs = [
            {"key": contract.primary_metric_key(), "sense": contract.sense},
        ]
    elif isinstance(contract, MultiObjectiveContract):
        objs = [
            {"key": oc.primary_metric_key(), "sense": oc.sense}
            for oc in contract.objectives
        ]
    elif isinstance(contract, Mapping):
        schema = str(contract.get("schema", "")).strip()
        if schema == OPT_LAB_SCHEMA:
            oc = parse_objective_contract(contract)
            objs = [{"key": oc.primary_metric_key(), "sense": oc.sense}]
        elif schema == MULTI_SCHEMA:
            multi = parse_multi_objective_contract(contract)
            objs = [
                {"key": oc.primary_metric_key(), "sense": oc.sense}
                for oc in multi.objectives
            ]
        elif schema in (EXTOPT_SCHEMA_V3, EXTOPT_SCHEMA_V2):
            # Already ExtOpt — normalize to v3.
            pairs = _extract_v3_objectives(contract)
            objs = [{"key": k, "sense": s} for k, s in pairs]
        else:
            raise ExtOptContractBridgeError(
                f"cannot map schema {schema!r} to ExtOpt v3"
            )
    else:
        raise ExtOptContractBridgeError(
            "contract must be ObjectiveContract, MultiObjectiveContract, or mapping"
        )
    if not objs:
        raise ExtOptContractBridgeError("no objectives to emit as ExtOpt v3")
    return {
        "schema": EXTOPT_SCHEMA_V3,
        "objectives": objs,
        "bridge": {
            "schema": BRIDGE_SCHEMA,
            "honesty": EXTOPT_LEGACY_HONESTY,
            "opt_lab_schemas": [OPT_LAB_SCHEMA, MULTI_SCHEMA],
        },
    }


def build_bridged_extopt_job_contract(
    *,
    objectives: Sequence[str],
    senses: Mapping[str, Any],
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Build ExtOpt v3 wire payload **with** Opt Lab contract attached.

    Returned dict is safe to pass as ``OptimizerJob.objective_contract``
    (orchestrator reads ``schema`` + ``objectives``; Opt Lab / Pareto read
    ``opt_lab_contract`` + ``bridge`` honesty).
    """
    objs = [str(o).strip() for o in objectives if str(o).strip()]
    if not objs:
        raise ExtOptContractBridgeError("objectives must be non-empty")
    pairs = [(o, _norm_sense(senses.get(o, "min"))) for o in objs]
    opt_lab = metric_objectives_to_opt_lab_contracts(
        pairs,
        seed=seed,
        seed_policy=SEED_REQUIRED if seed is not None else SEED_OPTIONAL,
    )
    wire = opt_lab_to_extopt_v3(opt_lab)
    wire["opt_lab_contract"] = opt_lab.to_dict()
    wire["opt_lab_contract_hash"] = opt_lab.hash_sha256()
    wire["honesty"] = EXTOPT_LEGACY_HONESTY
    return wire


def resolve_opt_lab_contract_from_extopt_payload(
    payload: Mapping[str, Any],
) -> Union[ObjectiveContract, MultiObjectiveContract]:
    """Prefer embedded ``opt_lab_contract``; else bridge from ExtOpt v2/v3."""
    embedded = payload.get("opt_lab_contract")
    if isinstance(embedded, Mapping):
        schema = str(embedded.get("schema", "")).strip()
        if schema == OPT_LAB_SCHEMA:
            return parse_objective_contract(embedded)
        if schema == MULTI_SCHEMA:
            return parse_multi_objective_contract(embedded)
        raise ExtOptContractBridgeError(
            f"embedded opt_lab_contract has unsupported schema {schema!r}"
        )
    return extopt_v3_to_opt_lab(payload)


def bridge_meta_summary(payload: Mapping[str, Any]) -> str:
    """One-line honesty summary for UI (no version tags in user labels)."""
    schema = str(payload.get("schema", "")).strip()
    hash_hex = str(payload.get("opt_lab_contract_hash") or "").strip()
    short = (hash_hex[:12] + "…") if len(hash_hex) > 12 else (hash_hex or "unset")
    return (
        f"ExtOpt wire={schema or 'unknown'} · Opt Lab contract hash={short} — "
        "Proposed — SHAMS-certified after CCFS (legacy ExtOpt FoM is not L0 truth)."
    )
