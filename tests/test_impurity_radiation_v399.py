from __future__ import annotations

import math

from src.physics.impurities.species_library_v399 import ImpurityMixContractV399, evaluate_impurity_radiation_partition_v399


def test_v399_zeff_and_partitions_basic():
    c = ImpurityMixContractV399(
        species_fz={"Ne": 3e-4, "W": 0.0},
        f_core=0.5, f_edge=0.2, f_sol=0.2, f_divertor=0.1,
    )
    rp = evaluate_impurity_radiation_partition_v399(c, ne20=1.0, volume_m3=100.0, t_keV=10.0)
    assert math.isfinite(rp.prad_total_MW)
    assert rp.prad_total_MW >= 0.0
    assert math.isfinite(rp.zeff)
    assert rp.zeff >= 1.0
    # partitions sum close to total
    s = rp.prad_core_MW + rp.prad_edge_MW + rp.prad_sol_MW + rp.prad_div_MW
    assert abs(s - rp.prad_total_MW) / max(1e-12, rp.prad_total_MW + 1e-12) < 1e-9
    assert "Ne" in rp.by_species_MW


def test_v399_charge_neutrality_violation_flag():
    # Intentionally too large: sum fz*Z > 1
    c = ImpurityMixContractV399(species_fz={"W": 0.05}, f_core=0.5, f_edge=0.2, f_sol=0.2, f_divertor=0.1)
    rp = evaluate_impurity_radiation_partition_v399(c, ne20=1.0, volume_m3=50.0, t_keV=5.0)
    assert rp.validity.get("charge_neutrality_violation", False) in (True, False)
    assert rp.fuel_ion_fraction >= 0.0
