from __future__ import annotations

from physics.hot_ion import hot_ion_point
from models.inputs import PointInputs


def test_v402_pipeline_merge_when_default_on() -> None:
    """PROPOSAL-007: v402 merges when schema default is ON (standard import path)."""
    inp = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.7,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=50.0,
        include_authority_dominance_v402=True,
    )
    out = hot_ion_point(inp)
    assert out.get("include_authority_dominance_v402") is True
    assert "global_dominant_authority_v402" in out
    assert isinstance(out.get("dominance_order_v402"), list)
