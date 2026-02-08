import pytest
import math

from models.reference_machines import reference_presets
from physics.hot_ion import hot_ion_point

def _get_first(out, keys):
    for k in keys:
        if k in out and out.get(k) is not None:
            return float(out.get(k))
    return float("nan")

@pytest.mark.parametrize("name", ["SPARC-class", "ARC-class", "ITER-inspired", "HH170"])
def test_reference_preset_runs(name):
    presets = reference_presets()
    assert name in presets, f"Missing preset: {name}"
    inp = presets[name]
    out = hot_ion_point(inp)

    Q = _get_first(out, ["Q", "Q_DT_eqv"])
    Pfus = _get_first(out, ["Pfus_total_MW", "Pfus_MW"])
    Pnet = _get_first(out, ["P_e_net_MW", "Pe_net_MW"])
    betaN = _get_first(out, ["betaN", "betaN_proxy"])
    q95 = _get_first(out, ["q95", "q95_proxy"])

    for v in [Q, Pfus, Pnet, betaN, q95]:
        assert v == v, f"{name}: got NaN in key outputs"
