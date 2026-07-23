"""Forge History Repro PHYS-KPI-001 honesty on INFEASIBLE candidates."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _infeas() -> dict:
    return {
        "feasible": False,
        "feasibility_state": "INFEASIBLE",
        "outputs": {
            "Q_DT_eqv": 12.0,
            "Pfus_total_MW": 500.0,
            "P_e_net_MW": 100.0,
            "beta_N": 2.0,
            "q95_proxy": 3.5,
        },
    }


def _feas() -> dict:
    c = _infeas()
    c["feasible"] = True
    c["feasibility_state"] = "FEASIBLE"
    return c


def test_history_repro_watermarks_claim_deltas_on_infeasible():
    from tools.sandbox.history_repro import history_repro_bundle

    bundle = history_repro_bundle(_infeas())
    assert bundle["feasible"] is False
    assert "PHYS-KPI-001" in bundle.get("phys_kpi_note", "")
    assert bundle["refs"]
    for ref in bundle["refs"]:
        if ref.get("error"):
            continue
        comp = ref.get("comparison") or {}
        for metric in ("Q", "Pfus_MW", "Pnet_MW"):
            row = comp.get(metric) or {}
            assert row.get("candidate") == "— (diagnostic)"
            assert row.get("delta") == "— (diagnostic)"
        # Non-claim rows stay numeric when available
        beta = (comp.get("betaN") or {}).get("candidate")
        assert beta is None or isinstance(beta, (int, float))


def test_history_repro_keeps_claim_deltas_when_feasible():
    from tools.sandbox.history_repro import history_repro_bundle

    bundle = history_repro_bundle(_feas())
    assert bundle["feasible"] is True
    assert "phys_kpi_note" not in bundle
    q = ((bundle["refs"][0].get("comparison") or {}).get("Q") or {})
    assert isinstance(q.get("candidate"), (int, float))
    assert q.get("delta") is None or isinstance(q.get("delta"), (int, float))


def test_report_pack_reference_context_inherits_watermark():
    from tools.sandbox.report_pack import build_report_pack

    pack = build_report_pack(candidate=_infeas())
    md = pack["markdown"]
    assert "PHYS-KPI-001" in md
    assert "ΔQ=— (diagnostic)" in md or "ΔQ=— (diagnostic)" in md.replace("\u2014", "—")
    hist = (pack.get("json") or {}).get("reference_context") or {}
    for ref in hist.get("refs") or []:
        q = (ref.get("comparison") or {}).get("Q") or {}
        if "error" in ref:
            continue
        assert q.get("delta") == "— (diagnostic)"


def test_inst_reference_reproduction_and_citation_wiring():
    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001: Q / Pfus / P_net deltas vs historical anchors" in eng
    assert "build_citation_blocks(root)" in eng
    assert "build_citation_blocks(cand, intent=" not in eng
