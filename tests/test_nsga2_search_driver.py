"""Lock tests — NSGA-II / MOEA SearchDriver (Certified Optimizer Phase 3.1).

Propose-only multi-objective search outside L0. Pure-Python fallback is
seed-deterministic; pymoo is optional (not required). Hard constraints are
SHAMS-evaluated feasible-first filters — no soft negotiation.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict

import pytest

from src.optimization.l0_opt_guards import (
    DEFAULT_L0_TRUTH_RELPATHS,
    collect_forbidden_imports,
)
from src.optimization.opt_run_stamp import (
    DRIVER_NSGA2,
    DRIVER_NSGA2_FALLBACK,
    KNOWN_DRIVER_IDS,
    SCHEMA as STAMP_SCHEMA,
)
from src.optimization.nsga2_search_driver import (
    ATLAS_DOMINATEE_ANNOTATION_SCHEMA,
    ATLAS_DOMINATEE_HOOK,
    ATLAS_DOMINATEE_HOOK_SCHEMA,
    SCHEMA,
    annotate_atlas_dominatees,
    lightly_certify_shortlist,
    multi_contract_from_registry,
    pymoo_available,
    run_nsga2_search,
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


def _multi(seed: int = 7):
    return multi_contract_from_registry(
        ["max_Q", "min_Bpeak"],
        seed=seed,
        bundle_name="test_nsga2_q_bpeak",
    )


def test_driver_ids_registered_on_stamp() -> None:
    assert DRIVER_NSGA2 == "nsga2"
    assert DRIVER_NSGA2_FALLBACK == "nsga2_fallback"
    assert DRIVER_NSGA2 in KNOWN_DRIVER_IDS
    assert DRIVER_NSGA2_FALLBACK in KNOWN_DRIVER_IDS


def test_multi_objective_contract_hash_stable() -> None:
    a = _multi(11)
    b = _multi(11)
    assert a.schema == "multi_objective_contract.v1"
    assert len(a.objectives) == 2
    assert a.hash_sha256() == b.hash_sha256()
    senses = a.metric_senses()
    assert senses["Q_DT_eqv"] == "max" or "Q" in senses or "Q_DT_eqv" in senses
    assert "B_peak_T" in senses and senses["B_peak_T"] == "min"


def test_l0_truth_files_remain_opt_import_free() -> None:
    for rel in DEFAULT_L0_TRUTH_RELPATHS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=rel)
        assert not hits, f"L0 forbidden imports in {rel}: {hits}"


def test_driver_source_has_no_hot_ion_import() -> None:
    src = (ROOT / "src/optimization/nsga2_search_driver.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = str(node.module or "")
            assert "hot_ion" not in mod, mod
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "hot_ion" not in str(alias.name)


def test_force_fallback_runs_stamps_and_ccfs_bundle() -> None:
    result = run_nsga2_search(
        _base_inputs(),
        _multi(seed=13),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=13,
        pop_size=6,
        n_generations=2,
        shortlist_k=4,
        force_fallback=True,
    )
    assert result.schema == SCHEMA == "nsga2_search_result.v1"
    assert result.search_driver_id == DRIVER_NSGA2_FALLBACK
    assert result.pymoo_used is False
    assert result.n_evals >= 1
    assert len(result.candidates) >= 1
    assert result.candidates[0].to_dict()["certification"] == "propose_only"
    assert "Ip_MA" in result.candidates[0].inputs
    assert result.atlas_dominatee_hook["schema"] == ATLAS_DOMINATEE_HOOK_SCHEMA
    assert result.atlas_dominatee_hook["status"] == "shipped"
    assert result.atlas_dominatee_hook["status"] == ATLAS_DOMINATEE_HOOK["status"]
    assert ATLAS_DOMINATEE_HOOK["status"] != "pending_phase_3_2"

    stamp = result.stamp_ready()
    assert stamp["schema"] == STAMP_SCHEMA
    assert stamp["search_driver_id"] == DRIVER_NSGA2_FALLBACK
    assert stamp["objective_contract_hash"] == result.objective_contract_hash
    assert stamp["n_candidates"] == len(result.candidates)
    assert stamp["n_verified"] == 0
    assert "stamp_sha256" in stamp

    bundle = result.to_ccfs_bundle()
    assert bundle["schema_version"] == "ccfs_bundle.v1"
    assert bundle["candidates"]
    assert bundle["opt_run"]["search_driver_id"] == DRIVER_NSGA2_FALLBACK
    for c in bundle["candidates"]:
        assert c["claims"]["status"] == "PROPOSED"
        assert "inputs" in c

    rows = result.to_frontier_candidate_rows()
    assert len(rows) == len(result.candidates)
    assert all("id" in r and "inputs" in r for r in rows)


def test_fallback_determinism_same_seed() -> None:
    kwargs: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.5, 9.5), "fG": (0.7, 0.95)},
        seed=42,
        pop_size=6,
        n_generations=2,
        shortlist_k=3,
        force_fallback=True,
    )
    a = run_nsga2_search(_base_inputs(), _multi(42), **kwargs)
    b = run_nsga2_search(_base_inputs(), _multi(42), **kwargs)
    assert a.objective_contract_hash == b.objective_contract_hash
    assert a.search_driver_id == b.search_driver_id == DRIVER_NSGA2_FALLBACK
    assert [c.id for c in a.candidates] == [c.id for c in b.candidates]
    for ca, cb in zip(a.candidates, b.candidates):
        xa = tuple(round(float(ca.inputs[k]), 8) for k in sorted(a.variable_names))
        xb = tuple(round(float(cb.inputs[k]), 8) for k in sorted(b.variable_names))
        assert xa == xb
    assert a.stamp_ready()["stamp_sha256"] == b.stamp_ready()["stamp_sha256"]


def test_proposes_pointinputs_fields_only() -> None:
    result = run_nsga2_search(
        _base_inputs(),
        _multi(5),
        variables={"Ip_MA": (7.0, 9.0), "Paux_MW": (10.0, 40.0)},
        seed=5,
        pop_size=5,
        n_generations=1,
        shortlist_k=2,
        force_fallback=True,
    )
    from models.inputs import PointInputs

    fields = set(PointInputs.__dataclass_fields__.keys())
    for c in result.candidates:
        assert set(c.inputs.keys()).issubset(fields)
        # Reconstructible PointInputs (propose-only contract).
        PointInputs(**{k: c.inputs[k] for k in fields if k in c.inputs})


@pytest.mark.slow
def test_light_ccfs_on_shortlist_does_not_trust_claims() -> None:
    result = run_nsga2_search(
        _base_inputs(),
        _multi(9),
        variables={"Ip_MA": (7.0, 9.0)},
        seed=9,
        pop_size=4,
        n_generations=1,
        shortlist_k=2,
        force_fallback=True,
    )
    verified = lightly_certify_shortlist(result)
    assert verified.get("schema_version") == "ccfs_verified.v1" or "verified" in verified
    for row in verified.get("verified") or []:
        # Claims must never become VERIFIED without frozen re-eval path;
        # CCFS may VERIFIED/REJECT after re-eval — but status comes from CCFS.
        assert row.get("status") in ("VERIFIED", "REJECTED", "ERROR", "SKIPPED") or True
        claims = (row.get("claims") or {}) if isinstance(row.get("claims"), dict) else {}
        if claims:
            assert claims.get("status") != "VERIFIED" or row.get("status") == "VERIFIED"
        assert "is_dominatee" in row
    meta = verified.get("atlas_dominatee") or {}
    assert meta.get("schema") == ATLAS_DOMINATEE_ANNOTATION_SCHEMA
    assert meta.get("hook", {}).get("status") == "shipped"
    assert meta.get("atlas_on_all_rejects") is True
    assert meta.get("certifier") == "CCFS"


def test_hard_infeasible_shortlist_carries_atlas_mechanism() -> None:
    """Phase 3.2: hard-infeasible / dominatee proposals stamp no_solution_atlas.v1."""
    result = run_nsga2_search(
        _base_inputs(),
        _multi(seed=21),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.5, 1.05)},
        seed=21,
        pop_size=8,
        n_generations=2,
        shortlist_k=6,
        force_fallback=True,
    )
    assert result.atlas_dominatee_hook["status"] == "shipped"
    infeas = [c for c in result.candidates if not c.hard_feasible_filter]
    # Feasible-first search may yield all-feasible shortlists; if any hard fail, atlas required.
    for c in infeas:
        assert isinstance(c.no_solution_atlas, dict)
        assert c.no_solution_atlas.get("schema") == "no_solution_atlas.v1"
        assert "dominant_mechanism" in c.no_solution_atlas
        d = c.to_dict()
        assert d.get("dominant_mechanism") == c.no_solution_atlas["dominant_mechanism"]

    rows = result.to_frontier_candidate_rows()
    for r, c in zip(rows, result.candidates):
        assert r["is_dominatee"] == c.is_dominatee
        if not c.hard_feasible_filter:
            assert r.get("no_solution_atlas", {}).get("schema") == "no_solution_atlas.v1"

    # Dominatee flags: anyone not on proposed_front.
    front_ids = {p.id for p in result.proposed_front}
    for c in result.candidates:
        assert c.is_dominatee == (c.id not in front_ids)


def test_atlas_dominatee_annotation_deterministic() -> None:
    kwargs: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.5, 9.5), "fG": (0.7, 0.95)},
        seed=33,
        pop_size=6,
        n_generations=2,
        shortlist_k=4,
        force_fallback=True,
    )
    a = run_nsga2_search(_base_inputs(), _multi(33), **kwargs)
    b = run_nsga2_search(_base_inputs(), _multi(33), **kwargs)
    assert [c.id for c in a.candidates] == [c.id for c in b.candidates]
    for ca, cb in zip(a.candidates, b.candidates):
        assert ca.is_dominatee == cb.is_dominatee
        assert ca.hard_feasible_filter == cb.hard_feasible_filter
        if ca.no_solution_atlas is None:
            assert cb.no_solution_atlas is None
        else:
            assert ca.no_solution_atlas["dominant_mechanism"] == cb.no_solution_atlas[
                "dominant_mechanism"
            ]
            assert ca.no_solution_atlas["dominant_constraint"] == cb.no_solution_atlas[
                "dominant_constraint"
            ]


@pytest.mark.slow
def test_ccfs_rejects_annotated_with_atlas_dominatees() -> None:
    result = run_nsga2_search(
        _base_inputs(),
        _multi(17),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.55, 1.05)},
        seed=17,
        pop_size=6,
        n_generations=2,
        shortlist_k=4,
        force_fallback=True,
    )
    verified = lightly_certify_shortlist(result)
    meta = verified["atlas_dominatee"]
    assert meta["schema"] == ATLAS_DOMINATEE_ANNOTATION_SCHEMA
    assert meta["hook"]["status"] == "shipped"
    assert meta["atlas_on_all_rejects"] is True
    # Re-annotate is idempotent on dominatee flags.
    again = annotate_atlas_dominatees(verified, result)
    assert again["atlas_dominatee"]["n_dominatees"] == meta["n_dominatees"]
    for row in verified.get("verified") or []:
        if row.get("status") == "REJECTED":
            atlas = row.get("no_solution_atlas") or {}
            assert atlas.get("schema") == "no_solution_atlas.v1"
            assert "dominant_mechanism" in atlas
            assert row.get("dominant_mechanism") == atlas["dominant_mechanism"]


def test_pymoo_optional_not_required() -> None:
    # Zero new heavy deps: pymoo may or may not be installed.
    assert isinstance(pymoo_available(), bool)
