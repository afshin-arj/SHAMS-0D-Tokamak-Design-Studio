from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CurrentDriveModelResult:
    model: str
    actuator: str
    gamma_A_per_W: float  # A/W
    eta_wallplug: float
    # Optional per-channel breakdown (v395 multi-channel library)
    channels: Optional[Dict[str, Dict[str, Any]]] = None


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


    # v395 multi-channel library (mix of ECCD/LHCD/NBI/ICRF)
    if model in ("channel_library_v395", "cd_library_v395", "v395"):
        Te_keV = float(out.get("Te_keV", out.get("Te0_keV", getattr(inp, "Ti_keV", 10.0) / max(getattr(inp, "Ti_over_Te", 2.0), 1e-6))))
        ne20 = float(out.get("ne20", out.get("ne_1e20_m3", out.get("nbar20", out.get("n_e_1e20", float(getattr(inp, "fG", 0.8)))))))
        if "ne_bar_1e20_m3" in out:
            ne20 = float(out["ne_bar_1e20_m3"])
        R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
        B0 = float(out.get("Bt_T", out.get("B0_T", getattr(inp, "Bt_T", 5.3))))

        Te_keV = max(0.2, min(50.0, Te_keV))
        ne20 = max(0.05, min(5.0, ne20))
        R0 = max(0.5, min(20.0, R0))
        B0 = max(0.5, min(25.0, B0))

        mix_enable = bool(getattr(inp, "cd_mix_enable", False))
        if not mix_enable:
            # If the mix is not enabled, fall back to the existing v357 single-actuator library
            model = "channel_library_v357"
        else:
            f_eccd = max(0.0, float(getattr(inp, "cd_mix_frac_eccd", 1.0)))
            f_lhcd = max(0.0, float(getattr(inp, "cd_mix_frac_lhcd", 0.0)))
            f_nbi = max(0.0, float(getattr(inp, "cd_mix_frac_nbi", 0.0)))
            f_icrf = max(0.0, float(getattr(inp, "cd_mix_frac_icrf", 0.0)))
            s = f_eccd + f_lhcd + f_nbi + f_icrf
            if s <= 0.0:
                f_eccd, s = 1.0, 1.0
            f_eccd /= s; f_lhcd /= s; f_nbi /= s; f_icrf /= s

            core = (Te_keV / 10.0) / (ne20 * (R0 / 6.0))

            # ECCD
            lf = max(0.2, min(2.0, float(getattr(inp, "eccd_launch_factor", 1.0))))
            gamma_eccd = 0.05 * core * (B0 / 5.0) ** 0.6 * lf
            # Conservative launcher power-density penalty if a cap is declared
            Pdens_max = float(getattr(inp, "eccd_launcher_power_density_max_MW_m2", float("nan")))
            if math.isfinite(Pdens_max) and Pdens_max > 0.0:
                gamma_eccd *= 0.85

            # LHCD
            npar = max(1.0, min(4.0, float(getattr(inp, "lhcd_n_parallel", 1.8))))
            gamma_lhcd = 0.10 * core * (2.0 / npar) ** 1.6
            lh_lim = 1.2
            if ne20 > lh_lim:
                gamma_lhcd *= max(0.4, 1.0 - 0.25 * (ne20 / lh_lim - 1.0))

            # NBI
            E = max(50.0, min(5000.0, float(getattr(inp, "nbi_beam_energy_keV", 500.0))))
            gamma_nbi = 0.035 * core * (E / 500.0) ** 0.55
            if ne20 < 0.2:
                gamma_nbi *= max(0.3, ne20 / 0.2)

            # ICRF/FWCD
            gamma_icrf = 0.025 * core * (B0 / 5.0) ** 0.3

            def _bound(g: float) -> float:
                return float(max(1e-4, min(0.25, g)))

            gamma_eccd = _bound(gamma_eccd)
            gamma_lhcd = _bound(gamma_lhcd)
            gamma_nbi = _bound(gamma_nbi)
            gamma_icrf = _bound(gamma_icrf)

            gamma_eff = f_eccd * gamma_eccd + f_lhcd * gamma_lhcd + f_nbi * gamma_nbi + f_icrf * gamma_icrf
            gamma_eff = float(max(1e-4, min(0.25, gamma_eff)))

            def _eta(suffix: str) -> float:
                v = float(getattr(inp, f"eta_cd_wallplug_{suffix}", float("nan")))
                if math.isfinite(v) and v > 0.0:
                    return float(min(0.95, max(0.05, v)))
                return float(min(0.95, max(0.05, eta)))

            eta_eccd = _eta("eccd")
            eta_lhcd = _eta("lhcd")
            eta_nbi = _eta("nbi")
            eta_icrf = _eta("icrf")

            eta_eff = f_eccd * eta_eccd + f_lhcd * eta_lhcd + f_nbi * eta_nbi + f_icrf * eta_icrf
            eta_eff = float(min(0.95, max(0.05, eta_eff)))

            channels = {
                "ECCD": {"frac": f_eccd, "gamma_A_per_W": gamma_eccd, "eta_wallplug": eta_eccd},
                "LHCD": {"frac": f_lhcd, "gamma_A_per_W": gamma_lhcd, "eta_wallplug": eta_lhcd},
                "NBI": {"frac": f_nbi, "gamma_A_per_W": gamma_nbi, "eta_wallplug": eta_nbi},
                "ICRF": {"frac": f_icrf, "gamma_A_per_W": gamma_icrf, "eta_wallplug": eta_icrf},
            }
            return CurrentDriveModelResult(model="channel_library_v395", actuator="MIX", gamma_A_per_W=gamma_eff, eta_wallplug=eta_eff, channels=channels)

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
