from __future__ import annotations
from typing import List, Dict, Any
import pandas as pd

# PROCESS-style variable registry for auditability: name, units, meaning, and model/source file.
# Keep lightweight; expand as models mature.

VARIABLES: List[Dict[str, Any]] = [
    # Performance / confinement
    {"key":"Q_DT_eqv","units":"-","category":"Performance","meaning":"Fusion gain Q (DT-equivalent) computed from Pfus and auxiliary power definition.","source":"physics/hot_ion.py"},
    {"key":"Pfus_MW","units":"MW","category":"Performance","meaning":"Fusion power (DT-equivalent depending on fuel_mode).","source":"physics/hot_ion.py"},
    {"key":"ash_dilution_mode","units":"–","category":"Composition","meaning":"Helium-ash dilution mode ('off' or 'fixed_fraction').","source":"physics/hot_ion.py"},
    {"key":"f_He_ash","units":"–","category":"Composition","meaning":"Helium-ash fraction used by the optional ash dilution closure (0..1).","source":"physics/hot_ion.py"},
    {"key":"ash_factor","units":"–","category":"Composition","meaning":"Multiplicative ash dilution factor applied to Pfus_for_Q when ash_dilution_mode is enabled (=(1-f_He_ash)^2).","source":"physics/hot_ion.py"},
    {"key":"Paux_MW","units":"MW","category":"Performance","meaning":"Auxiliary heating power input (plasma).","source":"physics/hot_ion.py"},
    {"key":"Palpha_MW","units":"MW","category":"Performance","meaning":"Alpha heating power (DT-equivalent, after optional alpha_loss_frac).","source":"physics/hot_ion.py"},
    {"key":"alpha_loss_model","units":"–","category":"Fast particles","meaning":"Alpha prompt-loss model selector ('fixed' or 'rho_star').","source":"physics/hot_ion.py"},
    {"key":"alpha_loss_frac_eff","units":"–","category":"Fast particles","meaning":"Effective alpha-loss fraction actually applied to Palpha (after any enabled proxy model).","source":"physics/hot_ion.py"},
    {"key":"rho_star","units":"–","category":"Fast particles","meaning":"Normalized ion gyroradius proxy rho* used by the alpha prompt-loss proxy when enabled.","source":"physics/hot_ion.py"},
    {"key":"alpha_partition_model","units":"–","category":"Fast particles","meaning":"Alpha ion/electron partition model selector ('fixed' or 'Te_ratio').","source":"physics/hot_ion.py"},
    {"key":"f_alpha_to_ion_eff","units":"–","category":"Fast particles","meaning":"Effective alpha-to-ion fraction used for Palpha_i/Palpha_e reporting (after any enabled proxy).","source":"physics/hot_ion.py"},
    {"key":"Palpha_i_MW","units":"MW","category":"Power channels","meaning":"Alpha power deposited to ions (fraction f_alpha_to_ion).","source":"physics/hot_ion.py"},
    {"key":"Palpha_e_MW","units":"MW","category":"Power channels","meaning":"Alpha power deposited to electrons (1-f_alpha_to_ion).","source":"physics/hot_ion.py"},
    {"key":"Paux_i_MW","units":"MW","category":"Power channels","meaning":"Aux power deposited to ions (fraction f_aux_to_ion).","source":"physics/hot_ion.py"},
    {"key":"Paux_e_MW","units":"MW","category":"Power channels","meaning":"Aux power deposited to electrons (1-f_aux_to_ion).","source":"physics/hot_ion.py"},
    {"key":"P_ie_MW","units":"MW","category":"Power channels","meaning":"Ion→electron equilibration power (positive if Ti>Te). Diagnostic ledger term.","source":"physics/hot_ion.py"},
    {"key":"tau_ei_s","units":"s","category":"Power channels","meaning":"Ion-electron equilibration time proxy used for P_ie.","source":"physics/hot_ion.py"},
    {"key":"tauE_s","units":"s","category":"Confinement","meaning":"Energy confinement time inferred from W/Ploss (legacy).","source":"physics/hot_ion.py"},
    {"key":"tauE_eff_s","units":"s","category":"Confinement","meaning":"Effective tauE after optional transport stiffness degradation.","source":"physics/hot_ion.py"},
    {"key":"tauIPB98_s","units":"s","category":"Confinement","meaning":"IPB98(y,2) confinement scaling value.","source":"phase1_models.py"},
    {"key":"tauScaling_s","units":"s","category":"Confinement","meaning":"Selected confinement scaling time (IPB98y2 or ITER89P) for comparison.","source":"physics/hot_ion.py"},
    {"key":"H98","units":"-","category":"Confinement","meaning":"H-factor relative to IPB98(y,2): H98=tauE_eff/tauIPB98.","source":"physics/hot_ion.py"},
    {"key":"H_scaling","units":"-","category":"Confinement","meaning":"H-factor relative to selected confinement_scaling.","source":"physics/hot_ion.py"},
    {"key":"tau_p_s","units":"s","category":"Particles","meaning":"Particle confinement time proxy tau_p = tau_p_over_tauE * tauE_eff (when enabled).","source":"physics/hot_ion.py"},
    {"key":"S_fuel_required_1e22_per_s","units":"1e22/s","category":"Particles","meaning":"Required fueling source to sustain <n_e> given tau_p (proxy).","source":"physics/hot_ion.py"},
    {"key":"fueling_ok","units":"bool","category":"Particles","meaning":"Fueling sustainability flag if S_fuel_max_1e22_per_s is set (1=ok).","source":"physics/hot_ion.py"},

    # Composition / ash dilution (optional)
    {"key":"ash_dilution_mode","units":"–","category":"Composition","meaning":"Helium-ash dilution selector ('off' or 'fixed_fraction').","source":"physics/hot_ion.py"},
    {"key":"f_He_ash","units":"–","category":"Composition","meaning":"Helium ash fraction used by the ash dilution proxy (when enabled).","source":"physics/hot_ion.py"},
    {"key":"ash_factor","units":"–","category":"Composition","meaning":"Multiplicative fusion penalty applied when ash dilution is enabled: (1-f_He_ash)^2.","source":"physics/hot_ion.py"},

    # Heat exhaust
    {"key":"P_SOL_MW","units":"MW","category":"Heat exhaust","meaning":"Power crossing the separatrix (proxy).","source":"physics/hot_ion.py"},
    {"key":"lambda_q_mm","units":"mm","category":"Heat exhaust","meaning":"Eich-like heat-flux width proxy (lambda_q).","source":"phase1_models.py"},
    {"key":"q_div_MW_m2","units":"MW/m^2","category":"Heat exhaust","meaning":"Divertor peak heat flux proxy from P_div, lambda_q, and geometry factors.","source":"physics/divertor.py"},
    {"key":"P_SOL_over_R_MW_m","units":"MW/m","category":"Heat exhaust","meaning":"SOL loading proxy P_SOL/R0.","source":"physics/hot_ion.py"},
    {"key":"q_midplane_MW_m2","units":"MW/m^2","category":"Heat exhaust","meaning":"Midplane/SOL heat flux proxy using lambda_q and geometry.","source":"physics/hot_ion.py"},
    {"key":"q_div_W_m2","units":"W/m^2","category":"Heat exhaust","meaning":"Divertor peak heat flux proxy in W/m^2 (q_div_MW_m2×1e6).","source":"physics/hot_ion.py"},
    {"key":"q_div_max_W_m2","units":"W/m^2","category":"Heat exhaust","meaning":"Divertor peak heat flux limit in W/m^2 (q_div_max_MW_m2×1e6).","source":"physics/hot_ion.py"},
    {"key":"q_midplane_W_m2","units":"W/m^2","category":"Heat exhaust","meaning":"Midplane/SOL heat flux proxy in W/m^2 (q_midplane_MW_m2×1e6).","source":"physics/hot_ion.py"},
    {"key":"q_midplane_max_MW_m2","units":"MW/m^2","category":"Heat exhaust","meaning":"Optional midplane/SOL heat flux feasibility cap (NaN disables).","source":"models/inputs.py"},
    {"key":"div_regime","units":"-","category":"Heat exhaust","meaning":"Divertor regime label (attached/detached proxy).","source":"physics/divertor.py"},

    # Magnets / engineering
    {"key":"B_peak_T","units":"T","category":"Magnets","meaning":"Peak TF field on conductor proxy from radial build / geometry.","source":"phase1_systems.py"},
    {"key":"hts_margin","units":"-","category":"Magnets","meaning":"HTS operating margin proxy (>=1 is acceptable).","source":"engineering/tf_coil.py"},
    {"key":"sigma_vm_MPa","units":"MPa","category":"Magnets","meaning":"Von Mises stress proxy in TF structure.","source":"engineering/tf_coil.py"},

    # Neutronics
    {"key":"TBR","units":"-","category":"Neutronics","meaning":"Tritium breeding ratio proxy from blanket coverage and shield/blanket thickness.","source":"physics/neutronics.py"},
    {"key":"neutron_wall_load_MW_m2","units":"MW/m^2","category":"Neutronics","meaning":"Neutron wall loading proxy.","source":"physics/neutronics.py"},
    {"key":"lifetime_yr","units":"yr","category":"Neutronics","meaning":"HTS fast-neutron lifetime proxy (from fluence and shielding).","source":"physics/neutronics.py"},

    # Plant
    {"key":"P_e_net_MW","units":"MW(e)","category":"Plant","meaning":"Net electric power after recirculating loads.","source":"physics/plant.py"},
    {"key":"P_recirc_MW","units":"MW(e)","category":"Plant","meaning":"Total recirculating power demand (aux wallplug, cryo, pumps, CD, etc.).","source":"physics/plant.py"},

    # Profiles (optional diagnostics)
    {"key":"profile_meta","units":"-","category":"Profiles","meaning":"Metadata for analytic profile diagnostics (central values, pedestal parameters).","source":"physics/profiles.py"},
    {"key":"profile_grad_proxy","units":"-","category":"Profiles","meaning":"Edge gradient proxy used for bootstrap sensitivity (diagnostic).","source":"physics/profiles.py"},

# Economics (proxies)
{"key":"CAPEX_proxy_MUSD","units":"MUSD","category":"Economics","meaning":"CAPEX proxy (magnets+blanket+BOP+cryo). For relative comparisons.","source":"economics/cost.py"},
{"key":"OPEX_proxy_MUSD_per_y","units":"MUSD/y","category":"Economics","meaning":"OPEX proxy (recirc electricity + maintenance scaling).","source":"economics/cost.py"},
{"key":"COE_proxy_USD_per_MWh","units":"USD/MWh","category":"Economics","meaning":"Cost of electricity proxy: (FCR*CAPEX+OPEX)/E_net.","source":"economics/cost.py"},
{"key":"cost_magnet_MUSD","units":"MUSD","category":"Economics","meaning":"Magnet cost proxy scaling ~ B_peak^2 * coil volume.","source":"economics/cost.py"},
{"key":"cost_blanket_MUSD","units":"MUSD","category":"Economics","meaning":"Blanket/shield cost proxy scaling ~ vessel area * shield thickness.","source":"economics/cost.py"},
{"key":"cost_bop_MUSD","units":"MUSD","category":"Economics","meaning":"Balance-of-plant cost proxy scaling ~ thermal power.","source":"economics/cost.py"},
{"key":"cost_cryo_MUSD","units":"MUSD","category":"Economics","meaning":"Cryoplant CAPEX proxy scaling ~ MW@20K.","source":"economics/cost.py"},

# Heating / current drive
{"key":"P_cd_launch_MW","units":"MW","category":"Heating/CD","meaning":"Launched current drive power required to meet f_noninductive_target (proxy).","source":"physics/hot_ion.py"},
{"key":"P_cd_ECCD_MW","units":"MW","category":"Heating/CD","meaning":"Portion of launched P_cd assigned to ECCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"P_cd_LHCD_MW","units":"MW","category":"Heating/CD","meaning":"Portion of launched P_cd assigned to LHCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"P_cd_NBI_MW","units":"MW","category":"Heating/CD","meaning":"Portion of launched P_cd assigned to NBI (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"P_cd_ICRF_MW","units":"MW","category":"Heating/CD","meaning":"Portion of launched P_cd assigned to ICRF/FWCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"I_cd_ECCD_MA","units":"MA","category":"Heating/CD","meaning":"Externally driven current from ECCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"I_cd_LHCD_MA","units":"MA","category":"Heating/CD","meaning":"Externally driven current from LHCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"I_cd_NBI_MA","units":"MA","category":"Heating/CD","meaning":"Externally driven current from NBI (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"I_cd_ICRF_MA","units":"MA","category":"Heating/CD","meaning":"Externally driven current from ICRF/FWCD (v395 mix bookkeeping).","source":"physics/hot_ion.py"},
{"key":"I_cd_MA","units":"MA","category":"Heating/CD","meaning":"Driven current corresponding to P_cd_launch_MW using gamma_cd.","source":"physics/hot_ion.py"},
{"key":"f_noninductive","units":"-","category":"Heating/CD","meaning":"Non-inductive fraction f_bs + I_cd/Ip (proxy).","source":"physics/hot_ion.py"},

# Pulsed operation
{"key":"t_flat_s","units":"s","category":"Pulsed","meaning":"Flat-top duration estimate from flux swing and loop voltage proxy.","source":"physics/hot_ion.py"},
{"key":"cycles_per_year","units":"1/y","category":"Pulsed","meaning":"Cycle count per year from (t_flat+t_dwell) and availability.","source":"physics/hot_ion.py"},
]

def registry_dataframe(filter_text: str = "") -> pd.DataFrame:
    df = pd.DataFrame(VARIABLES)
    if filter_text:
        t = filter_text.lower().strip()
        mask = df.apply(lambda r: any(t in str(r[c]).lower() for c in df.columns), axis=1)
        df = df[mask]
    return df.sort_values(["category","key"]).reset_index(drop=True)
