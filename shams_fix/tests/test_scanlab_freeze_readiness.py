import pytest


def test_scanlab_imports_ok():
    # Core Scan Lab modules must import cleanly (regression for 'Scan cartography engine unavailable')
    from src.evaluator.core import Evaluator  # noqa
    from tools.scan_cartography import build_cartography_report  # noqa
    from tools.scan_artifact_schema import build_scan_artifact, upgrade_scan_artifact  # noqa


@pytest.mark.slow
def test_scanlab_golden_smoke_and_schema_v1():
    import numpy as np
    from src.evaluator.core import Evaluator
    from src.models.reference_machines import reference_presets
    from tools.golden_scans import build_golden_scan_presets
    from tools.scan_cartography import build_cartography_report
    from tools.scan_artifact_schema import build_scan_artifact, SCAN_SCHEMA_VERSION

    base = reference_presets()["REF|REACTOR|ITER"]
    g = build_golden_scan_presets(base_inputs=base)[0]

    ev = Evaluator(cache_enabled=True)
    rep = build_cartography_report(
        evaluator=ev,
        base_inputs=g.get("base_inputs", base),
        x_key=str(g["x_key"]),
        y_key=str(g["y_key"]),
        x_vals=list(np.linspace(g["x_range"][0], g["x_range"][1], 9)),
        y_vals=list(np.linspace(g["y_range"][0], g["y_range"][1], 7)),
        intents=list(g.get("intents") or ["Reactor"]),
    )
    art = build_scan_artifact(report=rep, settings={"test": True}, metadata={})
    assert int(art.get("scan_schema_version")) == int(SCAN_SCHEMA_VERSION)
    assert "report_hash" in art and isinstance(art["report_hash"], str)
