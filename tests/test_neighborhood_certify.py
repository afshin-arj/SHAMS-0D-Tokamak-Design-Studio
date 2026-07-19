"""Lock tests — best + neighborhood CCFS re-certify (Certified Optimizer 2.2).

Reported best and a seeded local neighborhood always go through CCFS.
REJECTED rows carry no_solution_atlas.v1; opt_run_stamp.v1 is attached.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from src.optimization.l0_opt_guards import (
    DEFAULT_L0_TRUTH_RELPATHS,
    collect_forbidden_imports,
)
from src.optimization.opt_run_stamp import SCHEMA as STAMP_SCHEMA
from src.optimization.slsqp_search_driver import (
    DEFAULT_NEIGHBORHOOD_SIZE,
    NEIGHBORHOOD_CERTIFY_SCHEMA,
    best_and_neighborhood_bundle,
    build_neighborhood_proposals,
    certify_best_and_neighborhood,
    run_slsqp_search,
)

ROOT = Path(__file__).resolve().parents[1]


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


def _search(**kwargs: Any):
    defaults: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=13,
        maxiter=5,
        shortlist_k=2,
        force_fallback=True,
    )
    defaults.update(kwargs)
    seed = int(defaults["seed"])
    return run_slsqp_search(_base_inputs(), _contract(seed), **defaults)


def test_l0_truth_still_free_of_opt_imports() -> None:
    for rel in DEFAULT_L0_TRUTH_RELPATHS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=rel)
        assert not hits, f"L0 forbidden imports in {rel}: {hits}"


def test_neighborhood_proposals_deterministic_and_bounded() -> None:
    result = _search(seed=21)
    assert result.best is not None
    a = build_neighborhood_proposals(result, neighborhood_size=6, step_frac=0.05, seed=21)
    b = build_neighborhood_proposals(result, neighborhood_size=6, step_frac=0.05, seed=21)
    assert len(a) == len(b) >= 1
    assert [c.id for c in a] == [c.id for c in b]
    for n in result.variable_names:
        lo, hi = result.bounds[n]
        for cand in a:
            v = float(cand.inputs[n])
            assert lo - 1e-9 <= v <= hi + 1e-9
            # Neighbors must differ from best on at least one continuous knob.
    best_key = tuple(
        round(float(result.best.inputs[n]), 8) for n in result.variable_names
    )
    for cand in a:
        key = tuple(round(float(cand.inputs[n]), 8) for n in result.variable_names)
        assert key != best_key


def test_best_and_neighborhood_bundle_roles() -> None:
    result = _search(seed=17)
    bundle = best_and_neighborhood_bundle(result, neighborhood_size=4, step_frac=0.04)
    assert bundle["schema_version"] == "ccfs_bundle.v1"
    assert bundle["candidates"][0]["id"] == result.best.id
    assert len(bundle["candidates"]) == 1 + int(
        bundle["neighborhood_policy"]["n_neighbors_emitted"]
    )
    assert bundle["candidates"][0]["claims"]["role"] == "best"
    assert bundle["candidates"][0]["claims"]["status"] == "PROPOSED"
    for c in bundle["candidates"][1:]:
        assert c["claims"]["role"] == "neighborhood"
        assert c["claims"]["status"] == "PROPOSED"
    pol = bundle["neighborhood_policy"]
    assert pol["schema"] == NEIGHBORHOOD_CERTIFY_SCHEMA
    assert pol["deterministic"] is True
    assert pol["neighborhood_size"] == 4
    assert all(c["claims"]["status"] == "PROPOSED" for c in bundle["candidates"])


@pytest.mark.slow
def test_certify_best_and_neighborhood_ccfs_stamp_atlas() -> None:
    result = _search(seed=29, maxiter=4, shortlist_k=1)
    out = certify_best_and_neighborhood(
        result,
        neighborhood_size=4,
        step_frac=0.05,
        attach_opt_run_stamp=True,
    )
    assert out["schema_version"] == "ccfs_verified.v1"
    assert out["firewall"]["claims_never_set_status"] is True
    assert "opt_run_stamp" in out
    stamp = out["opt_run_stamp"]
    assert stamp["schema"] == STAMP_SCHEMA
    assert stamp["objective_contract_hash"] == result.objective_contract_hash
    assert stamp["search_driver_id"] == result.search_driver_id
    assert stamp["n_candidates"] == out["n_candidates"]
    assert stamp["n_verified"] == out["n_status_verified"]
    assert stamp["n_rejected"] == out["n_status_rejected"]

    meta = out["neighborhood_certify"]
    assert meta["schema"] == NEIGHBORHOOD_CERTIFY_SCHEMA
    assert meta["best_id"] == result.best.id
    assert meta["n_certified"] == out["n_candidates"]
    assert meta["n_neighbors"] >= 1
    assert meta["opt_run_stamp_attached"] is True
    assert meta["certifier"] == "CCFS"
    assert meta["best_status"] in {"VERIFIED", "REJECTED"}

    rows = out["verified"]
    assert any(r["id"] == result.best.id for r in rows)
    assert len(rows) == 1 + meta["n_neighbors"]
    for row in rows:
        assert row["claims_ignored"] is True
        assert row["status"] in {"VERIFIED", "REJECTED"}
        # Claims never become VERIFIED by themselves.
        assert row.get("claims", {}).get("status") == "PROPOSED"
        if row["status"] == "REJECTED":
            atlas = row["no_solution_atlas"]
            assert atlas["schema"] == "no_solution_atlas.v1"
            assert "verdict" in atlas
            assert "dominant_mechanism" in atlas
    assert meta["atlas_on_all_rejects"] is True


def test_default_neighborhood_size_is_sane() -> None:
    assert DEFAULT_NEIGHBORHOOD_SIZE == 8
    result = _search(seed=3)
    nbrs = build_neighborhood_proposals(result)
    assert 1 <= len(nbrs) <= DEFAULT_NEIGHBORHOOD_SIZE


def test_opt_lab_hook_mentions_neighborhood_certify() -> None:
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_SLSQP_HOOK_NOTE,
        opt_lab_user_facing_texts,
    )

    blob = " ".join(opt_lab_user_facing_texts()).lower()
    assert "neighborhood" in OPT_LAB_SLSQP_HOOK_NOTE.lower()
    assert "ccfs" in OPT_LAB_SLSQP_HOOK_NOTE.lower()
    assert "true minimum" not in OPT_LAB_SLSQP_HOOK_NOTE.lower()
    assert "neighborhood" in blob
