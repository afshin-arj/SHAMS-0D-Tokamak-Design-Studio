
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class MagnetPackResult:
    Jop_MA_per_mm2: float
    Jop_limit_MA_per_mm2: float
    Jop_margin: float
    stress_MPa: float
    stress_allow_MPa: float
    stress_margin: float
    cryo_power_MW: float

def magnet_pack_proxy(out: Dict[str, float], inp: object) -> MagnetPackResult:
    """Lightweight PROCESS-inspired TF magnet proxy.

    Transparent proxy (not a detailed FEM model). Purpose:
    - Connect field requirement to current density and stress margin
    - Provide a cryo power estimate that impacts net electric & economics

    Inputs (optional, read via getattr with defaults):
    - tf_Jop_MA_per_mm2 (operating current density)
    - tf_Jop_limit_MA_per_mm2 (limit)
    - tf_stress_allow_MPa (allowable)
    - tf_struct_factor (stress scaling factor)
    - cryo_W_per_W (cryogenic plant penalty factor)

    Output uses out['Bt_T'], out['R0_m'] if available; falls back to inp.
    """
    Bt = float(out.get("Bt_T", getattr(inp, "Bt_T", 5.0)))
    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
    # Peak field proxy: map B0 to inner leg using 1/R scaling with an explicit factor.
    R_inner = float(out.get("R_coil_inner_m", 0.0) or getattr(inp, "R_coil_inner_m", 0.0) or 0.0)
    if not (R_inner > 0.0):
        R_inner = 0.5 * R0
    Bpeak_factor = float(getattr(inp, "Bpeak_factor", 1.25) or 1.25)
    Bpeak = Bpeak_factor * Bt * (R0 / max(R_inner, 1e-6))
    # Expose for downstream authority bundles (deterministic transparency)
    out["B_peak_T"] = float(Bpeak)
    out["R_coil_inner_m"] = float(R_inner)

    struct_factor = float(getattr(inp, "tf_struct_factor", 1.0))
    # Stress proxy (thin-shell hoop): sigma ~ p_mag * R / t, p_mag = B^2/(2*mu0).
    MU0 = 4e-7 * 3.141592653589793
    Jop_input = float(getattr(inp, "tf_Jop_MA_per_mm2", 55.0e-3))  # 55 A/mm2 -> 0.055 MA/mm^2
    use_geom = bool(getattr(inp, "tf_Jop_from_wp_geometry", False))
    tf_wp_width_m = float(getattr(inp, "tf_wp_width_m", 0.25) or 0.25)
    tf_wp_height_factor = float(getattr(inp, "tf_wp_height_factor", 2.4) or 2.4)
    tf_wp_fill_factor = float(getattr(inp, "tf_wp_fill_factor", 1.0) or 1.0)
    # Winding-pack height proxy: factor * (a*kappa). Uses plasma shaping inputs (transparent 0-D proxy).
    a_m = float(getattr(inp, "a_m", out.get("a_m", 1.0) or 1.0))
    kappa = float(getattr(inp, "kappa", out.get("kappa", 1.7) or 1.7))
    tf_wp_height_m = tf_wp_height_factor * max(a_m, 1e-6) * max(kappa, 1e-6)
    tf_wp_area_m2 = max(tf_wp_width_m, 1e-6) * max(tf_wp_height_m, 1e-6) * max(tf_wp_fill_factor, 1e-6)
    tf_wp_area_mm2 = tf_wp_area_m2 * 1e6
    # Required ampere-turns for on-axis Bt: Bt(R0) ≈ mu0*(N*I)/(2πR0) => N*I = 2πR0 Bt / mu0
    NI_A = (2.0 * 3.141592653589793 * R0 * Bt) / MU0
    Jop_geom_A_per_mm2 = NI_A / max(tf_wp_area_mm2, 1e-12)
    Jop_geom_MA_per_mm2 = Jop_geom_A_per_mm2 / 1e6
    N_tf_turns = float(getattr(inp, "N_tf_turns", 1) or 1)
    I_turn_A = NI_A / max(N_tf_turns, 1.0)
    I_turn_MA = I_turn_A / 1e6
    # Choose Jop source
    Jop = Jop_geom_MA_per_mm2 if use_geom else Jop_input
    out["tf_Jop_source"] = "winding_pack_geometry" if use_geom else "input"
    out["tf_wp_area_mm2"] = float(tf_wp_area_mm2)
    out["tf_wp_height_m"] = float(tf_wp_height_m)
    out["tf_ampere_turns_MAturn"] = float(NI_A/1e6)
    out["tf_I_turn_MA"] = float(I_turn_MA)
    out["tf_Jop_geom_MA_per_mm2"] = float(Jop_geom_MA_per_mm2)
    out["tf_Jop_input_MA_per_mm2"] = float(Jop_input)
    Jlim = float(getattr(inp, "tf_Jop_limit_MA_per_mm2", 75.0e-3))
    t_struct = float(getattr(inp, "t_tf_struct_m", 0.15) or 0.15)
    p_mag_Pa = (Bpeak * Bpeak) / (2.0 * MU0)
    stress = struct_factor * (p_mag_Pa * max(R_inner, 1e-6) / max(t_struct, 1e-6)) / 1e6
    stress_allow = float(getattr(inp, "tf_stress_allow_MPa", 900.0))

    # Cryo proxy: cryo power scales with coil losses ~ J^2 * volume; use field and R0
    cryo_W_per_W = float(getattr(inp, "cryo_W_per_W", 250.0))
    # proxy electrical losses MW (arbitrary but monotonic)
    coil_loss_MW = 0.06 * (Jop / 0.055)**2 * (Bpeak / 7.0)**2 * (R0 / 6.2)
    cryo_power_MW = coil_loss_MW * cryo_W_per_W / 1000.0

    return MagnetPackResult(
        Jop_MA_per_mm2=Jop,
        Jop_limit_MA_per_mm2=Jlim,
        Jop_margin=Jlim - Jop,
        stress_MPa=stress,
        stress_allow_MPa=stress_allow,
        stress_margin=stress_allow - stress,
        cryo_power_MW=cryo_power_MW,
    )
