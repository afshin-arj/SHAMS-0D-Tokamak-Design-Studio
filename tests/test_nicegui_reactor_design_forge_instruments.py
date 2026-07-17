"""Forge instrument engine — group coverage and dispatch smoke."""
from __future__ import annotations

import pytest

from ui_nicegui.lib.forge_instrument_data import ALL_INSTRUMENTS, INSTRUMENT_GROUPS
from ui_nicegui.lib.forge_instrument_engine import build_context, compute_instrument
from ui_nicegui.session import DesignSession


def _session_with_archive() -> DesignSession:
    s = DesignSession()
    s.forge_workbench_run = {
        "intent": "Reactor",
        "archive": [
            {
                "feasible": True,
                "inputs": {"R0_m": 2.0, "Bt_T": 5.5, "Ip_MA": 7.0, "Paux_MW": 40.0},
                "outputs": {"P_e_net_MW": 80.0, "Q_DT_eqv": 2.5, "COE_proxy_USD_per_MWh": 90.0},
                "constraints": [{"name": "q95", "passed": True, "signed_margin": 0.1}],
                "min_signed_margin": 0.1,
                "_score": 3.0,
                "cost": {"COE_proxy": 90.0},
            }
        ],
        "trace": [{"feasible": True, "_score": 1.0}],
        "var_specs": [{"key": "R0_m", "lo": 1.5, "hi": 2.5}],
    }
    s.forge_lens_contract = {"objectives": [{"key": "P_e_net_MW", "sense": "max"}]}
    return s


@pytest.mark.parametrize("tool", ALL_INSTRUMENTS)
def test_all_instruments_return_view(tool: str) -> None:
    ctx = build_context(_session_with_archive())
    view = compute_instrument(tool, ctx)
    assert view is not None
    assert isinstance(view.caption, str)


def test_instrument_groups_cover_registry() -> None:
    grouped = [t for tools in INSTRUMENT_GROUPS.values() for t in tools]
    assert len(grouped) == len(ALL_INSTRUMENTS)
    assert set(grouped) == set(ALL_INSTRUMENTS)


@pytest.mark.parametrize(
    "tool",
    [
        "Run dashboard",
        "Resistance atlas",
        "Margin ledger",
        "Reality gates",
        "Design card",
        "Report pack",
    ],
)
def test_key_instruments_non_empty(tool: str) -> None:
    ctx = build_context(_session_with_archive())
    view = compute_instrument(tool, ctx)
    has_content = bool(view.markdown or view.kpis or view.json_blob is not None or view.table_rows)
    assert has_content or bool(view.error)
