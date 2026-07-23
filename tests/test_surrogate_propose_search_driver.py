"""Lock tests — Surrogate propose-only SearchDriver (Certified Optimizer Phase 4.1).

Surrogate may rank/propose; every shortlist point re-evals frozen L0 / CCFS.
Surrogate scores never set VERIFIED.
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
    DRIVER_SURROGATE_PROPOSE,
    KNOWN_DRIVER_IDS,
    SCHEMA as STAMP_SCHEMA,
)
from src.optimization.surrogate_propose_search_driver import (
    SCHEMA,
    lightly_certify_shortlist,
    run_surrogate_propose_search,
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
    from src.optimization.surrogate_propose_search_driver import contract_from_registry

    return contract_from_registry("min_R0", seed=seed)


def test_driver_id_registered_on_stamp() -> None:
    assert DRIVER_SURROGATE_PROPOSE == "surrogate_propose"
    assert DRIVER_SURROGATE_PROPOSE in KNOWN_DRIVER_IDS


def test_driver_module_does_not_pollute_l0() -> None:
    for rel in DEFAULT_L0_TRUTH_RELPATHS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = collect_forbidden_imports(text, filename=rel)
        assert not hits, f"L0 forbidden imports in {rel}: {hits}"


def test_driver_source_has_no_hot_ion_import() -> None:
    src = (ROOT / "src/optimization/surrogate_propose_search_driver.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = str(node.module or "")
            assert "hot_ion" not in mod, mod
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "hot_ion" not in str(alias.name)


def test_surrogate_propose_runs_stamps_and_is_propose_only() -> None:
    result = run_surrogate_propose_search(
        _base_inputs(),
        _contract(seed=11),
        variables={"Ip_MA": (6.0, 10.0), "fG": (0.6, 1.0)},
        seed=11,
        n_train=24,
        n_pool=120,
        shortlist_k=3,
    )
    assert result.schema == SCHEMA == "surrogate_propose_search_result.v1"
    assert result.search_driver_id == DRIVER_SURROGATE_PROPOSE
    assert result.n_train >= 8
    assert result.n_evals >= 1
    assert len(result.candidates) >= 1
    assert result.best is not None
    d0 = result.candidates[0].to_dict()
    assert d0["certification"] == "propose_only"
    assert d0["surrogate_uncertified"] is True
    assert "Ip_MA" in result.best.inputs
    stamp = result.stamp_ready()
    assert stamp["schema"] == STAMP_SCHEMA
    assert stamp["search_driver_id"] == DRIVER_SURROGATE_PROPOSE
    assert stamp["objective_contract_hash"] == result.objective_contract_hash
    assert stamp["n_candidates"] == len(result.candidates)
    assert stamp["n_verified"] == 0
    assert "stamp_sha256" in stamp
    assert result.to_dict()["surrogate_never_certifies"] is True
    assert result.surrogate_meta is not None
    assert result.surrogate_meta["surrogate_never_sets_verified"] is True


def test_ccfs_bundle_claims_stay_proposed_not_verified() -> None:
    result = run_surrogate_propose_search(
        _base_inputs(),
        _contract(3),
        variables={"Ip_MA": (7.0, 9.0)},
        seed=3,
        n_train=20,
        n_pool=80,
        shortlist_k=2,
    )
    bundle = result.to_ccfs_bundle()
    assert bundle["schema_version"] == "ccfs_bundle.v1"
    assert bundle["candidates"]
    assert bundle["opt_run"]["search_driver_id"] == DRIVER_SURROGATE_PROPOSE
    for c in bundle["candidates"]:
        claims = c["claims"]
        assert claims["status"] == "PROPOSED"
        assert claims.get("surrogate_uncertified") is True
        assert claims["status"] != "VERIFIED"
        assert "inputs" in c


def test_same_seed_determinism_shortlist_ids() -> None:
    kwargs: Dict[str, Any] = dict(
        variables={"Ip_MA": (6.5, 9.5), "fG": (0.7, 0.95)},
        seed=42,
        n_train=20,
        n_pool=100,
        shortlist_k=2,
    )
    a = run_surrogate_propose_search(_base_inputs(), _contract(42), **kwargs)
    b = run_surrogate_propose_search(_base_inputs(), _contract(42), **kwargs)
    assert a.objective_contract_hash == b.objective_contract_hash
    assert a.search_driver_id == b.search_driver_id == DRIVER_SURROGATE_PROPOSE
    assert [c.id for c in a.candidates] == [c.id for c in b.candidates]
    xa = tuple(round(float(a.best.inputs[k]), 8) for k in sorted(a.variable_names))
    xb = tuple(round(float(b.best.inputs[k]), 8) for k in sorted(b.variable_names))
    assert xa == xb
    assert a.stamp_ready()["stamp_sha256"] == b.stamp_ready()["stamp_sha256"]


@pytest.mark.slow
def test_light_ccfs_never_trusts_surrogate_claims() -> None:
    """CCFS re-evals shortlist; claims cannot set VERIFIED from surrogate scores."""
    result = run_surrogate_propose_search(
        _base_inputs(),
        _contract(5),
        variables={"Ip_MA": (7.0, 9.0), "fG": (0.7, 0.95)},
        seed=5,
        n_train=20,
        n_pool=80,
        shortlist_k=1,
    )
    # Poison claims would still be ignored — bundle already marks PROPOSED.
    verified = lightly_certify_shortlist(result, attach_opt_run_stamp=True)
    assert verified["schema_version"] == "ccfs_verified.v1"
    assert verified["firewall"]["claims_never_set_status"] is True
    row = verified["verified"][0]
    assert row["claims_ignored"] is True
    assert row["status"] in {"VERIFIED", "REJECTED"}
    # Surrogate score must not appear as the authority for status.
    assert "opt_run_stamp" in verified
    stamp = verified["opt_run_stamp"]
    assert stamp["search_driver_id"] == DRIVER_SURROGATE_PROPOSE


def test_surrogate_score_alone_cannot_be_verified_status() -> None:
    """Guard: driver never emits certification=VERIFIED from surrogate path."""
    result = run_surrogate_propose_search(
        _base_inputs(),
        _contract(9),
        variables={"Ip_MA": (6.0, 10.0)},
        seed=9,
        n_train=16,
        n_pool=60,
        shortlist_k=2,
    )
    for c in result.candidates:
        d = c.to_dict()
        assert d["certification"] == "propose_only"
        assert d["certification"] != "VERIFIED"
    blob = str(result.to_dict())
    assert "surrogate_never_certifies" in blob


def test_opt_lab_surrogate_hook_honesty() -> None:
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_SURROGATE_DRIVER_IDS,
        OPT_LAB_SURROGATE_HOOK_NOTE,
        opt_lab_surrogate_driver_ids,
        opt_lab_user_facing_texts,
    )

    assert OPT_LAB_SURROGATE_DRIVER_IDS == ("surrogate_propose",)
    assert opt_lab_surrogate_driver_ids() == OPT_LAB_SURROGATE_DRIVER_IDS
    note = OPT_LAB_SURROGATE_HOOK_NOTE.lower()
    assert "propose" in note
    assert "ccfs" in note
    assert "verified" in note
    assert "true minimum" not in note
    assert "true global" not in note
    texts = opt_lab_user_facing_texts()
    assert OPT_LAB_SURROGATE_HOOK_NOTE in texts


def test_panel_renders_surrogate_hook_note() -> None:
    panel = (
        ROOT / "ui_nicegui/components/opt_lab_entry_panel.py"
    ).read_text(encoding="utf-8")
    assert "OPT_LAB_SURROGATE_HOOK_NOTE" in panel
