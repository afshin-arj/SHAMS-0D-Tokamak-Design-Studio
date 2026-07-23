"""Forge design-card / narrative PHYS-KPI-001 honesty on INFEASIBLE candidates."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _infeas_cand() -> dict:
    return {
        "id": "c_bad",
        "feasible": False,
        "feasibility_state": "INFEASIBLE",
        "intent": "pilot",
        "outputs": {
            "Q_DT_eqv": 12.0,
            "H98": 1.2,
            "q95": 3.5,
            "P_fus_MW": 500.0,
            "P_e_net_MW": 100.0,
        },
        "closure_bundle": {
            "gross_electric_MW": 140.0,
            "recirc_electric_MW": 40.0,
            "net_electric_MW": 100.0,
        },
    }


def _feas_cand() -> dict:
    c = _infeas_cand()
    c["id"] = "c_ok"
    c["feasible"] = True
    c["feasibility_state"] = "FEASIBLE"
    return c


def test_design_card_watermarks_claim_foms_on_infeasible():
    from tools.sandbox.design_card import build_design_card_md

    md = build_design_card_md(_infeas_cand())
    assert "PHYS-KPI-001" in md
    assert "— (diagnostic)" in md
    assert "Q_DT_eqv: `12" not in md
    assert "P_e_net_MW: `100" not in md
    assert "Net electric: `100" not in md
    assert "diagnostic on INFEASIBLE" in md


def test_design_card_keeps_claim_foms_when_feasible():
    from tools.sandbox.design_card import build_design_card_md

    md = build_design_card_md(_feas_cand())
    assert "PHYS-KPI-001" not in md
    assert "Q_DT_eqv: `12" in md
    assert "Net electric: `100" in md


def test_narrative_watermarks_net_on_infeasible():
    from tools.sandbox.narrative_pack import build_narrative

    nar = build_narrative(_infeas_cand())
    md = nar["markdown"]
    assert nar["feasible"] is False
    assert "PHYS-KPI-001" in md
    assert "— (diagnostic)" in md
    assert "net **100" not in md


def test_narrative_keeps_net_when_feasible():
    from tools.sandbox.narrative_pack import build_narrative

    nar = build_narrative(_feas_cand())
    assert nar["feasible"] is True
    assert "net **100" in nar["markdown"]
    assert "PHYS-KPI-001" not in nar["markdown"]


def test_design_packet_watermarks_net_headline():
    from tools.sandbox.design_packet import build_design_packet_markdown

    md = build_design_packet_markdown(
        title="Packet",
        card_md="# card",
        narrative_md="# nar",
        candidate=_infeas_cand(),
    )
    assert "— (diagnostic)" in md
    assert "PHYS-KPI-001" in md
    assert "Net electric (MW): 100" not in md


def test_nicegui_wrappers_no_longer_pass_bad_kwargs():
    helpers = Path("ui_nicegui/lib/forge_interpret_helpers.py").read_text(encoding="utf-8")
    assert "build_design_card_md(c)" in helpers
    assert "build_design_card_md(cand, intent=" not in helpers

    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "build_narrative(c)" in eng
    assert "build_narrative(cand, intent=" not in eng
    assert "card_md=card_md" in eng
    assert "narrative_md=narrative_md" in eng


def test_design_card_markdown_wrapper_renders():
    from ui_nicegui.lib.forge_interpret_helpers import design_card_markdown

    md = design_card_markdown(_infeas_cand(), "pilot")
    assert md
    assert "PHYS-KPI-001" in md
    assert "— (diagnostic)" in md
