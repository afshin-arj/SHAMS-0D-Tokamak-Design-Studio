"""AUTO-GENERATED from authority_caps.json — do not edit by hand.

Regenerate: python -m constraints.registry_codegen
"""
from __future__ import annotations

from typing import Any, Dict, List

REGISTRY_SPECS: List[Dict[str, Any]] = [
    {"name": "Transport spread", "value_key": "transport_spread_ratio_v396", "sense": "<=", "limit_hi_key": "transport_spread_max_v396", "group": "transport", "authority": "v396"},
    {"name": "Profile peaking f_p0", "value_key": "profile_peaking_p_v397", "sense": "<=", "limit_hi_key": "profile_peaking_p_max_v397", "group": "profiles", "authority": "v397"},
    {"name": "q95 proxy", "value_key": "q95_proxy_v397", "sense": ">=", "limit_lo_key": "q95_proxy_min_v397", "group": "profiles", "authority": "v397"},
    {"name": "q0 proxy", "value_key": "q0_proxy_v397", "sense": ">=", "limit_lo_key": "q0_proxy_min_v397", "group": "profiles", "authority": "v397"},
    {"name": "Bootstrap localization", "value_key": "bootstrap_localization_index_v397", "sense": "<=", "limit_hi_key": "bootstrap_localization_max_v397", "group": "profiles", "authority": "v397"},
    {"name": "VS budget margin", "value_key": "vs_budget_margin_v398", "sense": ">=", "limit_lo_key": "vs_budget_margin_min_v398", "group": "control", "authority": "v398"},
    {"name": "VDE headroom", "value_key": "vde_headroom_v398", "sense": ">=", "limit_lo_key": "vde_headroom_min_v398", "group": "control", "authority": "v398"},
    {"name": "RWM proximity", "value_key": "rwm_proximity_index_v398", "sense": "<=", "limit_hi_key": "rwm_proximity_index_max_v398", "group": "control", "authority": "v398"},
    {"name": "Zeff", "value_key": "impurity_v399_zeff", "sense": "<=", "limit_hi_key": "zeff_max_v399", "group": "exhaust", "authority": "v399", "enabled_key": "include_impurity_v399"},
    {"name": "Detachment margin", "value_key": "detachment_margin_v399", "sense": ">=", "limit_lo_key": "detachment_margin_min_v399", "group": "exhaust", "authority": "v399", "enabled_key": "include_impurity_v399"},
    {"name": "FW DPA", "value_key": "dpa_fw_v403", "sense": "<=", "limit_hi_key": "dpa_fw_max_v403", "group": "neutronics", "authority": "v403"},
    {"name": "TBR proxy", "value_key": "tbr_proxy_v403", "sense": ">=", "limit_lo_key": "tbr_proxy_min_v403", "group": "neutronics", "authority": "v403"},
    {"name": "TF case fluence", "value_key": "tf_case_fluence_n_m2_per_fpy_v407", "sense": "<=", "limit_hi_key": "tf_case_fluence_max_n_m2_per_fpy_v392", "group": "neutronics", "authority": "v407"},
    {"name": "ELM transient heat flux", "value_key": "elm_transient_q_parallel_MW_m2_v409", "sense": "<=", "limit_hi_key": "elm_transient_q_parallel_max_MW_m2_v409", "group": "exhaust", "authority": "v409", "enabled_key": "include_elm_transient_heat_v409"},
    {"name": "Tritium in-vessel inventory", "value_key": "T_in_vessel_required_kg", "sense": "<=", "limit_hi_key": "T_in_vessel_max_kg", "group": "fuel_cycle", "authority": "v405", "enabled_key": "include_tritium_tight_closure"},
    {"name": "Tritium total inventory", "value_key": "T_total_inventory_required_kg", "sense": "<=", "limit_hi_key": "T_total_inventory_max_kg", "group": "fuel_cycle", "authority": "v405", "enabled_key": "include_tritium_tight_closure"},
    {"name": "TBR effective (tight closure)", "value_key": "TBR_eff_fuelcycle", "sense": ">=", "limit_lo_key": "TBR_self_sufficiency_required", "group": "fuel_cycle", "authority": "v405", "enabled_key": "include_tritium_tight_closure"},
    {"name": "CD ECCD electric (mix)", "value_key": "P_cd_eccd_el_MW", "sense": "<=", "limit_hi_key": "P_cd_eccd_max_MW", "group": "plant", "authority": "v408", "enabled_key": "cd_mix_enable"},
    {"name": "CD LHCD electric (mix)", "value_key": "P_cd_lhcd_el_MW", "sense": "<=", "limit_hi_key": "P_cd_lhcd_max_MW", "group": "plant", "authority": "v408", "enabled_key": "cd_mix_enable"},
    {"name": "CD mix fraction sum", "value_key": "cd_mix_frac_sum", "sense": "<=", "limit_hi_key": "cd_mix_frac_sum_max", "group": "plant", "authority": "v408", "enabled_key": "cd_mix_enable"},
    {"name": "Magnet SC system margin", "value_key": "magnet_v410_system_margin", "sense": ">=", "limit_lo_key": "magnet_system_margin_min_v410", "group": "magnets", "authority": "v410", "enabled_key": "include_magnet_sc_system_authority_v410"},
    {"name": "TF family margin", "value_key": "magnet_v410_tf_margin", "sense": ">=", "limit_lo_key": "tf_family_margin_min_v410", "group": "magnets", "authority": "v410", "enabled_key": "include_magnet_sc_system_authority_v410"},
    {"name": "PF family margin", "value_key": "magnet_v410_pf_margin", "sense": ">=", "limit_lo_key": "pf_family_margin_min_v410", "group": "magnets", "authority": "v410", "enabled_key": "include_magnet_sc_system_authority_v410"},
    {"name": "CS family margin", "value_key": "magnet_v410_cs_margin", "sense": ">=", "limit_lo_key": "cs_family_margin_min_v410", "group": "magnets", "authority": "v410", "enabled_key": "include_magnet_sc_system_authority_v410"},
    {"name": "Machine-build closure", "value_key": "machine_v412_system_margin", "sense": ">=", "limit_lo_key": "machine_build_closure_margin_min_v412", "group": "build", "authority": "v412", "enabled_key": "include_machine_build_authority_v412"},
    {"name": "Inboard build clearance", "value_key": "machine_v412_inboard_margin_m", "sense": ">=", "limit_lo_key": "machine_build_inboard_margin_min_m_v412", "group": "build", "authority": "v412", "enabled_key": "include_machine_build_authority_v412"},
    {"name": "Build gap clearance", "value_key": "machine_v412_gap_thickness_m", "sense": ">=", "limit_lo_key": "machine_build_gap_min_m_v412", "group": "build", "authority": "v412", "enabled_key": "include_machine_build_authority_v412"},
    {"name": "Plant Sankey f_recirc", "value_key": "plant_v419_f_recirc", "sense": "<=", "limit_hi_key": "plant_sankey_f_recirc_max_v419", "group": "plant", "authority": "v419", "enabled_key": "include_plant_sankey_ledger_authority_v419"},
    {"name": "Plant Sankey Pe_net floor", "value_key": "plant_v419_Pe_net_MW", "sense": ">=", "limit_lo_key": "plant_sankey_Pe_net_min_MW_v419", "group": "plant", "authority": "v419", "enabled_key": "include_plant_sankey_ledger_authority_v419"},
    {"name": "Availability floor", "value_key": "avail_v420_availability", "sense": ">=", "limit_lo_key": "availability_min_v420", "group": "plant", "authority": "v420", "enabled_key": "include_availability_opex_lcoe_authority_v420"},
    {"name": "LCOE cap", "value_key": "avail_v420_LCOE_USD_per_MWh", "sense": "<=", "limit_hi_key": "lcoe_max_USD_per_MWh_v420", "group": "plant", "authority": "v420", "enabled_key": "include_availability_opex_lcoe_authority_v420"},
    {"name": "OPEX cap", "value_key": "avail_v420_OPEX_total_MUSD_per_y", "sense": "<=", "limit_hi_key": "opex_max_MUSD_per_y_v420", "group": "plant", "authority": "v420", "enabled_key": "include_availability_opex_lcoe_authority_v420"},
    {"name": "Total CAPEX cap", "value_key": "costing_v421_CAPEX_total_MUSD", "sense": "<=", "limit_hi_key": "capex_total_max_MUSD_v421", "group": "plant", "authority": "v421", "enabled_key": "include_bottom_up_costing_authority_v421"},
    {"name": "Bottom-up LCOE cap", "value_key": "costing_v421_LCOE_USD_per_MWh", "sense": "<=", "limit_hi_key": "lcoe_bottom_up_max_USD_per_MWh_v421", "group": "plant", "authority": "v421", "enabled_key": "include_bottom_up_costing_authority_v421"},
]
REGISTRY_SPEC_COUNT = 34
