"""Batch 4: Scan Lab cartography wiring."""

from __future__ import annotations



from ui_nicegui.decks.scan_lab import render_scan_lab

from ui_nicegui.evaluate import ui_evaluate

from ui_nicegui.lib.scan_helpers import (

    default_scan_bounds,

    report_to_json_bytes,

    run_cartography_scan,

    summarize_scan_report,

)

from ui_nicegui.lib.session_store import set_point_evaluation

from ui_nicegui.session import DesignSession





def test_scan_lab_renderer_import() -> None:

    assert callable(render_scan_lab)





def test_default_scan_bounds() -> None:

    s = DesignSession()

    base = s.build_point_inputs()

    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")

    assert x_hi > x_lo

    assert y_hi > y_lo





def test_run_cartography_scan_smoke() -> None:

    s = DesignSession()

    base = s.build_point_inputs()

    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")

    rep = run_cartography_scan(

        base,

        x_key="Ip_MA",

        y_key="R0_m",

        x_lo=x_lo,

        x_hi=x_hi,

        y_lo=y_lo,

        y_hi=y_hi,

        nx=11,

        ny=11,

        intents=["Reactor"],

        include_outputs=False,

    )

    assert rep.get("kind") == "shams_scan_cartography"

    assert int(rep.get("n_points") or 0) == 121

    summary = summarize_scan_report(rep)

    assert summary["loaded"] is True

    assert summary["robustness"] in (
        "Robust",
        "Balanced",
        "Brittle",
        "Knife-edge",
        "Dense slice",
        "Moderate slice",
        "Sparse slice",
        "Near-empty slice",
    )





def test_scan_report_json_export() -> None:

    s = DesignSession()

    base = s.build_point_inputs()

    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Paux_MW", "fG")

    rep = run_cartography_scan(

        base,

        x_key="Paux_MW",

        y_key="fG",

        x_lo=x_lo,

        x_hi=x_hi,

        y_lo=y_lo,

        y_hi=y_hi,

        nx=11,

        ny=11,

        intents=["Reactor"],

    )

    data = report_to_json_bytes(rep)

    assert b"shams_scan_cartography" in data





def test_scan_verdict_after_point_eval() -> None:

    s = DesignSession()

    out = ui_evaluate(s.build_point_inputs(), origin="test")

    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))

    base = s.build_point_inputs()

    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")

    s.scan_cartography_report = run_cartography_scan(

        base,

        x_key="Ip_MA",

        y_key="R0_m",

        x_lo=x_lo,

        x_hi=x_hi,

        y_lo=y_lo,

        y_hi=y_hi,

        nx=11,

        ny=11,

        intents=["Reactor"],

    )

    summary = summarize_scan_report(s.scan_cartography_report)

    assert summary["n_points"] == 121


