import math


def test_species_library_contains_required_species():
    from src.physics.impurities.species_library import Species  # type: ignore

    # Literal typing is compile-time, but we can at least ensure the module imports
    # and provides the required symbols.
    assert "C" in str(Species)
    assert "N" in str(Species)
    assert "Ne" in str(Species)
    assert "Ar" in str(Species)
    assert "W" in str(Species)


def test_radiation_partition_sums_and_sol_key():
    from src.physics.impurities.species_library import ImpurityContract, evaluate_impurity_radiation_partition  # type: ignore

    rp = evaluate_impurity_radiation_partition(
        ImpurityContract(species="Ne", f_z=3e-4, f_core=0.5, f_edge=0.2, f_sol=0.2, f_divertor=0.1),
        ne20=1.0,
        volume_m3=100.0,
        t_keV=10.0,
    )
    assert rp.prad_sol_MW == rp.prad_sol_MW
    # Partition should sum to total (within floating error)
    s = rp.prad_core_MW + rp.prad_edge_MW + rp.prad_sol_MW + rp.prad_div_MW
    assert math.isfinite(s)
    assert abs(s - rp.prad_total_MW) <= 1e-9 * max(1.0, abs(rp.prad_total_MW))


def test_detachment_inversion_monotonicity():
    from src.physics.impurities.detachment_authority import detachment_requirement_from_target  # type: ignore

    dr_lo = detachment_requirement_from_target(
        species="Ne",
        ne20=1.0,
        volume_m3=100.0,
        P_SOL_MW=50.0,
        q_div_no_rad_MW_m2=20.0,
        q_div_target_MW_m2=15.0,
        T_sol_keV=0.08,
        f_V_sol_div=0.12,
    )
    dr_hi = detachment_requirement_from_target(
        species="Ne",
        ne20=1.0,
        volume_m3=100.0,
        P_SOL_MW=50.0,
        q_div_no_rad_MW_m2=20.0,
        q_div_target_MW_m2=10.0,
        T_sol_keV=0.08,
        f_V_sol_div=0.12,
    )
    # Stricter target => higher required radiation fraction and fz.
    assert dr_hi.f_sol_div_required >= dr_lo.f_sol_div_required
    assert dr_hi.f_z_required >= dr_lo.f_z_required
