from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point

def test_fusion_increases_with_temperature_local():
    base = PointInputs(R0_m=1.81,a_m=0.57,kappa=1.8,Bt_T=12.2,Ip_MA=7.5,Ti_keV=10.0,fG=0.85,Paux_MW=25.0)
    out1 = hot_ion_point(base)
    out2 = hot_ion_point(base.__class__(**{**base.__dict__, "Ti_keV": 12.0}))
    assert out2["Pfus_total_MW"] >= out1["Pfus_total_MW"]

def test_greenwald_density_increases_with_current():
    base = PointInputs(R0_m=1.81,a_m=0.57,kappa=1.8,Bt_T=12.2,Ip_MA=6.0,Ti_keV=12.0,fG=0.85,Paux_MW=25.0)
    out1 = hot_ion_point(base)
    out2 = hot_ion_point(base.__class__(**{**base.__dict__, "Ip_MA": 8.0}))
    assert out2["ne20"] >= out1["ne20"]
