"""Trade Study advanced sub-deck render routing (UI wiring)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from ui_nicegui.decks.trade_study_studio import advanced as adv
from ui_nicegui.lib.display_labels import DECK_FRONTIER_ATLAS, DECK_REGIME_MAPS, DECK_ROBUST_CERT
from ui_nicegui.lib.trade_study_helpers import ADVANCED_DECKS
from ui_nicegui.session import DesignSession


def _trade_session() -> DesignSession:
    s = DesignSession()
    s.trade_last = {
        "records": [{"is_feasible": False, "i": 0, "min_R0": 1.0}],
        "feasible": [],
        "pareto": [],
        "meta": {
            "objectives": ["min_R0"],
            "objective_senses": {"min_R0": "min"},
            "n_samples": 1,
            "seed": 1,
            "bounds": {"R0_m": [1.5, 2.0]},
        },
        "summary": {"n_samples": 1, "n_feasible": 0, "n_pareto": 0},
    }
    s.active_study_capsule = {"records": s.trade_last["records"], "meta": s.trade_last["meta"]}
    return s


@pytest.mark.parametrize(
    "deck,handler",
    [
        (DECK_FRONTIER_ATLAS, "_render_v351"),
        (DECK_ROBUST_CERT, "_render_v352"),
        ("Feasible-First Surrogate Accelerator", "_render_surrogate_accel"),
        ("Optimizer Kits (External)", "_render_optimizer_kits"),
        ("Fast Optimistic Design (Two-Lane)", "_render_two_lane"),
        ("Design Family Atlas", "_render_family_atlas"),
        (DECK_REGIME_MAPS, "_render_v324"),
        ("Mirage Pathfinding", "_render_mirage_pathfinding"),
    ],
)
def test_render_advanced_deck_dispatches(deck: str, handler: str) -> None:
    s = _trade_session()
    with patch.object(adv, handler) as mock_handler:
        with patch.object(adv, "render_proposal_banner"):
            adv.render_advanced_deck(s, deck)
            mock_handler.assert_called_once_with(s)


def test_render_advanced_deck_unknown() -> None:
    s = _trade_session()
    with patch.object(adv, "empty_state") as mock_empty:
        with patch.object(adv, "render_proposal_banner"):
            adv.render_advanced_deck(s, "Not a real deck")
            mock_empty.assert_called_once()


def test_require_trade_last_missing() -> None:
    s = DesignSession()
    with patch.object(adv, "empty_state") as mock_empty:
        assert adv._require_trade_last(s) is None
        mock_empty.assert_called_once()


def test_advanced_deck_list_matches_handlers() -> None:
    assert len(ADVANCED_DECKS) == 8
    assert DECK_FRONTIER_ATLAS in ADVANCED_DECKS
    assert "Mirage Pathfinding" in ADVANCED_DECKS


def test_advanced_router_refreshes_deck_body_on_category_change() -> None:
    import inspect

    from ui_nicegui.decks import trade_study_studio as ts_mod

    src = inspect.getsource(ts_mod._render_advanced_router)
    assert "_deck_body.refresh" in src
    assert "on_change=_on_deck_change" in src


def test_advanced_tab_uses_json_view_not_ui_json() -> None:
    import inspect

    from ui_nicegui.decks.trade_study_studio import advanced as adv_mod

    src = inspect.getsource(adv_mod)
    assert "render_json_blob" in src
    assert "ui.json" not in src
