from __future__ import annotations

import math


def test_v407_disabled_returns_stub() -> None:
    from src.analysis.nuclear_data_authority_v407 import evaluate_nuclear_data_authority_v407

    class Inp:
        include_nuclear_data_authority_v407 = False

    r = evaluate_nuclear_data_authority_v407({}, Inp())
    assert r["include_nuclear_data_authority_v407"] is False
    assert r["nuclear_data_authority_ledger_v407"] == []


def test_v407_enabled_screening_proxy() -> None:
    from src.analysis.nuclear_data_authority_v407 import evaluate_nuclear_data_authority_v407

    class Inp:
        include_nuclear_data_authority_v407 = True
        nuclear_dataset_id_v407 = "SCREENING_PROXY_V407"
        nuclear_group_structure_id_v407 = "G6_V407"
        f_geom_to_tf = 1.0

    out = {
        "neutron_wall_load_MW_m2": 2.0,
        "Pfus_total_MW": 500.0,
        "A_fw_m2": 50.0,
    }

    r = evaluate_nuclear_data_authority_v407(out, Inp())
    assert r["include_nuclear_data_authority_v407"] is True
    assert r["nuclear_dataset_id_v407"] == "SCREENING_PROXY_V407"
    assert isinstance(r["nuclear_data_authority_ledger_v407"], list)
    flu = float(r["tf_case_fluence_n_m2_per_fpy_v407"])
    assert flu == flu and math.isfinite(flu) and flu > 0.0
