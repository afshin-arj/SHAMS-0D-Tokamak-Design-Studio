"""Lock tests — SLSQP/SQP SearchDriver (Certified Optimizer Phase 2.1).

Propose-only continuous search outside L0. SciPy optional with pure-Python
fallback. Hard constraints are SHAMS-evaluated filters — no soft negotiation.
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
    DRIVER_SLSQP,
    DRIVER_SLSQP_FALLBACK,
    KNOWN_DRIVER_IDS,
    SCHEMA as STAMP_SCHEMA,
)
from src.optimization.slsqp_search_driver import (
    SCHEMA,
    lightly_certify_shortlist,
    run_slsqp_search,
    scipy_optimize_available,
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


def test_driver_ids_registered_on_stamp() -> None:
    assert DRIVER_SLSQP == "slsqp"
    assert DRIVER_SLSQP_FALLBACK == "slsqp_fallback"
    assert DRIVER_SLSQP in KNOWN_DRIVER_IDS
    assert DRIVER_SLSQP_FALLBACK in KNOWN_DRIVER_IDS


def test_driver_module_does_not_import_l0_packages_into_hot_ion() -> None:
    """SLSQP module is outside L0; L0 truth files must stay free of opt imports."""
    for rel in DEFAULT_L0_TRUTH_RELPATHS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=rel)
        assert not hits, f"L0 forbidden imports in {rel}: {hits}"


def test_driver_source_has_no_evaluator_hot_ion_import_edge() -> None:
    """Driver may call Evaluator; must not import hot_ion directly."""
    src = (ROOT / "src/optimization/slsqp_search_driver.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = str(node.module or "")
            assert "hot_ion" not in mod, mod
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "hot_ion" not in str(alias.name)


def test_force_fallback_path_runs_and_stamps() -> None:
    result = run_slsqp_search(
        _base_inputs(),
        _contract(seed=11),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=11,
        maxiter=6,
        shortlist_k=3,
        force_fallback=True,
    )
    assert result.schema == SCHEMA == "slsqp_search_result.v1"
    assert result.search_driver_id == DRIVER_SLSQP_FALLBACK
    assert result.scipy_used is False
    assert result.n_evals >= 1
    assert len(result.candidates) >= 1
    assert result.best is not None
    assert result.candidates[0].to_dict()["certification"] == "propose_only"
    assert "Ip_MA" in result.best.inputs
    stamp = result.stamp_ready()
    assert stamp["schema"] == STAMP_SCHEMA
    assert stamp["search_driver_id"] == DRIVER_SLSQP_FALLBACK
    assert stamp["objective_contract_hash"] == result.objective_contract_hash
    assert stamp["n_candidates"] == len(result.candidates)
    assert stamp["n_verified"] == 0
    assert "stamp_sha256" in stamp


def test_fallback_determinism_same_seed() -> None:
    kwargs: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.5, 9.5), "fG": (0.7, 0.95)},
        seed=42,
        maxiter=5,
        shortlist_k=2,
        force_fallback=True,
    )
    a = run_slsqp_search(_base_inputs(), _contract(42), **kwargs)
    b = run_slsqp_search(_base_inputs(), _contract(42), **kwargs)
    assert a.objective_contract_hash == b.objective_contract_hash
    assert a.search_driver_id == b.search_driver_id == DRIVER_SLSQP_FALLBACK
    xa = tuple(round(float(a.best.inputs[k]), 8) for k in sorted(a.variable_names))
    xb = tuple(round(float(b.best.inputs[k]), 8) for k in sorted(b.variable_names))
    assert xa == xb
    assert [c.id for c in a.candidates] == [c.id for c in b.candidates]


def test_ccfs_bundle_hook_is_propose_only() -> None:
    result = run_slsqp_search(
        _base_inputs(),
        _contract(3),
        variables={"Ip_MA": (7.0, 9.0)},
        seed=3,
        maxiter=4,
        shortlist_k=2,
        force_fallback=True,
    )
    bundle = result.to_ccfs_bundle()
    assert bundle["schema_version"] == "ccfs_bundle.v1"
    assert bundle["candidates"]
    assert bundle["opt_run"]["search_driver_id"] == DRIVER_SLSQP_FALLBACK
    for c in bundle["candidates"]:
        assert c["claims"]["status"] == "PROPOSED"
        assert "inputs" in c


@pytest.mark.slow
def test_light_ccfs_on_shortlist_does_not_trust_claims() -> None:
    """Optional light certify: claims never set VERIFIED."""
    result = run_slsqp_search(
        _base_inputs(),
        _contract(5),
        variables={"Ip_MA": (7.0, 9.0), "fG": (0.7, 0.95)},
        seed=5,
        maxiter=4,
        shortlist_k=1,
        force_fallback=True,
    )
    verified = lightly_certify_shortlist(result, attach_opt_run_stamp=True)
    assert verified["schema_version"] == "ccfs_verified.v1"
    assert verified["firewall"]["claims_never_set_status"] is True
    row = verified["verified"][0]
    assert row["claims_ignored"] is True
    assert row["status"] in {"VERIFIED", "REJECTED"}
    assert "opt_run_stamp" in verified


def test_scipy_path_when_available() -> None:
    if not scipy_optimize_available():
        pytest.skip("SciPy not installed")
    result = run_slsqp_search(
        _base_inputs(),
        _contract(19),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=19,
        maxiter=8,
        shortlist_k=3,
        force_fallback=False,
    )
    assert result.search_driver_id == DRIVER_SLSQP
    assert result.scipy_used is True
    assert result.best is not None
    stamp = result.stamp_ready()
    assert stamp["search_driver_id"] == DRIVER_SLSQP


def test_hard_infeasible_not_softened_in_archive_scores() -> None:
    """Infeasible proposals carry barrier penalty — no soft negotiation."""
    from src.optimization.slsqp_search_driver import _HARD_INFEASIBLE_PENALTY

    result = run_slsqp_search(
        _base_inputs(),
        _contract(8),
        # Extreme fG band often hits Greenwald / density hard limits.
        variables={"fG": (1.05, 1.25), "Ip_MA": (10.0, 14.0)},
        seed=8,
        maxiter=5,
        shortlist_k=5,
        force_fallback=True,
        prefer_feasible=False,
    )
    # At least the API preserves the filter flag; barrier used when infeasible.
    for c in result.candidates:
        if not c.hard_feasible_filter:
            assert c.minimize_score >= _HARD_INFEASIBLE_PENALTY * 0.5


def test_opt_lab_exposes_slsqp_driver_ids() -> None:
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_SLSQP_HOOK_NOTE,
        opt_lab_slsqp_driver_ids,
        opt_lab_user_facing_texts,
    )

    assert opt_lab_slsqp_driver_ids() == ("slsqp", "slsqp_fallback")
    blob = " ".join(opt_lab_user_facing_texts()).lower()
    assert "slsqp" in blob or "propose" in blob
    assert "ccfs" in OPT_LAB_SLSQP_HOOK_NOTE.lower()
    assert "true minimum" not in OPT_LAB_SLSQP_HOOK_NOTE.lower()
    assert "true global" not in OPT_LAB_SLSQP_HOOK_NOTE.lower()


def test_panel_renders_slsqp_hook_note() -> None:
    panel = (ROOT / "ui_nicegui/components/opt_lab_entry_panel.py").read_text(
        encoding="utf-8"
    )
    assert "OPT_LAB_SLSQP_HOOK_NOTE" in panel
