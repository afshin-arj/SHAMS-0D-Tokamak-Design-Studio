import math
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs

def _base():
    return PointInputs(
        R0_m=1.81,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=7.5,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=25.0,
    )

def test_hot_ion_point_smoke():
    out = hot_ion_point(_base())
    assert math.isfinite(out.get("Pfus_total_MW", float("nan")))
    assert out["Pfus_total_MW"] >= 0.0

def test_constraints_smoke():
    out = hot_ion_point(_base())
    cs = build_constraints_from_outputs(out)
    assert len(cs) > 3
    # margins must be finite for constraints that have finite limits
    for c in cs:
        assert c.name
        assert math.isfinite(float(c.value))
