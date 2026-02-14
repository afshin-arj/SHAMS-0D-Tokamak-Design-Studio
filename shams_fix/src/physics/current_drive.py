from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class CurrentDriveModelResult:
    model: str
    actuator: str
    gamma_A_per_W: float  # A/W
    eta_wallplug: float


def cd_gamma_and_efficiency(out: Dict[str, float], inp: object) -> CurrentDriveModelResult:
    """Return current-drive efficiency proxies (deterministic).

    This function provides a *minimal* but higher-credibility alternative to a fixed gamma_cd_A_per_W:
    - fixed_gamma (legacy): gamma = inp.gamma_cd_A_per_W
    - actuator_scaling: gamma scales with (Te / (ne * R0)) with actuator-specific baselines.

    The goal is trend correctness and auditability, not predictive ECCD/LHCD physics.

    Units
    -----
    - gamma: A/W
    - Te in keV, ne in 1e20 m^-3, R0 in m
    """
    model = str(getattr(inp, "cd_model", "fixed_gamma") or "fixed_gamma").strip().lower()
    actuator = str(getattr(inp, "cd_actuator", "ECCD") or "ECCD").strip().upper()
    eta = float(getattr(inp, "eta_cd_wallplug", 0.35))

    # Legacy fixed gamma
    if model in ("fixed", "fixed_gamma", "legacy"):
        gamma = float(getattr(inp, "gamma_cd_A_per_W", 0.05))
        return CurrentDriveModelResult(model="fixed_gamma", actuator=actuator, gamma_A_per_W=max(gamma, 1e-6), eta_wallplug=max(eta, 1e-6))


    # v357 channel library (actuator-specific trend scalings + declared knobs)
    if model in ("channel_library_v357", "cd_library_v357", "v357"):
        # Base trend variables
        Te_keV = float(out.get("Te_keV", out.get("Te0_keV", getattr(inp, "Ti_keV", 10.0) / max(getattr(inp, "Ti_over_Te", 2.0), 1e-6))))
        ne20 = float(out.get("ne20", out.get("ne_1e20_m3", out.get("nbar20", out.get("n_e_1e20", float(getattr(inp, "fG", 0.8)))))))
        if "ne_bar_1e20_m3" in out:
            ne20 = float(out["ne_bar_1e20_m3"])
        R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
        B0 = float(out.get("Bt_T", out.get("B0_T", getattr(inp, "Bt_T", 5.3))))

        # Guardrails
        Te_keV = max(0.2, min(50.0, Te_keV))
        ne20 = max(0.05, min(5.0, ne20))
        R0 = max(0.5, min(20.0, R0))
        B0 = max(0.5, min(25.0, B0))

        # Common core trend
        core = (Te_keV / 10.0) / (ne20 * (R0 / 6.0))

        if actuator == "ECCD":
            lf = float(getattr(inp, "eccd_launch_factor", 1.0))
            lf = max(0.2, min(2.0, lf))
            gamma = 0.05 * core * (B0 / 5.0) ** 0.5 * lf
        elif actuator == "LHCD":
            npar = float(getattr(inp, "lhcd_n_parallel", 1.8))
            npar = max(1.0, min(4.0, npar))
            # accessibility / phase-velocity trend: higher n|| reduces efficiency
            gamma = 0.09 * core * (2.0 / npar) ** 1.5
        elif actuator == "NBI":
            E = float(getattr(inp, "nbi_beam_energy_keV", 500.0))
            E = max(50.0, min(5000.0, E))
            gamma = 0.03 * core * (E / 500.0) ** 0.5
        else:  # ICRF/FWCD or unknown -> proxy-only
            gamma = 0.02 * core

        gamma = max(1e-4, min(0.2, gamma))
        return CurrentDriveModelResult(model="channel_library_v357", actuator=actuator, gamma_A_per_W=gamma, eta_wallplug=max(eta, 1e-6))

    # Actuator scaling: gamma ~ gamma0 * (Te/10) / (ne20 * (R0/6))
    # Baselines chosen to be monotone and in the right *order* (LHCD > ECCD > NBI) for typical regimes.
    gamma0_map = {
        "LHCD": 0.08,
        "ECCD": 0.05,
        "NBI": 0.03,
        "ICRF": 0.02,
    }
    gamma0 = float(gamma0_map.get(actuator, 0.05))

    Te_keV = float(out.get("Te_keV", out.get("Te0_keV", getattr(inp, "Ti_keV", 10.0) / max(getattr(inp, "Ti_over_Te", 2.0), 1e-6))))
    ne20 = float(out.get("ne20", out.get("ne_1e20_m3", out.get("nbar20", out.get("n_e_1e20", float(getattr(inp, "fG", 0.8)))))))
    # Use the explicit volume-average density if available
    if "ne_bar_1e20_m3" in out:
        ne20 = float(out["ne_bar_1e20_m3"])
    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))

    # Guardrails (avoid nonsense when using partial outputs)
    Te_keV = max(0.2, min(50.0, Te_keV))
    ne20 = max(0.05, min(5.0, ne20))
    R0 = max(0.5, min(20.0, R0))

    gamma = gamma0 * (Te_keV / 10.0) / (ne20 * (R0 / 6.0))
    # Bound to keep solver stable and reviewer-safe
    gamma = max(1e-4, min(0.2, gamma))

    return CurrentDriveModelResult(model="actuator_scaling", actuator=actuator, gamma_A_per_W=gamma, eta_wallplug=max(eta, 1e-6))
