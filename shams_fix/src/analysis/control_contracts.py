from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List

from physics.mhd_rwm import compute_rwm_screening


def _f(out: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(out.get(key, default))
    except Exception:
        return default


def _get(inp: Any, key: str, default: Any) -> Any:
    try:
        return getattr(inp, key, default)
    except Exception:
        return default


@dataclass(frozen=True)
class ControlContracts:
    # Vertical stability / control requirements
    gamma_VS_s_inv: float
    tau_VS_s: float
    vs_bandwidth_req_Hz: float
    vs_control_power_req_MW: float
    vs_control_ok: float  # 1/0/NaN

    # PF waveform envelope (canonical ramp–flat–ramp)
    pf_I_peak_MA: float
    pf_dIdt_peak_MA_s: float
    pf_V_peak_V: float
    pf_P_peak_MW: float
    pf_E_pulse_MJ: float
    pf_waveform_decimated: List[Dict[str, float]]
    pf_envelope_ok: float  # 1/0/NaN

    # SOL radiative control envelope
    f_rad_SOL_required: float
    f_rad_SOL_max: float
    sol_control_ok: float  # 1/0/NaN

    # RWM screening (v229.0) — MHD/control coupling
    rwm_regime: str
    rwm_betaN_no_wall: float
    rwm_betaN_ideal_wall: float
    rwm_chi: float
    rwm_tau_w_s: float
    rwm_gamma_s_inv: float
    rwm_bandwidth_req_Hz: float
    rwm_control_power_req_MW: float
    rwm_control_ok: float  # 1/0/NaN

    # Authority + budgeting (v227.0)
    control_contracts_authority: Dict[str, str]
    control_budget_ledger: Dict[str, float]
    # v228.0: explicit signed margins for optional caps (positive=within)
    contract_margins: Dict[str, float]
    contract_caps: Dict[str, float]


def compute_control_contracts(out: Dict[str, Any], inp: Any, caps_override: Dict[str, float] | None = None) -> ControlContracts:
    """Compute envelope-based control contracts.

    This is a *read-only* post-processing layer. It does not modify the evaluated
    plasma/plant state; it only computes required actuator envelopes and checks
    optional caps when present.
    """

    enabled = bool(_get(inp, "include_control_contracts", False))
    if not enabled:
        return ControlContracts(
            gamma_VS_s_inv=float("nan"),
            tau_VS_s=float("nan"),
            vs_bandwidth_req_Hz=float("nan"),
            vs_control_power_req_MW=float("nan"),
            vs_control_ok=float("nan"),
            pf_I_peak_MA=float("nan"),
            pf_dIdt_peak_MA_s=float("nan"),
            pf_V_peak_V=float("nan"),
            pf_P_peak_MW=float("nan"),
            pf_E_pulse_MJ=float("nan"),
            pf_waveform_decimated=[],
            pf_envelope_ok=float("nan"),
            f_rad_SOL_required=float(out.get("f_rad_SOL_required", float("nan"))),
            f_rad_SOL_max=float(_get(inp, "f_rad_SOL_max", float("nan"))),
            sol_control_ok=float("nan"),

            rwm_regime="UNAVAILABLE",
            rwm_betaN_no_wall=float("nan"),
            rwm_betaN_ideal_wall=float("nan"),
            rwm_chi=float("nan"),
            rwm_tau_w_s=float("nan"),
            rwm_gamma_s_inv=float("nan"),
            rwm_bandwidth_req_Hz=float("nan"),
            rwm_control_power_req_MW=float("nan"),
            rwm_control_ok=float("nan"),

            control_contracts_authority={"vs": "disabled", "pf": "disabled", "sol": "disabled"},
            control_budget_ledger={},
            contract_margins={},
            contract_caps={},
        )

    caps_override = caps_override or {}

    def _cap(key: str, default: float = float('nan')) -> float:
        """Return cap value from inputs when finite, else from caps_override, else default."""
        v = _get(inp, key, float('nan'))
        try:
            v = float(v)
        except Exception:
            v = float('nan')
        if math.isfinite(v):
            return float(v)
        v2 = caps_override.get(key, float('nan'))
        try:
            v2 = float(v2)
        except Exception:
            v2 = float('nan')
        if math.isfinite(v2):
            return float(v2)
        return float(default)

    # -----------------------------
    # Vertical stability: growth-rate + bandwidth requirement
    # -----------------------------
    vs_margin = float(_f(out, "vs_margin", float("nan")))
    vs_margin = vs_margin if math.isfinite(vs_margin) else float("nan")

    tau_nom = float(_cap("vs_tau_nominal_s", 0.30))
    tau_nom = max(tau_nom, 0.02)

    # Map margin -> timescale (bounded). Small margin => fast growth.
    if math.isfinite(vs_margin):
        m = max(min(vs_margin, 1.0), 0.0)
        # 1/m behavior with floor/ceiling to avoid absurd numbers
        tau_vs = tau_nom / max(m, 0.05)
        tau_vs = max(min(tau_vs, 10.0), 0.02)
    else:
        tau_vs = float("nan")

    gamma_vs = (1.0 / tau_vs) if math.isfinite(tau_vs) else float("nan")
    bw_factor = float(_cap("vs_bw_factor", 3.0))
    bw_factor = max(bw_factor, 1.0)
    bw_req = (bw_factor * gamma_vs / (2.0 * math.pi)) if math.isfinite(gamma_vs) else float("nan")

    # Control power requirement uses PF energy proxy.
    # Estimate an effective inductance from required CS flux when available:
    #   L_eff ≈ Ψ_req / I  (Ψ in Wb, I in A)
    I_pf_MA = float(_f(out, "pf_I_pf_MA", float("nan")))
    I_pf_A = I_pf_MA * 1e6 if math.isfinite(I_pf_MA) else float("nan")
    psi_req = float(_f(out, "cs_flux_required_Wb", float("nan")))
    L_eff = float(_cap("pf_L_eff_H"))
    if not math.isfinite(L_eff):
        if math.isfinite(psi_req) and math.isfinite(I_pf_A) and I_pf_A > 0:
            L_eff = max(psi_req / I_pf_A, 1e-7)
        else:
            L_eff = 1e-5  # conservative default, but bounded
    L_eff = max(L_eff, 1e-7)

    # PF stored energy proxy
    if math.isfinite(I_pf_A):
        W_pf_J = 0.5 * L_eff * (I_pf_A ** 2)
        W_pf_MJ = W_pf_J / 1e6
    else:
        W_pf_MJ = float("nan")

    margin_factor = float(_cap("vs_control_margin_factor", 1.3))
    margin_factor = max(margin_factor, 1.0)
    P_vs_req = (margin_factor * W_pf_MJ / tau_vs) if (math.isfinite(W_pf_MJ) and math.isfinite(tau_vs)) else float("nan")
    P_vs_req = float(P_vs_req) if math.isfinite(P_vs_req) else float("nan")

    vs_bw_max = float(_cap("vs_bandwidth_max_Hz"))
    vs_Pmax = float(_cap("vs_control_power_max_MW"))
    vs_ok = float("nan")
    if math.isfinite(bw_req) or math.isfinite(P_vs_req):
        ok = True
        if math.isfinite(vs_bw_max) and math.isfinite(bw_req):
            ok = ok and (bw_req <= vs_bw_max)
        if math.isfinite(vs_Pmax) and math.isfinite(P_vs_req):
            ok = ok and (P_vs_req <= vs_Pmax)
        vs_ok = 1.0 if ok else 0.0

    # -----------------------------
    # PF waveform envelope: ramp–flat–ramp
    # -----------------------------
    ramp_s = float(_cap("pf_ramp_s", float(_get(inp, "pulse_ramp_s", 300.0))))
    ramp_s = max(ramp_s, 1.0)
    flat_s = float(_get(inp, "pf_flat_s", float(_f(out, "t_flat_s", float(_get(inp, "t_burn_s", 7200.0))))))
    flat_s = max(flat_s, 0.0)
    R_eff = float(_cap("pf_R_eff_Ohm", 1e-4))
    R_eff = max(R_eff, 0.0)

    if math.isfinite(I_pf_MA):
        dIdt_MA_s = I_pf_MA / ramp_s
        dIdt_A_s = dIdt_MA_s * 1e6
        V_peak = L_eff * dIdt_A_s + R_eff * I_pf_A
        # peak power (use V at end-of-ramp and flat)
        P_peak_W = V_peak * I_pf_A if math.isfinite(V_peak) and math.isfinite(I_pf_A) else float("nan")
        P_peak_MW = P_peak_W / 1e6 if math.isfinite(P_peak_W) else float("nan")
        # pulse energy: ramp up + flat (approx) + ramp down
        # Ramp energy ~ ∫ V I dt ≈ 0.5*L*I^2 + 0.5*R*I^2*ramp
        E_ramp_J = 0.5 * L_eff * (I_pf_A ** 2) + 0.5 * R_eff * (I_pf_A ** 2) * ramp_s
        # Flat energy ~ R*I^2*flat
        E_flat_J = R_eff * (I_pf_A ** 2) * flat_s
        E_pulse_MJ = (2.0 * E_ramp_J + E_flat_J) / 1e6
    else:
        dIdt_MA_s = V_peak = P_peak_MW = E_pulse_MJ = float("nan")

    # Decimated canonical waveform table (0..ramp..ramp+flat..end)
    wf: List[Dict[str, float]] = []
    if math.isfinite(I_pf_MA):
        # 9 points total: 0, 25%, 50%, 75%, 100% ramp; mid-flat; end-flat; 50% down; end
        t0 = 0.0
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            t = ramp_s * frac
            I = I_pf_MA * frac
            wf.append({"t_s": float(t0 + t), "I_MA": float(I)})
        if flat_s > 0.0:
            wf.append({"t_s": float(ramp_s + 0.5 * flat_s), "I_MA": float(I_pf_MA)})
            wf.append({"t_s": float(ramp_s + flat_s), "I_MA": float(I_pf_MA)})
        # ramp down
        t_start = ramp_s + flat_s
        for frac in [0.5, 1.0]:
            t = ramp_s * frac
            I = I_pf_MA * (1.0 - frac)
            wf.append({"t_s": float(t_start + t), "I_MA": float(I)})

    # PF envelope feasibility (optional caps)
    I_max = float(_cap("pf_I_peak_max_MA"))
    V_max = float(_cap("pf_V_peak_max_V"))
    P_max = float(_cap("pf_P_peak_max_MW"))
    dIdt_max = float(_cap("pf_dIdt_max_MA_s"))
    E_max = float(_cap("pf_E_pulse_max_MJ"))

    env_ok = float("nan")
    if math.isfinite(I_pf_MA) or math.isfinite(V_peak) or math.isfinite(P_peak_MW):
        ok = True
        if math.isfinite(I_max) and math.isfinite(I_pf_MA):
            ok = ok and (I_pf_MA <= I_max)
        if math.isfinite(V_max) and math.isfinite(V_peak):
            ok = ok and (V_peak <= V_max)
        if math.isfinite(P_max) and math.isfinite(P_peak_MW):
            ok = ok and (P_peak_MW <= P_max)
        if math.isfinite(dIdt_max) and math.isfinite(dIdt_MA_s):
            ok = ok and (dIdt_MA_s <= dIdt_max)
        if math.isfinite(E_max) and math.isfinite(E_pulse_MJ):
            ok = ok and (E_pulse_MJ <= E_max)
        env_ok = 1.0 if ok else 0.0

    # -----------------------------
    # SOL radiative control envelope (already computed elsewhere)
    # -----------------------------
    f_req = float(_f(out, "f_rad_SOL_required", float("nan")))
    f_max = float(_get(inp, "f_rad_SOL_max", float("nan")))
    sol_ok = float("nan")
    if bool(_get(inp, "include_sol_radiation_control", False)) and math.isfinite(f_req):
        if math.isfinite(f_max):
            sol_ok = 1.0 if (f_req <= f_max) else 0.0
        else:
            sol_ok = float("nan")

    # -----------------------------
    # RWM screening (v229.0) — deterministic coupling to control caps
    # -----------------------------
    rwm = compute_rwm_screening(out, inp)
    rwm_bw_max = float(_get(inp, "rwm_bandwidth_max_Hz", float(_get(inp, "vs_bandwidth_max_Hz", float("nan")))))
    rwm_Pmax = float(_get(inp, "rwm_control_power_max_MW", float(_get(inp, "vs_control_power_max_MW", float("nan")))))

    rwm_ok = float("nan")
    if rwm.regime in ("RWM_ACTIVE", "IDEAL_WALL_EXCEEDED"):
        ok = True
        if rwm.regime == "IDEAL_WALL_EXCEEDED":
            ok = False
        if math.isfinite(rwm_bw_max) and math.isfinite(rwm.f_req_Hz):
            ok = ok and (rwm.f_req_Hz <= rwm_bw_max)
        if math.isfinite(rwm_Pmax) and math.isfinite(rwm.P_req_MW):
            ok = ok and (rwm.P_req_MW <= rwm_Pmax)
        rwm_ok = 1.0 if ok else 0.0


    # -----------------------------
    # Authority tags + control budget ledger (v227.0)
    # -----------------------------
    authority: Dict[str, str] = {}
    authority["vs"] = "proxy" if math.isfinite(vs_margin) else "proxy_missing"
    L_inferred = not math.isfinite(float(_get(inp, "pf_L_eff_H", float("nan"))))
    authority["pf"] = "proxy_inferred" if L_inferred else "proxy_input"
    authority["sol"] = "diagnostic_proxy" if bool(_get(inp, "include_sol_radiation_control", False)) else "disabled"
    authority["rwm"] = str((rwm.authority or {}).get("rwm", "proxy")) if bool(_get(inp, "include_rwm_screening", False)) else "disabled"

    t_cycle_s = float(2.0 * ramp_s + flat_s) if (math.isfinite(ramp_s) and math.isfinite(flat_s)) else float("nan")
    P_pf_avg_MW = (E_pulse_MJ / t_cycle_s) if (math.isfinite(E_pulse_MJ) and math.isfinite(t_cycle_s) and t_cycle_s > 0) else float("nan")
    vs_horizon_s = float(_get(inp, "vs_control_horizon_s", 1.0))
    vs_horizon_s = max(vs_horizon_s, 0.1)
    E_vs_MJ = (P_vs_req * vs_horizon_s) if (math.isfinite(P_vs_req)) else float("nan")
    P_vs_avg_MW = (E_vs_MJ / t_cycle_s) if (math.isfinite(E_vs_MJ) and math.isfinite(t_cycle_s) and t_cycle_s > 0) else float("nan")

    def _nansum(vals: List[float]) -> float:
        s = 0.0
        anyf = False
        for v in vals:
            if math.isfinite(v):
                s += float(v)
                anyf = True
        return s if anyf else float("nan")

    budget: Dict[str, float] = {
        "t_cycle_s": float(t_cycle_s) if math.isfinite(t_cycle_s) else float("nan"),
        "pf_P_peak_MW": float(P_peak_MW) if math.isfinite(P_peak_MW) else float("nan"),
        "pf_P_avg_MW": float(P_pf_avg_MW) if math.isfinite(P_pf_avg_MW) else float("nan"),
        "pf_E_pulse_MJ": float(E_pulse_MJ) if math.isfinite(E_pulse_MJ) else float("nan"),
        "vs_P_peak_MW": float(P_vs_req) if math.isfinite(P_vs_req) else float("nan"),
        "vs_E_horizon_MJ": float(E_vs_MJ) if math.isfinite(E_vs_MJ) else float("nan"),
        "vs_P_avg_MW": float(P_vs_avg_MW) if math.isfinite(P_vs_avg_MW) else float("nan"),
        "control_P_peak_MW": float(_nansum([P_peak_MW, P_vs_req])),
        "control_P_avg_MW": float(_nansum([P_pf_avg_MW, P_vs_avg_MW])),
        "rwm_bandwidth_req_Hz": float(rwm.f_req_Hz) if math.isfinite(rwm.f_req_Hz) else float("nan"),
        "rwm_control_power_req_MW": float(rwm.P_req_MW) if math.isfinite(rwm.P_req_MW) else float("nan"),
    }

    # -----------------------------
    # Cap margins (v228.0)
    # -----------------------------
    caps: Dict[str, float] = {
        "vs_bandwidth_max_Hz": float(_get(inp, "vs_bandwidth_max_Hz", float("nan"))),
        "vs_control_power_max_MW": float(_get(inp, "vs_control_power_max_MW", float("nan"))),
        "pf_I_peak_max_MA": float(_get(inp, "pf_I_peak_max_MA", float("nan"))),
        "pf_dIdt_max_MA_s": float(_get(inp, "pf_dIdt_max_MA_s", float("nan"))),
        "pf_V_peak_max_V": float(_get(inp, "pf_V_peak_max_V", float("nan"))),
        "pf_P_peak_max_MW": float(_get(inp, "pf_P_peak_max_MW", float("nan"))),
        "pf_E_pulse_max_MJ": float(_get(inp, "pf_E_pulse_max_MJ", float("nan"))),
        "f_rad_SOL_max": float(_get(inp, "f_rad_SOL_max", float("nan"))),
        "rwm_bandwidth_max_Hz": float(rwm_bw_max),
        "rwm_control_power_max_MW": float(rwm_Pmax),
    }
    margins: Dict[str, float] = {}

    def _margin(cap: float, req: float) -> float:
        if math.isfinite(cap) and math.isfinite(req):
            return float(cap - req)
        return float("nan")

    margins["vs_bandwidth_margin_Hz"] = _margin(caps["vs_bandwidth_max_Hz"], bw_req)
    margins["vs_control_power_margin_MW"] = _margin(caps["vs_control_power_max_MW"], P_vs_req)
    margins["pf_I_peak_margin_MA"] = _margin(caps["pf_I_peak_max_MA"], I_pf_MA)
    margins["pf_dIdt_margin_MA_s"] = _margin(caps["pf_dIdt_max_MA_s"], dIdt_MA_s)
    margins["pf_V_peak_margin_V"] = _margin(caps["pf_V_peak_max_V"], V_peak)
    margins["pf_P_peak_margin_MW"] = _margin(caps["pf_P_peak_max_MW"], P_peak_MW)
    margins["pf_E_pulse_margin_MJ"] = _margin(caps["pf_E_pulse_max_MJ"], E_pulse_MJ)
    margins["f_rad_SOL_margin"] = _margin(caps["f_rad_SOL_max"], f_req)
    margins["rwm_bandwidth_margin_Hz"] = _margin(caps["rwm_bandwidth_max_Hz"], rwm.f_req_Hz)
    margins["rwm_control_power_margin_MW"] = _margin(caps["rwm_control_power_max_MW"], rwm.P_req_MW)
    return ControlContracts(
        gamma_VS_s_inv=float(gamma_vs),
        tau_VS_s=float(tau_vs),
        vs_bandwidth_req_Hz=float(bw_req),
        vs_control_power_req_MW=float(P_vs_req),
        vs_control_ok=float(vs_ok),
        pf_I_peak_MA=float(I_pf_MA),
        pf_dIdt_peak_MA_s=float(dIdt_MA_s),
        pf_V_peak_V=float(V_peak),
        pf_P_peak_MW=float(P_peak_MW),
        pf_E_pulse_MJ=float(E_pulse_MJ),
        pf_waveform_decimated=wf,
        pf_envelope_ok=float(env_ok),
        f_rad_SOL_required=float(f_req),
        f_rad_SOL_max=float(f_max),
        sol_control_ok=float(sol_ok),

        rwm_regime=str(rwm.regime),
        rwm_betaN_no_wall=float(rwm.betaN_NW),
        rwm_betaN_ideal_wall=float(rwm.betaN_IW),
        rwm_chi=float(rwm.chi),
        rwm_tau_w_s=float(rwm.tau_w_s),
        rwm_gamma_s_inv=float(rwm.gamma_rwm_s_inv),
        rwm_bandwidth_req_Hz=float(rwm.f_req_Hz),
        rwm_control_power_req_MW=float(rwm.P_req_MW),
        rwm_control_ok=float(rwm_ok),

        control_contracts_authority=authority,
        control_budget_ledger=budget,
        contract_margins=margins,
        contract_caps=caps,
    )
