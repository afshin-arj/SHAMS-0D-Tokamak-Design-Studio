"""Forge Review Room / Reviewer Packet PHYS-KPI-001 honesty on INFEASIBLE."""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _infeas() -> dict:
    return {
        "id": "rr_bad",
        "feasible": False,
        "feasibility_state": "INFEASIBLE",
        "intent": "pilot",
        "failure_mode": "q95",
        "min_signed_margin": -0.2,
        "inputs": {"R0_m": 6.0},
        "outputs": {
            "Q_DT_eqv": 12.0,
            "H98": 1.2,
            "P_fus_MW": 500.0,
            "P_e_net_MW": 100.0,
        },
        "closure_bundle": {
            "gross_electric_MW": 140.0,
            "recirc_electric_MW": 40.0,
            "net_electric_MW": 100.0,
        },
        "constraints": [],
    }


def test_review_trinity_watermarks_net_on_infeasible():
    from tools.sandbox.review_room import build_review_trinity

    tri = build_review_trinity(candidate=_infeas())
    closure = (tri.get("stress_story") or {}).get("closure") or {}
    assert closure.get("net_electric_MW") == "— (diagnostic)"
    # Fallback from outputs when only P_e_net_MW naming exists
    assert "PHYS-KPI-001" in tri["markdown"]
    assert "— (diagnostic)" in tri["markdown"]
    assert "`P_e_net_MW`: `100" not in tri["markdown"]
    assert "`net_electric_MW`: `100" not in tri["markdown"]
    assert tri.get("phys_kpi_note")


def test_review_trinity_keeps_net_when_feasible():
    from tools.sandbox.review_room import build_review_trinity

    c = _infeas()
    c["feasible"] = True
    c["feasibility_state"] = "FEASIBLE"
    tri = build_review_trinity(candidate=c)
    closure = (tri.get("stress_story") or {}).get("closure") or {}
    assert closure.get("net_electric_MW") == 100.0
    assert "PHYS-KPI-001" not in tri["markdown"]


def test_review_trinity_picks_output_pnet_alias():
    from tools.sandbox.review_room import build_review_trinity

    c = {
        "feasible": False,
        "outputs": {"P_e_net_MW": 88.0},
        "closure_bundle": {},
    }
    tri = build_review_trinity(candidate=c)
    closure = (tri.get("stress_story") or {}).get("closure") or {}
    assert "P_e_net_MW" in closure
    assert closure["P_e_net_MW"] == "— (diagnostic)"


def test_reviewer_packet_watermarks_trinity_and_report_pack():
    from tools.sandbox.reviewer_packet_builder import ReviewerPacketOptions, build_reviewer_packet_zip

    zip_bytes, _summary = build_reviewer_packet_zip(
        candidate=_infeas(),
        repo_root=Path(_ROOT),
        options=ReviewerPacketOptions(
            include_core_docs=False,
            include_ui_wiring_index=False,
            include_design_state_graph_snapshot=False,
            include_repo_manifests=False,
            include_attack_simulation=False,
            include_run_capsule=False,
            include_scan_grounding=False,
            include_do_not_build_brief=False,
        ),
    )
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        md = zf.read("review_trinity/review_trinity.md").decode("utf-8")
        tri = json.loads(zf.read("review_trinity/review_trinity.json").decode("utf-8"))
        rp_md = zf.read("report_pack/report_pack.md").decode("utf-8")
        rp_j = json.loads(zf.read("report_pack/report_pack.json").decode("utf-8"))
        rp_csv = zf.read("report_pack/report_pack.csv").decode("utf-8")
        cand = json.loads(zf.read("candidate.json").decode("utf-8"))
    assert "PHYS-KPI-001" in md
    assert "— (diagnostic)" in md
    assert (tri.get("stress_story") or {}).get("closure", {}).get("net_electric_MW") == "— (diagnostic)"
    assert "PHYS-KPI-001" in rp_md
    assert rp_j.get("key_outputs", {}).get("Q_DT_eqv") == "— (diagnostic)"
    assert rp_j.get("closure_bundle", {}).get("net_electric_MW") == "— (diagnostic)"
    # CSV must not ship raw claim FoMs on INFEASIBLE.
    assert "12.0" not in rp_csv or "diagnostic" in rp_csv
    assert "Q_DT_eqv,— (diagnostic)" in rp_csv or "key_outputs.Q_DT_eqv,— (diagnostic)" in rp_csv
    assert cand.get("outputs", {}).get("Q_DT_eqv") == "— (diagnostic)"
    assert cand.get("outputs", {}).get("P_e_net_MW") == "— (diagnostic)"


def test_inst_review_trinity_uses_source_markdown():
    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "build_review_trinity" in eng
    assert 'tri.get("markdown")' in eng or "tri.get('markdown')" in eng


def test_forge_soft_gate_keeps_workbench_after_pd_clear():
    src = Path("ui_nicegui/decks/reactor_design_forge/__init__.py").read_text(encoding="utf-8")
    assert "_has_forge_workbench" in src
    assert "BASELINE CLEARED" in src
    assert "FORGE_RUNNING_ATTRS" in src.split("def _set_forge_review_mode")[1].split("def ")[0]
    hand = Path("ui_nicegui/decks/reactor_design_forge/handoff_panel.py").read_text(encoding="utf-8")
    assert "pd_pending_forge_eval = True" in hand
    pd = Path("ui_nicegui/decks/point_designer/__init__.py").read_text(encoding="utf-8")
    assert "FORGE PROMOTE — EVAL PENDING" in pd
    assert "pd_pending_forge_eval" in pd
    cap = Path("ui_nicegui/lib/forge_machine_finder_helpers.py").read_text(encoding="utf-8")
    assert "watermark_extopt_zip_bytes" in cap.split("def build_capsule_zip_bytes")[1].split("def ")[0]