"""Opt-run artifact stamp (``opt_run_stamp.v1``) — Certified Optimizer Phase 1.2.

Every Opt Lab / CCFS / Pareto / Systems Mode search run should store a
deterministic meta block so results are citeable without putting FoM inside L0:

* SHAMS ``VERSION``
* ``objective_contract.v1`` SHA-256
* reproducibility seed
* search driver id (propose-only; never truth)
* candidate / VERIFIED / REJECTED counts
* stamp SHA-256 (canonical body hash; optional pack SHA when pack bytes given)

Pipeline role:

    ObjectiveContract → SearchDriver → CandidateBatch → CCFS / Evaluator
      → VerifiedFrontier | RejectedAtlas → **opt_run_stamp.v1** → cite pack

L0 risk: none. This module lives under ``src/optimization/`` (studio layer).
SearchDrivers remain propose-only; SHAMS certifies via frozen Evaluator / CCFS.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from src.optimization.objective_contract import (
    ObjectiveContract,
    ObjectiveContractError,
    build_objective_contract,
    canonical_dumps,
    parse_objective_contract,
    sha256_hex,
)

SCHEMA = "opt_run_stamp.v1"

# Known propose-only driver identifiers (Phase 1–4).
DRIVER_CCFS_VERIFY = "ccfs_verify"
DRIVER_LHS = "lhs"
DRIVER_PARETO = "pareto"
DRIVER_RANDOM_SEARCH = "random_search"
DRIVER_BUDGETED_SEARCH = "budgeted_search"
DRIVER_CERTIFIED_SEARCH = "certified_search"
DRIVER_SLSQP = "slsqp"
DRIVER_SLSQP_FALLBACK = "slsqp_fallback"
DRIVER_NSGA2 = "nsga2"
DRIVER_NSGA2_FALLBACK = "nsga2_fallback"
DRIVER_SURROGATE_PROPOSE = "surrogate_propose"

KNOWN_DRIVER_IDS = frozenset(
    {
        DRIVER_CCFS_VERIFY,
        DRIVER_LHS,
        DRIVER_PARETO,
        DRIVER_RANDOM_SEARCH,
        DRIVER_BUDGETED_SEARCH,
        DRIVER_CERTIFIED_SEARCH,
        DRIVER_SLSQP,
        DRIVER_SLSQP_FALLBACK,
        DRIVER_NSGA2,
        DRIVER_NSGA2_FALLBACK,
        DRIVER_SURROGATE_PROPOSE,
    }
)

# Fields hashed into stamp_sha256 (stamp_sha256 itself excluded).
_HASH_BODY_KEYS = (
    "schema",
    "shams_version",
    "objective_contract_hash",
    "seed",
    "search_driver_id",
    "n_candidates",
    "n_verified",
    "n_rejected",
    "pack_sha256",
)


class OptRunStampError(ValueError):
    """Invalid ``opt_run_stamp.v1`` payload."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_shams_version(repo_root: Optional[Path] = None) -> str:
    """Read SHAMS ``VERSION`` file (strip whitespace); ``unknown`` on failure."""
    root = repo_root or _repo_root()
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        return "unknown"


def _normalize_driver_id(driver_id: str) -> str:
    d = str(driver_id).strip()
    if not d:
        raise OptRunStampError("search_driver_id must be a non-empty string")
    # Allow known ids and future additive ids (no vNNN; lowercase_snake preferred).
    if any(ch.isspace() for ch in d):
        raise OptRunStampError(f"search_driver_id must not contain whitespace; got {driver_id!r}")
    return d


def _normalize_seed(seed: Any) -> Optional[int]:
    if seed is None:
        return None
    try:
        return int(seed)
    except (TypeError, ValueError) as exc:
        raise OptRunStampError(f"seed must be an integer or null; got {seed!r}") from exc


def _normalize_count(name: str, value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise OptRunStampError(f"{name} must be an integer; got {value!r}") from exc
    if n < 0:
        raise OptRunStampError(f"{name} must be >= 0; got {n}")
    return n


def _normalize_hex64(name: str, value: Any, *, allow_empty: bool = False) -> str:
    if value is None or value == "":
        if allow_empty:
            return ""
        raise OptRunStampError(f"{name} must be a non-empty hex digest")
    h = str(value).strip().lower()
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise OptRunStampError(f"{name} must be a 64-char lowercase hex SHA-256; got {value!r}")
    return h


def _contract_hash_from(
    objective_contract: Optional[Union[ObjectiveContract, Mapping[str, Any]]] = None,
    *,
    objective_contract_hash: Optional[str] = None,
) -> str:
    if objective_contract is not None:
        if isinstance(objective_contract, ObjectiveContract):
            return objective_contract.hash_sha256()
        if isinstance(objective_contract, Mapping):
            return parse_objective_contract(objective_contract).hash_sha256()
        raise OptRunStampError("objective_contract must be ObjectiveContract or mapping")
    if objective_contract_hash is not None:
        return _normalize_hex64("objective_contract_hash", objective_contract_hash)
    raise OptRunStampError(
        "objective_contract or objective_contract_hash is required for opt_run_stamp.v1"
    )


def default_ccfs_verify_contract(*, seed: Optional[int] = None) -> ObjectiveContract:
    """FoM-free contract used when CCFS batch-verify has no Opt Lab FoM attached.

    Certification-only: metric is the verified count label; never lives in L0.
    """
    return build_objective_contract(
        name="ccfs_batch_verify",
        sense="max",
        metric_keys=["n_status_verified"],
        bounds_policy="driver_default",
        seed_policy="optional" if seed is None else "fixed",
        seed=seed,
        notes=(
            "CCFS batch verify — certify feasibility only; "
            "attach a real ObjectiveContract when FoM search is in play."
        ),
        provenance={"source": "opt_run_stamp.v1", "role": "ccfs_default"},
    )


@dataclass(frozen=True)
class OptRunStamp:
    """Deterministic run meta for Certified Optimizer artifacts."""

    shams_version: str
    objective_contract_hash: str
    search_driver_id: str
    n_candidates: int
    n_verified: int
    n_rejected: int
    seed: Optional[int] = None
    pack_sha256: str = ""
    schema: str = SCHEMA

    def to_dict(self) -> Dict[str, Any]:
        """Serialize including ``stamp_sha256`` of the canonical body."""
        body = self._hash_body()
        out = dict(body)
        out["stamp_sha256"] = sha256_hex(body)
        return out

    def _hash_body(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema": SCHEMA,
            "shams_version": self.shams_version,
            "objective_contract_hash": self.objective_contract_hash,
            "search_driver_id": self.search_driver_id,
            "n_candidates": int(self.n_candidates),
            "n_verified": int(self.n_verified),
            "n_rejected": int(self.n_rejected),
        }
        if self.seed is not None:
            d["seed"] = int(self.seed)
        if self.pack_sha256:
            d["pack_sha256"] = self.pack_sha256
        return d

    def hash_sha256(self) -> str:
        """SHA-256 of canonical stamp body (excludes ``stamp_sha256``)."""
        return sha256_hex(self._hash_body())


def build_opt_run_stamp(
    *,
    search_driver_id: str,
    n_candidates: int,
    n_verified: int,
    n_rejected: int,
    objective_contract: Optional[Union[ObjectiveContract, Mapping[str, Any]]] = None,
    objective_contract_hash: Optional[str] = None,
    seed: Optional[int] = None,
    shams_version: Optional[str] = None,
    pack_sha256: Optional[str] = None,
    pack_bytes: Optional[bytes] = None,
    repo_root: Optional[Path] = None,
) -> OptRunStamp:
    """Validate and construct an ``opt_run_stamp.v1`` record."""
    oc_hash = _contract_hash_from(
        objective_contract, objective_contract_hash=objective_contract_hash
    )
    driver = _normalize_driver_id(search_driver_id)
    n_cand = _normalize_count("n_candidates", n_candidates)
    n_ver = _normalize_count("n_verified", n_verified)
    n_rej = _normalize_count("n_rejected", n_rejected)
    if n_ver + n_rej > n_cand:
        raise OptRunStampError(
            f"n_verified ({n_ver}) + n_rejected ({n_rej}) exceeds n_candidates ({n_cand})"
        )
    seed_n = _normalize_seed(seed)
    version = str(shams_version).strip() if shams_version else read_shams_version(repo_root)
    if not version:
        version = "unknown"

    pack_h = ""
    if pack_bytes is not None:
        pack_h = hashlib.sha256(pack_bytes).hexdigest()
    elif pack_sha256:
        pack_h = _normalize_hex64("pack_sha256", pack_sha256)

    return OptRunStamp(
        shams_version=version,
        objective_contract_hash=oc_hash,
        search_driver_id=driver,
        n_candidates=n_cand,
        n_verified=n_ver,
        n_rejected=n_rej,
        seed=seed_n,
        pack_sha256=pack_h,
        schema=SCHEMA,
    )


def parse_opt_run_stamp(payload: Mapping[str, Any]) -> OptRunStamp:
    """Parse and validate a dict as ``opt_run_stamp.v1``."""
    if not isinstance(payload, Mapping):
        raise OptRunStampError("opt run stamp must be a mapping")
    schema = str(payload.get("schema", "")).strip()
    if schema != SCHEMA:
        raise OptRunStampError(f"unsupported schema {schema!r}; expected {SCHEMA!r}")

    stamp = build_opt_run_stamp(
        search_driver_id=str(payload.get("search_driver_id", "")),
        n_candidates=payload.get("n_candidates", -1),
        n_verified=payload.get("n_verified", -1),
        n_rejected=payload.get("n_rejected", -1),
        objective_contract_hash=payload.get("objective_contract_hash"),
        seed=payload.get("seed"),
        shams_version=str(payload.get("shams_version", "") or "unknown"),
        pack_sha256=payload.get("pack_sha256") or None,
    )
    # If caller included stamp_sha256, verify integrity.
    expected = payload.get("stamp_sha256")
    if expected is not None and str(expected).strip():
        got = stamp.hash_sha256()
        want = _normalize_hex64("stamp_sha256", expected)
        if got != want:
            raise OptRunStampError(
                f"stamp_sha256 mismatch: payload={want} recomputed={got}"
            )
    return stamp


def stamp_hash(payload: Mapping[str, Any]) -> str:
    """Validate then return SHA-256 of the normalized stamp body."""
    return parse_opt_run_stamp(payload).hash_sha256()


def build_stamp_from_ccfs_result(
    result: Mapping[str, Any],
    *,
    objective_contract: Optional[Union[ObjectiveContract, Mapping[str, Any]]] = None,
    objective_contract_hash: Optional[str] = None,
    seed: Optional[int] = None,
    search_driver_id: str = DRIVER_CCFS_VERIFY,
    shams_version: Optional[str] = None,
    pack_bytes: Optional[bytes] = None,
    repo_root: Optional[Path] = None,
) -> OptRunStamp:
    """Build a stamp from a ``ccfs_verified.v1`` result dict."""
    n_cand = int(result.get("n_candidates", 0) or 0)
    n_ver = int(result.get("n_status_verified", 0) or 0)
    n_rej = int(result.get("n_status_rejected", 0) or 0)
    # Fallback: count rows if summary keys missing.
    rows = result.get("verified")
    if isinstance(rows, list) and n_cand == 0:
        n_cand = len(rows)
        n_ver = sum(1 for r in rows if isinstance(r, dict) and r.get("status") == "VERIFIED")
        n_rej = n_cand - n_ver

    if objective_contract is None and objective_contract_hash is None:
        objective_contract = default_ccfs_verify_contract(seed=seed)

    return build_opt_run_stamp(
        search_driver_id=search_driver_id,
        n_candidates=n_cand,
        n_verified=n_ver,
        n_rejected=n_rej,
        objective_contract=objective_contract,
        objective_contract_hash=objective_contract_hash,
        seed=seed,
        shams_version=shams_version,
        pack_bytes=pack_bytes,
        repo_root=repo_root,
    )


def attach_opt_run_stamp(
    result: Dict[str, Any],
    stamp: Union[OptRunStamp, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Attach ``opt_run_stamp`` key to a result dict (mutates and returns)."""
    if isinstance(stamp, OptRunStamp):
        result["opt_run_stamp"] = stamp.to_dict()
    else:
        result["opt_run_stamp"] = parse_opt_run_stamp(stamp).to_dict()
    return result


def stamp_ccfs_verified(
    result: Dict[str, Any],
    *,
    objective_contract: Optional[Union[ObjectiveContract, Mapping[str, Any]]] = None,
    objective_contract_hash: Optional[str] = None,
    seed: Optional[int] = None,
    search_driver_id: str = DRIVER_CCFS_VERIFY,
    shams_version: Optional[str] = None,
    pack_bytes: Optional[bytes] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build stamp from CCFS result and attach under ``opt_run_stamp``."""
    stamp = build_stamp_from_ccfs_result(
        result,
        objective_contract=objective_contract,
        objective_contract_hash=objective_contract_hash,
        seed=seed,
        search_driver_id=search_driver_id,
        shams_version=shams_version,
        pack_bytes=pack_bytes,
        repo_root=repo_root,
    )
    return attach_opt_run_stamp(result, stamp)


def format_opt_run_stamp_summary(stamp: Union[OptRunStamp, Mapping[str, Any], None]) -> str:
    """One-line user-facing summary (no ``vNNN`` labels; honesty-safe)."""
    if stamp is None:
        return "No opt-run stamp yet — run a certified search to stamp VERSION + contract hash."
    if isinstance(stamp, OptRunStamp):
        d = stamp.to_dict()
    else:
        d = dict(stamp)
    driver = d.get("search_driver_id", "?")
    n_v = d.get("n_verified", "?")
    n_r = d.get("n_rejected", "?")
    n_c = d.get("n_candidates", "?")
    ver = d.get("shams_version", "?")
    oc = str(d.get("objective_contract_hash", ""))[:12]
    sha = str(d.get("stamp_sha256", ""))[:12]
    seed = d.get("seed")
    seed_bit = f" seed={seed}" if seed is not None else ""
    return (
        f"Last run stamp: driver={driver} candidates={n_c} "
        f"VERIFIED={n_v} REJECTED={n_r} VERSION={ver} "
        f"contract={oc}… stamp={sha}…{seed_bit}"
    )


def resolve_opt_run_meta_from_bundle(
    bundle: Mapping[str, Any],
    *,
    opt_run: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge optional ``opt_run`` kwarg with ``bundle['opt_run']`` for stamp inputs."""
    meta: Dict[str, Any] = {}
    raw = bundle.get("opt_run")
    if isinstance(raw, Mapping):
        meta.update(dict(raw))
    if isinstance(opt_run, Mapping):
        meta.update(dict(opt_run))
    return meta


# Re-export for callers that need contract errors alongside stamp errors.
__all__ = [
    "SCHEMA",
    "KNOWN_DRIVER_IDS",
    "DRIVER_CCFS_VERIFY",
    "DRIVER_LHS",
    "DRIVER_PARETO",
    "DRIVER_RANDOM_SEARCH",
    "DRIVER_BUDGETED_SEARCH",
    "DRIVER_CERTIFIED_SEARCH",
    "DRIVER_SLSQP",
    "DRIVER_SLSQP_FALLBACK",
    "DRIVER_NSGA2",
    "DRIVER_NSGA2_FALLBACK",
    "DRIVER_SURROGATE_PROPOSE",
    "OptRunStamp",
    "OptRunStampError",
    "ObjectiveContractError",
    "read_shams_version",
    "default_ccfs_verify_contract",
    "build_opt_run_stamp",
    "parse_opt_run_stamp",
    "stamp_hash",
    "build_stamp_from_ccfs_result",
    "attach_opt_run_stamp",
    "stamp_ccfs_verified",
    "format_opt_run_stamp_summary",
    "resolve_opt_run_meta_from_bundle",
    "canonical_dumps",
]
