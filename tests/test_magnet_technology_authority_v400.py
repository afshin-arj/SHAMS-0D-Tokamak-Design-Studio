from __future__ import annotations

import math


def test_v400_disabled_returns_off() -> None:
    from src.analysis.magnet_technology_authority_v400 import evaluate_magnet_technology_authority_v400

    class Inp:
        include_magnet_technology_authority_v400 = False

    r = evaluate_magnet_technology_authority_v400(Inp(), {})
    assert r["magnet_v400_enabled"] is False


def test_v400_computes_margin_ledger() -> None:
    from src.analysis.magnet_technology_authority_v400 import evaluate_magnet_technology_authority_v400

    class Inp:
        include_magnet_technology_authority_v400 = True
        magnet_technology = "HTS"

    out = {
        "B_peak_T": 20.0,
        "B_peak_allow_T": 22.0,
        "J_eng_A_mm2": 180.0,
        "J_eng_max_A_mm2": 250.0,
        "sigma_vm_MPa": 400.0,
        "sigma_allow_MPa": 900.0,
        "hts_margin": 1.2,
        "hts_margin_min": 1.0,
        "Tcoil_K": 20.0,
        "Tcoil_min_K": 4.0,
        "Tcoil_max_K": 30.0,
    }

    r = evaluate_magnet_technology_authority_v400(Inp(), out)
    assert r["magnet_v400_enabled"] is True
    mm = float(r["magnet_v400_margin"])
    assert mm == mm and math.isfinite(mm)
    assert r["magnet_v400_technology"] == "HTS"
    assert r["magnet_v400_tier"] in {"comfortable", "near_limit", "deficit", "unknown"}
