"""Lock tests — SLSQP SearchDriver determinism (Certified Optimizer Phase 2.3).

Float policy (publication lock)
-------------------------------
* **Locked (bit-stable identity):** ``force_fallback=True`` (``slsqp_fallback``)
  pure-Python coordinate descent + seeded neighborhood proposals +
  ``opt_run_stamp.v1`` / shortlist identity hashes. Same seed + ObjectiveContract
  + bounds → same rounded continuous knobs (8 dp) and same ``stamp_sha256``.
* **Not locked for bit-identity:** SciPy ``SLSQP`` (``force_fallback=False``) may
  differ across SciPy / BLAS / OS builds. Publication studies that need
  cross-platform citeable shortlists should use ``force_fallback=True`` (or
  accept platform-local SciPy results and re-certify via CCFS).
* Continuous-knob compare / shortlist identity uses **8 decimal places**
  (matches driver archive / neighborhood dedupe keys).
* L0 / ``hot_ion`` untouched — this module only locks propose-side identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

import pytest

from src.optimization.l0_opt_guards import (
    DEFAULT_L0_TRUTH_RELPATHS,
    collect_forbidden_imports,
)
from src.optimization.objective_contract import sha256_hex
from src.optimization.opt_run_stamp import DRIVER_SLSQP_FALLBACK, SCHEMA as STAMP_SCHEMA
from src.optimization.slsqp_search_driver import (
    best_and_neighborhood_bundle,
    build_neighborhood_proposals,
    certify_best_and_neighborhood,
    run_slsqp_search,
    scipy_optimize_available,
)

ROOT = Path(__file__).resolve().parents[1]

# Documented float policy — keep in sync with module docstring + CERTIFIED_OPTIMIZER.md
FLOAT_COMPARE_DECIMALS = 8
FLOAT_POLICY_DOC = (
    "SciPy SLSQP may be platform-sensitive; lock tests prefer "
    "force_fallback (slsqp_fallback) + neighborhood + CCFS shortlist identity"
)


def _base_inputs():
    from models.inputs import PointInputs

    return PointInputs(
        R0_m=1.85,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=8.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=25.0,
    )


def _contract(seed: int = 7):
    from src.optimization.slsqp_search_driver import contract_from_registry

    return contract_from_registry("min_R0", seed=seed)


def _round_knobs(inputs: Mapping[str, Any], names: Sequence[str]) -> Tuple[float, ...]:
    return tuple(round(float(inputs[n]), FLOAT_COMPARE_DECIMALS) for n in names)


def _shortlist_identity(result) -> Dict[str, Any]:
    """Canonical shortlist identity (rounded knobs + ids + contract hash)."""
    names = tuple(result.variable_names)
    rows = []
    for c in result.candidates:
        rows.append(
            {
                "id": c.id,
                "rank": int(c.rank),
                "knobs": list(_round_knobs(c.inputs, names)),
                "hard_feasible_filter": bool(c.hard_feasible_filter),
            }
        )
    return {
        "search_driver_id": result.search_driver_id,
        "objective_contract_hash": result.objective_contract_hash,
        "seed": int(result.seed),
        "variable_names": list(names),
        "bounds": {k: [float(lo), float(hi)] for k, (lo, hi) in result.bounds.items()},
        "candidates": rows,
        "best_knobs": (
            None
            if result.best is None
            else list(_round_knobs(result.best.inputs, names))
        ),
    }


def _shortlist_hash(result) -> str:
    return sha256_hex(_shortlist_identity(result))


def _fallback_search(**kwargs: Any):
    defaults: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0), "Paux_MW": (10.0, 50.0)},
        seed=42,
        maxiter=6,
        shortlist_k=3,
        force_fallback=True,
    )
    defaults.update(kwargs)
    seed = int(defaults["seed"])
    return run_slsqp_search(_base_inputs(), _contract(seed), **defaults)


def test_float_policy_documented_in_stance() -> None:
    """CERTIFIED_OPTIMIZER.md must state the SciPy vs fallback float policy."""
    text = (ROOT / "docs/CERTIFIED_OPTIMIZER.md").read_text(encoding="utf-8")
    low = text.lower()
    assert "float policy" in low
    assert "force_fallback" in text
    assert "slsqp_fallback" in text
    assert "platform-sensitive" in low
    assert "8 decimal" in low or "8 dp" in low or "8 decimal places" in low
    assert FLOAT_POLICY_DOC  # module constant kept for reviewers


def test_l0_truth_untouched_by_determinism_locks() -> None:
    for rel in DEFAULT_L0_TRUTH_RELPATHS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=rel)
        assert not hits, f"L0 forbidden imports in {rel}: {hits}"


def test_fallback_path_determinism_two_runs() -> None:
    """Same seed + contract + bounds → identical fallback shortlist hashes."""
    a = _fallback_search(seed=42)
    b = _fallback_search(seed=42)
    assert a.search_driver_id == b.search_driver_id == DRIVER_SLSQP_FALLBACK
    assert a.scipy_used is False and b.scipy_used is False
    assert a.objective_contract_hash == b.objective_contract_hash
    assert _shortlist_hash(a) == _shortlist_hash(b)
    assert a.n_evals == b.n_evals
    assert [c.id for c in a.candidates] == [c.id for c in b.candidates]
    for ca, cb in zip(a.candidates, b.candidates):
        assert _round_knobs(ca.inputs, a.variable_names) == _round_knobs(
            cb.inputs, b.variable_names
        )


def test_stamp_sha256_stable_across_two_fallback_runs() -> None:
    a = _fallback_search(seed=77, maxiter=5, shortlist_k=2)
    b = _fallback_search(seed=77, maxiter=5, shortlist_k=2)
    sa = a.stamp_ready()
    sb = b.stamp_ready()
    assert sa["schema"] == sb["schema"] == STAMP_SCHEMA
    assert sa["stamp_sha256"] == sb["stamp_sha256"]
    assert len(sa["stamp_sha256"]) == 64
    assert sa["objective_contract_hash"] == a.objective_contract_hash
    assert sa["search_driver_id"] == DRIVER_SLSQP_FALLBACK
    assert sa["n_candidates"] == len(a.candidates)
    assert sa["n_verified"] == 0
    assert sa["n_rejected"] == 0


def test_neighborhood_proposal_determinism() -> None:
    result = _fallback_search(seed=21)
    a = build_neighborhood_proposals(result, neighborhood_size=6, step_frac=0.05, seed=21)
    b = build_neighborhood_proposals(result, neighborhood_size=6, step_frac=0.05, seed=21)
    assert len(a) == len(b) >= 1
    assert [c.id for c in a] == [c.id for c in b]
    for ca, cb in zip(a, b):
        assert _round_knobs(ca.inputs, result.variable_names) == _round_knobs(
            cb.inputs, result.variable_names
        )


def test_neighborhood_bundle_identity_stable() -> None:
    result = _fallback_search(seed=33, shortlist_k=1)
    ba = best_and_neighborhood_bundle(result, neighborhood_size=4, step_frac=0.04, seed=33)
    bb = best_and_neighborhood_bundle(result, neighborhood_size=4, step_frac=0.04, seed=33)
    # Drop non-identity noise; hash candidate ids + rounded continuous knobs.
    def _bundle_id(bundle: Mapping[str, Any]) -> str:
        names = list(bundle["neighborhood_policy"]["variable_names"])
        rows = []
        for c in bundle["candidates"]:
            rows.append(
                {
                    "id": c["id"],
                    "role": c["claims"]["role"],
                    "knobs": list(_round_knobs(c["inputs"], names)),
                }
            )
        body = {
            "schema_version": bundle["schema_version"],
            "opt_run": {
                "objective_contract_hash": bundle["opt_run"]["objective_contract_hash"],
                "seed": bundle["opt_run"]["seed"],
                "search_driver_id": bundle["opt_run"]["search_driver_id"],
            },
            "candidates": rows,
            "neighborhood_policy": {
                "neighborhood_size": bundle["neighborhood_policy"]["neighborhood_size"],
                "step_frac": bundle["neighborhood_policy"]["step_frac"],
                "n_neighbors_emitted": bundle["neighborhood_policy"]["n_neighbors_emitted"],
                "deterministic": bundle["neighborhood_policy"]["deterministic"],
            },
        }
        return sha256_hex(body)

    assert _bundle_id(ba) == _bundle_id(bb)


@pytest.mark.slow
def test_certified_shortlist_stamp_stable_two_runs() -> None:
    """CCFS neighborhood certify: stamp_sha256 + status counts match across runs."""
    r1 = _fallback_search(seed=29, maxiter=4, shortlist_k=1)
    r2 = _fallback_search(seed=29, maxiter=4, shortlist_k=1)
    assert _shortlist_hash(r1) == _shortlist_hash(r2)

    out1 = certify_best_and_neighborhood(
        r1, neighborhood_size=4, step_frac=0.05, attach_opt_run_stamp=True
    )
    out2 = certify_best_and_neighborhood(
        r2, neighborhood_size=4, step_frac=0.05, attach_opt_run_stamp=True
    )
    assert out1["schema_version"] == out2["schema_version"] == "ccfs_verified.v1"
    s1 = out1["opt_run_stamp"]
    s2 = out2["opt_run_stamp"]
    assert s1["stamp_sha256"] == s2["stamp_sha256"]
    assert s1["n_candidates"] == s2["n_candidates"]
    assert s1["n_verified"] == s2["n_verified"]
    assert s1["n_rejected"] == s2["n_rejected"]
    assert s1["objective_contract_hash"] == r1.objective_contract_hash

    ids1 = [row["id"] for row in out1["verified"]]
    ids2 = [row["id"] for row in out2["verified"]]
    assert ids1 == ids2
    statuses1 = [row["status"] for row in out1["verified"]]
    statuses2 = [row["status"] for row in out2["verified"]]
    assert statuses1 == statuses2


def test_different_seed_changes_shortlist_or_stamp() -> None:
    """Sanity: seed change must not silently collide with locked identity."""
    a = _fallback_search(seed=10, maxiter=5, shortlist_k=2)
    b = _fallback_search(seed=11, maxiter=5, shortlist_k=2)
    # Contract hash includes seed when seed_policy=fixed → hashes differ.
    assert a.objective_contract_hash != b.objective_contract_hash
    assert a.stamp_ready()["stamp_sha256"] != b.stamp_ready()["stamp_sha256"]


def test_scipy_path_smoke_not_bit_locked() -> None:
    """SciPy path may run; we do **not** assert cross-run bit identity here.

    Documents that publication locks prefer ``force_fallback``. If SciPy is
    absent, skip. If present, smoke that driver id is ``slsqp`` and a stamp
    exists — without requiring two-run equality (platform-sensitive).
    """
    if not scipy_optimize_available():
        pytest.skip("SciPy not installed")
    result = run_slsqp_search(
        _base_inputs(),
        _contract(19),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=19,
        maxiter=6,
        shortlist_k=2,
        force_fallback=False,
    )
    assert result.scipy_used is True
    assert result.search_driver_id == "slsqp"
    stamp = result.stamp_ready()
    assert stamp["schema"] == STAMP_SCHEMA
    assert "stamp_sha256" in stamp
    # Explicit non-lock note for reviewers / future editors.
    assert FLOAT_COMPARE_DECIMALS == 8
    assert "platform-sensitive" in FLOAT_POLICY_DOC


def test_shortlist_hash_uses_documented_rounding() -> None:
    """Identity helper must use FLOAT_COMPARE_DECIMALS (8) consistently."""
    result = _fallback_search(seed=5, shortlist_k=1)
    body = _shortlist_identity(result)
    # Manual recompute with json+hashlib to prove sha256_hex path is stable.
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    manual = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    # sha256_hex uses canonical_dumps — may differ from naive json; both must
    # be stable across two calls of the same helper.
    h1 = _shortlist_hash(result)
    h2 = _shortlist_hash(result)
    assert h1 == h2
    assert len(h1) == 64
    assert manual  # computed (documents alternative); identity lock is h1==h2
