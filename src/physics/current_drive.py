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

    # Actuator scaling: gamma ~ gamma0 * (Te/10) / (ne20 * (R0/6))
    # Baselines chosen to be monotone and in the right *order* (LHCD > ECCD > NBI) for typical regimes.
    gamma0_map = {
        "LHCD": 0.08,
        "ECCD": 0.05,
        "NBI": 0.03,
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
