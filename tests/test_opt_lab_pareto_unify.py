"""Certified Optimizer 3.3 — Opt Lab ↔ Pareto Lab unify + ExtOpt contract bridge.

Locks: shared certified-front viewer schema, honesty phrases (no true minimum /
vNNN), ExtOpt v3 ↔ Opt Lab v1/multi bridge, session handoff, frontier-check
module import, Streamlit/NiceGUI surface presence. L0 untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_VERSION_TAG = re.compile(r"\bv\d{3}\b", re.IGNORECASE)


def test_extopt_v3_bridges_to_multi_objective_contract() -> None:
    from src.optimization.extopt_contract_bridge import (
        EXTOPT_LEGACY_HONESTY,
        EXTOPT_SCHEMA_V3,
        MULTI_SCHEMA,
        build_bridged_extopt_job_contract,
        resolve_opt_lab_contract_from_extopt_payload,
    )
    from src.optimization.objective_contract import MultiObjectiveContract

    wire = build_bridged_extopt_job_contract(
        objectives=["P_e_net_MW", "B_peak_T"],
        senses={"P_e_net_MW": "max", "B_peak_T": "min"},
        seed=7,
    )
    assert wire["schema"] == EXTOPT_SCHEMA_V3
    assert wire["honesty"] == EXTOPT_LEGACY_HONESTY
    assert "Proposed — SHAMS-certified" in wire["honesty"]
    assert wire["opt_lab_contract"]["schema"] == MULTI_SCHEMA
    assert isinstance(wire["opt_lab_contract_hash"], str)
    assert len(wire["opt_lab_contract_hash"]) == 64

    # Orchestrator still accepts the wire schema.
    from src.extopt.orchestrator import _validate_objective_contract

    keys, senses = _validate_objective_contract(wire)
    assert keys == ["P_e_net_MW", "B_peak_T"]
    assert senses["P_e_net_MW"] == "max"

    resolved = resolve_opt_lab_contract_from_extopt_payload(wire)
    assert isinstance(resolved, MultiObjectiveContract)
    assert resolved.hash_sha256() == wire["opt_lab_contract_hash"]


def test_extopt_single_objective_bridges_to_v1() -> None:
    from src.optimization.extopt_contract_bridge import (
        OPT_LAB_SCHEMA,
        build_bridged_extopt_job_contract,
        extopt_v3_to_opt_lab,
        opt_lab_to_extopt_v3,
    )
    from src.optimization.objective_contract import ObjectiveContract

    wire = build_bridged_extopt_job_contract(
        objectives=["R0_m"],
        senses={"R0_m": "min"},
        seed=1,
    )
    assert wire["opt_lab_contract"]["schema"] == OPT_LAB_SCHEMA
    oc = extopt_v3_to_opt_lab(
        {"schema": "objective_contract.v3", "objectives": [{"key": "R0_m", "sense": "min"}]}
    )
    assert isinstance(oc, ObjectiveContract)
    roundtrip = opt_lab_to_extopt_v3(oc)
    assert roundtrip["schema"] == "objective_contract.v3"
    assert roundtrip["objectives"] == [{"key": "R0_m", "sense": "min"}]


def test_certified_front_summary_from_ccfs_and_pareto() -> None:
    from ui_nicegui.lib.certified_front_viewer import (
        CERTIFIED_FRONT_SCHEMA,
        apply_handoff_to_pareto,
        build_certified_front_summary,
        format_front_caption,
        get_certified_front,
        store_certified_front,
        summary_from_ccfs_bundle,
        summary_from_pareto_last,
    )
    from ui_nicegui.session import DesignSession

    ccfs = summary_from_ccfs_bundle(
        {
            "schema_version": "ccfs_verified.v1",
            "n_candidates": 5,
            "n_status_verified": 2,
            "n_status_rejected": 3,
            "opt_run_stamp": {
                "schema": "opt_run_stamp.v1",
                "objective_contract_hash": "a" * 64,
                "n_verified": 2,
                "n_rejected": 3,
            },
        }
    )
    assert ccfs["schema"] == CERTIFIED_FRONT_SCHEMA
    assert ccfs["n_verified"] == 2
    assert ccfs["n_rejected"] == 3
    assert ccfs["authoritative_optimum"] is False
    assert "Proposed — SHAMS-certified" in ccfs["counts_line"]

    pareto = summary_from_pareto_last(
        {
            "n_samples": 100,
            "feasible": [{"id": "a"}, {"id": "b"}],
            "pareto": [{"id": "a"}],
            "summary": {"n_feasible": 2, "n_pareto": 1},
        }
    )
    assert pareto["n_verified"] == 0
    assert pareto["n_rejected"] == 0
    assert pareto["n_blocking_ok"] == 2
    assert pareto["n_hard_fail"] == 98
    assert pareto["n_front"] == 1
    assert pareto["screening_only"] is True
    assert "blocking-OK" in pareto["counts_line"]
    assert "VERIFIED=" not in pareto["counts_line"]
    assert "not L0 FEASIBLE" in pareto["notes"]
    assert "not CCFS VERIFIED" in pareto["notes"]

    session = DesignSession()
    store_certified_front(session, ccfs)
    assert get_certified_front(session)["n_verified"] == 2
    apply_handoff_to_pareto(session)
    assert session.pareto_workflow_step == "3 · Interpret & Audit"
    assert session.pareto_decision_state == "Audit mechanisms & knees"
    assert "VERIFIED" in format_front_caption(ccfs)

    # Empty builder still honesty-safe.
    empty = build_certified_front_summary(
        source="test", n_verified=0, n_rejected=0, n_candidates=0
    )
    assert empty["proposed_certified"] is True
    assert empty["authoritative_optimum"] is False


def test_sync_prefers_ccfs_stamp_over_pareto_screening() -> None:
    from ui_nicegui.lib.certified_front_viewer import (
        store_certified_front,
        summary_from_ccfs_bundle,
        summary_from_pareto_last,
        sync_certified_front_from_session,
    )
    from ui_nicegui.session import DesignSession

    session = DesignSession()
    session.pareto_last = {
        "n_samples": 50,
        "feasible": [{"id": "a"}],
        "pareto": [{"id": "a"}],
        "summary": {"n_feasible": 1, "n_pareto": 1},
    }
    session.opt_lab_last_run_stamp = {
        "schema": "opt_run_stamp.v1",
        "objective_contract_hash": "b" * 64,
        "n_verified": 3,
        "n_rejected": 1,
        "n_candidates": 4,
    }
    out = sync_certified_front_from_session(session)
    assert out is not None
    assert out["n_verified"] == 3
    assert out.get("screening_only") is False
    assert out["source"] == "opt_lab"

    # Without stamp, Pareto screening must not invent VERIFIED counts.
    session2 = DesignSession()
    session2.pareto_last = session.pareto_last
    screen = sync_certified_front_from_session(session2)
    assert screen is not None
    assert screen["n_verified"] == 0
    assert screen["n_blocking_ok"] == 1
    assert screen["screening_only"] is True

    # Stored CCFS handoff must not be overwritten by Pareto alone.
    session3 = DesignSession()
    store_certified_front(
        session3,
        summary_from_ccfs_bundle(
            {"n_status_verified": 4, "n_status_rejected": 1, "n_candidates": 5}
        ),
    )
    session3.pareto_last = session.pareto_last
    kept = sync_certified_front_from_session(session3)
    assert kept["n_verified"] == 4
    assert kept.get("screening_only") is False


def test_certified_front_honesty_and_no_version_tags() -> None:
    from ui_nicegui.lib.certified_front_viewer import (
        FORBIDDEN_PHRASES,
        REQUIRED_PHRASES,
        certified_front_user_facing_texts,
    )

    blob = " ".join(certified_front_user_facing_texts())
    for phrase in REQUIRED_PHRASES:
        assert phrase in blob or phrase.lower() in blob.lower()
    lower = blob.lower()
    for bad in FORBIDDEN_PHRASES:
        # Allow negated warnings only — none of the positive forbidden claims.
        assert bad.lower() not in lower or any(
            m in lower for m in ("never", "not an", "not a")
        ), bad
    # Stricter: no bare "true minimum" as a positive claim without "never"/"not".
    for text in certified_front_user_facing_texts():
        assert not _VERSION_TAG.search(text), text
        low = text.lower()
        if "true minimum" in low:
            assert "never" in low or "not an" in low or "not a" in low


def test_opt_lab_and_pareto_wire_certified_front_viewer() -> None:
    opt_panel = (ROOT / "ui_nicegui/components/opt_lab_entry_panel.py").read_text(
        encoding="utf-8"
    )
    pareto = (ROOT / "ui_nicegui/decks/pareto_lab/__init__.py").read_text(encoding="utf-8")
    helpers = (ROOT / "ui_nicegui/lib/external_optimizer_helpers.py").read_text(
        encoding="utf-8"
    )
    streamlit_opt = (ROOT / "ui/decks/opt_lab.py").read_text(encoding="utf-8")

    assert "render_certified_front_viewer" in opt_panel
    assert "render_certified_front_viewer" in pareto
    assert "build_bridged_extopt_job_contract" in helpers
    assert "CERTIFIED_FRONT_TITLE" in streamlit_opt
    assert "objective_contract.v3" in helpers or "EXTOPT" in helpers


def test_frontier_check_gates_importable() -> None:
    from ui_nicegui.lib.certified_front_viewer import frontier_check_gates

    gates = frontier_check_gates()
    assert "src.extopt.frontier_intake_v406" in gates
    import src.extopt.frontier_intake_v406 as fi

    assert hasattr(fi, "run_frontier_intake_v406")
    assert hasattr(fi, "pareto_front")




def test_l0_untouched_by_unify_modules() -> None:
    bridge = (ROOT / "src/optimization/extopt_contract_bridge.py").read_text(
        encoding="utf-8"
    )
    viewer = (ROOT / "ui_nicegui/lib/certified_front_viewer.py").read_text(encoding="utf-8")
    for text in (bridge, viewer):
        assert "from src.evaluator" not in text
        assert "from src.physics" not in text
        assert "import hot_ion" not in text
        assert "hot_ion_point" not in text
