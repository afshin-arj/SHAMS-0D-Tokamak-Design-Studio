"""Regime compass / power ledger badge demotion honesty (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.lib.pd_parity_helpers import (
    BASELINE_DELTA_KPIS,
    fuel_cycle_metric_groups,
    power_ledger_badged_rows,
    regime_compass_rows,
)


def test_compass_h98_fg_are_proxy_not_authoritative():
    rows = {r["key"]: r for r in regime_compass_rows({})}
    assert rows["H98"]["type"] == "Proxy"
    assert rows["fG"]["type"] == "Proxy"
    assert rows["q95_proxy"]["type"] == "Proxy"
    assert rows["beta_N"]["type"] == "Proxy"


def test_compass_h98_alias_and_fuel_tbr_v403():
    rows = {r["key"]: r for r in regime_compass_rows({"H_IPB98y2": 1.15}, feasible=True)}
    assert "1.15" in str(rows["H98"]["value"])
    groups = fuel_cycle_metric_groups({"tbr_proxy_v403": 1.08})
    flat = {lab: val for g in groups for lab, val in g}
    assert "1.08" in flat.get("TBR (proxy)", "")


def test_power_ledger_bookkeeping_is_proxy_paux_authoritative():
    rows = {r["key"]: r for r in power_ledger_badged_rows({})}
    assert rows["Paux_MW"]["type"] == "Authoritative"
    for key in ("Pin_MW", "Palpha_MW", "P_SOL_MW", "Ploss_MW", "P_e_net_MW", "Pfus_total_MW"):
        assert rows[key]["type"] == "Proxy", key
    assert rows["Pohm_MW"]["type"] == "Diagnostic"


def test_baseline_delta_alias_tuples():
    by_label = {t[0]: t[3] for t in BASELINE_DELTA_KPIS}
    assert "H_IPB98y2" in by_label["H98"]
    assert "tbr_proxy_v403" in by_label["TBR (proxy)"]
    assert "Pe_net_MW" in by_label["P_net_e"]


def test_mission_snapshot_badge_blurb_clarifies_authoritative():
    src = Path("ui_nicegui/decks/point_designer/mission_snapshot.py").read_text(encoding="utf-8")
    assert "not first-principles certification" in src
    assert "0-D plant bookkeeping" in src or "empirical scaling" in src
