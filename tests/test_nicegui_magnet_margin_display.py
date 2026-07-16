"""Magnet margin display — no raw nan in telemetry (MAG-NAN-001)."""
from __future__ import annotations

from ui_nicegui.lib.pd_parity_helpers import build_coils_metrics, fmt_magnet_margin, magnet_card_metrics


def test_fmt_magnet_margin_off_when_v400_disabled() -> None:
    assert fmt_magnet_margin(float("nan"), v400_enabled=False) == "OFF"


def test_fmt_magnet_margin_dash_when_v400_enabled() -> None:
    assert fmt_magnet_margin(float("nan"), v400_enabled=True) == "—"


def test_magnet_card_nan_margin_display() -> None:
    out = {"magnet_technology": "HTS_REBCO", "tf_sc_flag": 1.0, "sc_margin": float("nan")}
    mc = magnet_card_metrics(out)
    assert mc["sc_margin_display"] == "OFF"


def test_build_coils_hts_margin_not_nan_string() -> None:
    rows = build_coils_metrics({"hts_margin": float("nan")})
    hts = next(v for lab, v in rows if lab == "HTS margin")
    assert hts != "nan"
    assert hts in ("OFF", "—")
