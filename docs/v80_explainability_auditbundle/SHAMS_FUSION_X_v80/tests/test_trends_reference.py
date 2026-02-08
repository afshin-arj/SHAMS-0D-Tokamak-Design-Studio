from __future__ import annotations

from dataclasses import replace

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point

def test_trend_pfus_increases_with_bt():
    base = PointInputs(R0_m=2.0, a_m=0.6, kappa=1.8, Bt_T=10.0, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)
    o1 = hot_ion_point(replace(base, Bt_T=9.0))
    o2 = hot_ion_point(replace(base, Bt_T=11.0))
    # Allow NaN-safe fallback
    pf1 = float(o1.get("Pfus_total_MW", o1.get("Pfus_MW", 0.0)))
    pf2 = float(o2.get("Pfus_total_MW", o2.get("Pfus_MW", 0.0)))
    assert pf2 >= pf1

def test_trend_qdiv_decreases_with_radiation():
    base = PointInputs(R0_m=2.0, a_m=0.6, kappa=1.8, Bt_T=10.0, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)
    # legacy fractional radiation path: vary f_rad
    o1 = hot_ion_point(replace(base, f_rad_core=0.05))
    o2 = hot_ion_point(replace(base, f_rad_core=0.30))
    q1 = float(o1.get("q_div_MW_m2", 1e9))
    q2 = float(o2.get("q_div_MW_m2", 1e9))
    assert q2 <= q1
