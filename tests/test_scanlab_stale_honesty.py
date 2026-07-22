"""Scan Lab STALE / cartography baseline-drift honesty."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_hash_scan_base_inputs_matches_cartography():
    from tools.scan_cartography import _serialize_inputs, _stable_hash
    from ui_nicegui.lib.scan_helpers import hash_scan_base_inputs

    base = {"R0_m": 6.2, "Ip_MA": 15.0, "Bt_T": 5.3}
    assert hash_scan_base_inputs(base) == _stable_hash(_serialize_inputs(base))


def test_scan_cartography_stale_vs_session():
    from ui_nicegui.lib.scan_helpers import hash_scan_base_inputs, scan_cartography_stale_vs_session

    class _Sess:
        def __init__(self, d):
            self._d = d
            self.scan_cartography_report = None

        def build_point_inputs(self):
            return dict(self._d)

    sess = _Sess({"R0_m": 6.0, "Ip_MA": 12.0})
    h0 = hash_scan_base_inputs(sess.build_point_inputs())
    sess.scan_cartography_report = {"base_inputs_hash": h0, "n_points": 10}
    assert scan_cartography_stale_vs_session(sess) is False

    sess._d["R0_m"] = 7.0
    assert scan_cartography_stale_vs_session(sess) is True

    assert scan_cartography_stale_vs_session(SimpleNamespace(scan_cartography_report=None)) is False
    assert (
        scan_cartography_stale_vs_session(
            SimpleNamespace(scan_cartography_report={"n_points": 1}, build_point_inputs=lambda: {})
        )
        is False
    )


def test_scan_lab_ui_wires_stale_banners():
    init_src = Path("ui_nicegui/decks/scan_lab/__init__.py").read_text(encoding="utf-8")
    assert "inputs_stale" in init_src
    assert "SCAN MAP STALE" in init_src
    assert "STALE · " in init_src
    assert "scan_cartography_stale_vs_session" in init_src

    vsrc = Path("ui_nicegui/decks/scan_lab/verdict.py").read_text(encoding="utf-8")
    assert "map_stale" in vsrc
    assert "SCAN MAP STALE" in vsrc

    wsrc = Path("ui_nicegui/decks/scan_lab/workbench.py").read_text(encoding="utf-8")
    assert "scan_cartography_stale_vs_session" in wsrc
    assert "SCAN MAP STALE" in wsrc
