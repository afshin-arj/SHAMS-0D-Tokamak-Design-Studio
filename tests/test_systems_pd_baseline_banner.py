"""Systems PD-baseline banner + Mission Snapshot verdict + Pe_net aliases."""
from __future__ import annotations

from pathlib import Path


def test_mission_snapshot_has_local_verdict_banner():
    src = Path("ui_nicegui/decks/point_designer/mission_snapshot.py").read_text(encoding="utf-8")
    assert "verdict_banner" in src
    assert "inputs_stale" in src


def test_power_ledger_pe_net_aliases():
    from ui_nicegui.lib.pd_parity_helpers import power_ledger_badged_rows, power_ledger_rows

    rows = power_ledger_rows({"Pe_net_MW": 42.0})
    assert any("Net electric" in r["channel"] and "42" in r["MW"] for r in rows)
    badged = power_ledger_badged_rows({"Pe_net_MW": 42.0}, feasible=True)
    net = [r for r in badged if "Net electric" in r.get("item", "")]
    assert net and "42" in str(net[0].get("MW"))
