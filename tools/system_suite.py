from __future__ import annotations

"""SHAMS System Suite (v250.0).

System-code–grade overlays that **do not** modify the frozen evaluator truth.

These helpers intentionally live in ``tools/``:
  - They are UI/analysis-facing.
  - They operate on already-produced Point Designer artifacts.

No hidden iteration policy
--------------------------
Nothing here is allowed to change PointInputs, relax constraints, or iterate
back into physics. Any time-domain computations are *diagnostic clients*
executed on frozen envelopes/values.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import hashlib
import json
import math


def _sha256_json(obj: Any) -> str:
    """Stable SHA-256 of a JSON-serializable object."""
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = json.dumps(str(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return x
    except Exception:
        return default


@dataclass(frozen=True)
class PowerClosureReport:
    Pe_gross_MW: float
    Precirc_MW: float
    Pe_net_MW: float
    recirc_frac: float
    Qe: float
    stamp_sha256: str
    breakdown: Dict[str, float]


def power_closure_overlay(point_out: Mapping[str, Any], point_inp: Optional[Mapping[str, Any]] = None) -> PowerClosureReport:
    """Return a deterministic power-closure report.

    Uses evaluator outputs if present; otherwise derives a minimal closure.
    """
    o = dict(point_out or {})
    i = dict(point_inp or {})

    Pe_gross = _f(o.get("P_e_gross_MW", o.get("P_gross_e_MW", float("nan"))))
    Precirc = _f(o.get("P_recirc_MW", float("nan")))
    Pe_net = _f(o.get("P_e_net_MW", o.get("P_net_e_MW", float("nan"))))
    Qe = _f(o.get("Qe", float("nan")))

    # Minimal derivations if any pieces missing
    if not math.isfinite(Pe_net) and math.isfinite(Pe_gross) and math.isfinite(Precirc):
        Pe_net = Pe_gross - Precirc
    if not math.isfinite(Precirc) and math.isfinite(Pe_gross) and math.isfinite(Pe_net):
        Precirc = max(Pe_gross - Pe_net, 0.0)
    if not math.isfinite(Pe_gross) and math.isfinite(Pe_net) and math.isfinite(Precirc):
        Pe_gross = Pe_net + Precirc

    recirc_frac = float("nan")
    if math.isfinite(Pe_gross) and Pe_gross > 0:
        recirc_frac = max(min(Precirc / Pe_gross, 1.0), 0.0) if math.isfinite(Precirc) else float("nan")

    breakdown = {
        "Paux_MW": _f(o.get("Paux_MW", i.get("Paux_MW", float("nan")))),
        "P_cd_launch_MW": _f(o.get("P_cd_launch_MW", float("nan"))),
        "P_pumps_MW": _f(o.get("P_pumps_MW", o.get("P_pump_MW", float("nan")))),
        "P_balance_of_plant_MW": _f(o.get("P_balance_of_plant_MW", i.get("P_balance_of_plant_MW", float("nan")))),
        "P_cryo_20K_MW": _f(o.get("P_cryo_20K_MW", i.get("P_cryo_20K_MW", float("nan")))),
        "P_tf_ohmic_MW": _f(o.get("P_tf_ohmic_MW", float("nan"))),
    }
    stamp_sha256 = _sha256_json(
        {
            "Pe_gross_MW": Pe_gross,
            "Precirc_MW": Precirc,
            "Pe_net_MW": Pe_net,
            "Qe": Qe,
            "breakdown": breakdown,
        }
    )

    return PowerClosureReport(
        Pe_gross_MW=Pe_gross,
        Precirc_MW=Precirc,
        Pe_net_MW=Pe_net,
        recirc_frac=recirc_frac,
        Qe=Qe,
        stamp_sha256=stamp_sha256,
        breakdown=breakdown,
    )


@dataclass(frozen=True)
class TrajectoryDiagnostics:
    t_s: List[float]
    Pe_net_MW: List[float]
    Precirc_MW: List[float]
    meta: Dict[str, Any]
    violations: List[Dict[str, Any]]
    stamp_sha256: str


def trajectory_diagnostics_client(
    point_out: Mapping[str, Any],
    point_inp: Optional[Mapping[str, Any]] = None,
    n_points: int = 241,
) -> TrajectoryDiagnostics:
    """Deterministic, piecewise trajectory diagnostic.

    This is *not* a plasma/control solver. It creates a replayable time-series
    using frozen pulse envelope fields already computed in the evaluator:
      - ramp duration: pulse_ramp_s (fallback 300s)
      - burn duration: t_burn_s or t_flat_s (fallback 7200s)
      - dwell duration: t_dwell_s (fallback 600s)

    The intent is to expose **time-integrated** violations (power/energy limits)
    without contaminating physics truth.
    """
    o = dict(point_out or {})
    i = dict(point_inp or {})

    ramp = _f(i.get("pulse_ramp_s", o.get("pulse_ramp_s", 300.0)), 300.0)
    burn = _f(o.get("t_flat_s", o.get("t_burn_s", i.get("t_burn_s", 7200.0))), 7200.0)
    dwell = _f(o.get("t_dwell_s", i.get("t_dwell_s", 600.0)), 600.0)
    burn = max(burn, 0.0)

    T = float(max(ramp + burn + ramp + dwell, 1.0))
    n = int(max(21, min(int(n_points), 2001)))
    dt = T / (n - 1)

    Pe_net = _f(o.get("P_e_net_MW", o.get("P_net_e_MW", float("nan"))))
    Precirc = _f(o.get("P_recirc_MW", float("nan")))
    if not math.isfinite(Pe_net):
        Pe_net = 0.0
    if not math.isfinite(Precirc):
        Precirc = 0.0

    # Shape: ramp-up -> flat -> ramp-down -> dwell
    t_s: List[float] = []
    pnet: List[float] = []
    prec: List[float] = []

    for k in range(n):
        t = k * dt
        if t <= ramp and ramp > 0:
            f = t / ramp
        elif t <= ramp + burn:
            f = 1.0
        elif t <= ramp + burn + ramp and ramp > 0:
            f = max(1.0 - (t - (ramp + burn)) / ramp, 0.0)
        else:
            f = 0.0
        t_s.append(float(t))
        pnet.append(float(Pe_net * f))
        prec.append(float(Precirc * f))

    # Diagnostics: peak/avg power and integrated energies
    Pnet_peak = max(pnet) if pnet else 0.0
    Prec_peak = max(prec) if prec else 0.0
    Pnet_avg = sum(pnet) / len(pnet) if pnet else 0.0
    Prec_avg = sum(prec) / len(prec) if prec else 0.0
    Enet_MJ = sum((pnet[j] * dt) for j in range(len(pnet)))  # MW*s = MJ
    Erec_MJ = sum((prec[j] * dt) for j in range(len(prec)))

    # Violation checks (only if limits exist and are finite)
    violations: List[Dict[str, Any]] = []
    P_recirc_max = _f(i.get("P_recirc_max_MW", o.get("P_recirc_max_MW", float("nan"))))
    P_aux_wall_max = _f(i.get("P_aux_wallplug_max_MW", o.get("P_aux_wallplug_max_MW", float("nan"))))
    E_pf_max = _f(i.get("E_pf_max_MJ", o.get("E_pf_max_MJ", float("nan"))))

    if math.isfinite(P_recirc_max) and Prec_peak > P_recirc_max:
        violations.append({"kind": "POWER", "name": "Precirc_peak", "value": Prec_peak, "limit": P_recirc_max})
    if math.isfinite(P_aux_wall_max):
        # We proxy aux wallplug peak as Precirc_peak in absence of detailed split.
        if Prec_peak > P_aux_wall_max:
            violations.append({"kind": "POWER", "name": "Paux_wallplug_peak_proxy", "value": Prec_peak, "limit": P_aux_wall_max})
    if math.isfinite(E_pf_max) and Erec_MJ > E_pf_max:
        violations.append({"kind": "ENERGY", "name": "Erecirc_proxy", "value": Erec_MJ, "limit": E_pf_max})

    meta = {
        "ramp_s": ramp,
        "burn_s": burn,
        "dwell_s": dwell,
        "T_s": T,
        "dt_s": dt,
        "Pnet_peak_MW": Pnet_peak,
        "Pnet_avg_MW": Pnet_avg,
        "Precirc_peak_MW": Prec_peak,
        "Precirc_avg_MW": Prec_avg,
        "Enet_MJ": Enet_MJ,
        "Erecirc_MJ": Erec_MJ,
        "note": "Deterministic envelope trajectory diagnostic (non-authoritative).",
    }

    stamp_sha256 = _sha256_json({"meta": meta, "violations": violations})
    return TrajectoryDiagnostics(t_s=t_s, Pe_net_MW=pnet, Precirc_MW=prec, meta=meta, violations=violations, stamp_sha256=stamp_sha256)


@dataclass(frozen=True)
class LifetimeFuelReport:
    fw_dpa_per_year: float
    fw_dpa_max_per_year: float
    fw_dpa_margin: float
    cycles_per_year: float
    cycles_max: float
    cycles_margin: float
    tbr: float
    tbr_min: float
    tbr_margin: float
    stamp_sha256: str


def lifetime_and_fuel_overlay(point_out: Mapping[str, Any], point_inp: Optional[Mapping[str, Any]] = None) -> LifetimeFuelReport:
    """Static lifetime + fuel closure overlay.

    Uses existing proxies already emitted by the evaluator when available.
    """
    o = dict(point_out or {})
    i = dict(point_inp or {})

    fw_dpa = _f(o.get("fw_dpa_per_year", float("nan")))
    fw_dpa_max = _f(o.get("fw_dpa_max_per_year", i.get("fw_dpa_max_per_year", float("nan"))))
    fw_margin = float("nan")
    if math.isfinite(fw_dpa) and math.isfinite(fw_dpa_max):
        fw_margin = fw_dpa_max - fw_dpa

    cyc_y = _f(o.get("cycles_per_year", float("nan")))
    cyc_max = _f(o.get("cycles_max", i.get("cycles_max", float("nan"))))
    cyc_margin = float("nan")
    if math.isfinite(cyc_y) and math.isfinite(cyc_max) and cyc_y > 0:
        # years to hit cycle limit (proxy)
        cyc_margin = (cyc_max / cyc_y) - 1.0  # margin in "years-1" space; positive means >1 year

    tbr = _f(o.get("TBR", o.get("tbr_proxy", float("nan"))))
    tbr_min = _f(i.get("TBR_min", o.get("TBR_min", float("nan"))))
    tbr_margin = float("nan")
    if math.isfinite(tbr) and math.isfinite(tbr_min):
        tbr_margin = tbr - tbr_min

    stamp_sha256 = _sha256_json(
        {
            "fw": {"dpa": fw_dpa, "max": fw_dpa_max, "margin": fw_margin},
            "cycles": {"per_year": cyc_y, "max": cyc_max, "margin": cyc_margin},
            "tbr": {"tbr": tbr, "min": tbr_min, "margin": tbr_margin},
        }
    )

    return LifetimeFuelReport(
        fw_dpa_per_year=fw_dpa,
        fw_dpa_max_per_year=fw_dpa_max,
        fw_dpa_margin=fw_margin,
        cycles_per_year=cyc_y,
        cycles_max=cyc_max,
        cycles_margin=cyc_margin,
        tbr=tbr,
        tbr_min=tbr_min,
        tbr_margin=tbr_margin,
        stamp_sha256=stamp_sha256,
    )


# =============================
# v253.0: Operations & Thermal
# =============================

@dataclass(frozen=True)
class OpsAvailabilityReport:
    """Deterministic operations overlay.

    This does not change feasibility truth; it provides a system-code style
    *operations closure* using frozen pulse parameters and optional RAM
    scenarios.
    """

    duty_cycle: float
    availability: float
    Pe_net_MW: float
    avg_delivered_MW: float
    annual_energy_GWh: float
    stamp_sha256: str
    breakdown: Dict[str, float]


def ops_availability_overlay(
    point_out: Mapping[str, Any],
    point_inp: Optional[Mapping[str, Any]] = None,
    *,
    availability: Optional[float] = None,
) -> OpsAvailabilityReport:
    """Compute duty-cycle and simple availability overlay.

    Parameters
    ----------
    availability:
        Availability fraction [0,1]. If None, a conservative default is
        chosen based on declared intent when available.
    """
    o = dict(point_out or {})
    i = dict(point_inp or {})

    # Pulse timings (seconds)
    ramp = _f(i.get("pulse_ramp_s", o.get("pulse_ramp_s", 300.0)), 300.0)
    burn = _f(o.get("t_flat_s", o.get("t_burn_s", i.get("t_burn_s", 7200.0))), 7200.0)
    dwell = _f(o.get("t_dwell_s", i.get("t_dwell_s", 600.0)), 600.0)
    burn = max(burn, 0.0)

    T = max(ramp + burn + ramp + dwell, 1.0)
    duty = max(min(burn / T if T > 0 else 0.0, 1.0), 0.0)

    # Availability default by intent (deterministic, conservative)
    if availability is None:
        intent = str(i.get("design_intent", o.get("design_intent", ""))).strip().lower()
        if "react" in intent or "power" in intent or "pilot" in intent:
            availability = 0.75
        else:
            availability = 0.35
    availability = float(max(min(availability, 1.0), 0.0))

    Pe_net = _f(o.get("P_e_net_MW", o.get("P_net_e_MW", float("nan"))))
    if not math.isfinite(Pe_net):
        Pe_net = 0.0

    avg_delivered = Pe_net * duty * availability
    annual_energy_GWh = avg_delivered * 8760.0 / 1000.0

    breakdown = {
        "ramp_s": float(ramp),
        "burn_s": float(burn),
        "dwell_s": float(dwell),
        "cycle_s": float(T),
        "duty_cycle": float(duty),
        "availability": float(availability),
        "Pe_net_MW": float(Pe_net),
        "avg_delivered_MW": float(avg_delivered),
        "annual_energy_GWh": float(annual_energy_GWh),
    }
    stamp = _sha256_json(breakdown)
    return OpsAvailabilityReport(
        duty_cycle=float(duty),
        availability=float(availability),
        Pe_net_MW=float(Pe_net),
        avg_delivered_MW=float(avg_delivered),
        annual_energy_GWh=float(annual_energy_GWh),
        stamp_sha256=stamp,
        breakdown=breakdown,
    )


@dataclass(frozen=True)
class ThermalNetworkDiagnostics:
    """Deterministic thermal network diagnostic (external-client style)."""

    t_s: List[float]
    nodes_K: Dict[str, List[float]]
    violations: List[Dict[str, Any]]
    meta: Dict[str, Any]
    stamp_sha256: str


def thermal_network_diagnostics_client(
    point_out: Mapping[str, Any],
    point_inp: Optional[Mapping[str, Any]] = None,
    *,
    n_points: int = 361,
) -> ThermalNetworkDiagnostics:
    """Run a small lumped thermal network driven by frozen power envelopes.

    Design intent
    -------------
    - Deterministic; fixed-step forward Euler.
    - Diagnostic-only; no back-coupling into feasibility truth.
    - Graceful degradation when needed fields are unavailable.

    Model
    -----
    3-node network: blanket/FW, divertor, cryo plant (proxy).

    Each node i has lumped heat capacity C_i [MJ/K] and is cooled to a sink
    temperature T_sink via R_i [K/MW].

    dT_i/dt = (P_i(t) - (T_i - T_sink)/R_i) / C_i

    Input power partitioning uses best-effort fields; if unavailable,
    it derives a conservative thermal load from fusion power minus gross
    electric.
    """
    o = dict(point_out or {})
    i = dict(point_inp or {})

    # Time base from pulse envelope
    ramp = _f(i.get("pulse_ramp_s", o.get("pulse_ramp_s", 300.0)), 300.0)
    burn = _f(o.get("t_flat_s", o.get("t_burn_s", i.get("t_burn_s", 7200.0))), 7200.0)
    dwell = _f(o.get("t_dwell_s", i.get("t_dwell_s", 600.0)), 600.0)
    burn = max(burn, 0.0)
    Ttot = float(max(ramp + burn + ramp + dwell, 1.0))
    n = int(max(31, min(int(n_points), 4001)))
    dt = Ttot / (n - 1)

    # Available power fields
    P_fus = _f(o.get("P_fus_MW", o.get("Pfusion_MW", float("nan"))))
    Pe_gross = _f(o.get("P_e_gross_MW", o.get("P_gross_e_MW", float("nan"))))
    P_rad = _f(o.get("P_rad_MW", o.get("Prad_MW", float("nan"))))
    P_SOL = _f(o.get("P_SOL_MW", o.get("Psol_MW", float("nan"))))
    P_aux = _f(o.get("Paux_MW", i.get("Paux_MW", float("nan"))))

    # Conservative derived thermal power to manage (MW)
    P_thermal = float("nan")
    if math.isfinite(P_fus) and math.isfinite(Pe_gross):
        P_thermal = max(P_fus + (P_aux if math.isfinite(P_aux) else 0.0) - Pe_gross, 0.0)
    elif math.isfinite(P_fus):
        P_thermal = max(P_fus * 0.7 + (P_aux if math.isfinite(P_aux) else 0.0), 0.0)
    else:
        # If fusion power unavailable, use recirc as a proxy load.
        Precirc = _f(o.get("P_recirc_MW", float("nan")))
        P_thermal = max(Precirc, 0.0) if math.isfinite(Precirc) else 0.0

    # Partitioning (best-effort)
    # - Blanket/FW gets bulk thermal excluding divertor/SOL
    # - Divertor gets SOL power (or a fixed fraction)
    # - Cryo proxy gets a small fraction of recirc/aux
    P_div0 = P_SOL if math.isfinite(P_SOL) else 0.15 * P_thermal
    P_cryo0 = 0.05 * (P_aux if math.isfinite(P_aux) else 0.0)
    P_fw0 = max(P_thermal - P_div0 - P_cryo0, 0.0)

    # Thermal parameters (overrideable)
    T_sink = _f(i.get("T_sink_K", 300.0), 300.0)
    C_fw = _f(i.get("C_fw_MJ_per_K", 5.0e4), 5.0e4)      # 50,000 MJ/K
    C_div = _f(i.get("C_div_MJ_per_K", 1.5e4), 1.5e4)    # 15,000 MJ/K
    C_cryo = _f(i.get("C_cryo_MJ_per_K", 5.0e3), 5.0e3)  # 5,000 MJ/K

    R_fw = _f(i.get("R_fw_K_per_MW", 0.02), 0.02)
    R_div = _f(i.get("R_div_K_per_MW", 0.01), 0.01)
    R_cryo = _f(i.get("R_cryo_K_per_MW", 0.05), 0.05)

    # Limits (optional)
    T_fw_max = _f(i.get("T_fw_max_K", o.get("T_fw_max_K", float("nan"))))
    T_div_max = _f(i.get("T_div_max_K", o.get("T_div_max_K", float("nan"))))

    # Initial temperatures
    T_fw = _f(i.get("T_fw0_K", T_sink), T_sink)
    T_div = _f(i.get("T_div0_K", T_sink), T_sink)
    T_cryo = _f(i.get("T_cryo0_K", T_sink), T_sink)

    t_s: List[float] = []
    fw: List[float] = []
    dv: List[float] = []
    cr: List[float] = []

    violations: List[Dict[str, Any]] = []

    def _shape(t: float) -> float:
        if t <= ramp and ramp > 0:
            return t / ramp
        if t <= ramp + burn:
            return 1.0
        if t <= ramp + burn + ramp and ramp > 0:
            return max(1.0 - (t - (ramp + burn)) / ramp, 0.0)
        return 0.0

    for k in range(n):
        t = k * dt
        f = _shape(t)

        # Drive powers
        P_fw = P_fw0 * f
        P_div = P_div0 * f
        P_cryo = P_cryo0 * f

        # Euler updates (MW*s = MJ)
        T_fw += dt * (P_fw - (T_fw - T_sink) / R_fw) / C_fw
        T_div += dt * (P_div - (T_div - T_sink) / R_div) / C_div
        T_cryo += dt * (P_cryo - (T_cryo - T_sink) / R_cryo) / C_cryo

        t_s.append(float(t))
        fw.append(float(T_fw))
        dv.append(float(T_div))
        cr.append(float(T_cryo))

    # Post violations
    if math.isfinite(T_fw_max) and max(fw) > T_fw_max:
        violations.append({"kind": "THERMAL", "node": "fw", "max_K": max(fw), "limit_K": T_fw_max})
    if math.isfinite(T_div_max) and max(dv) > T_div_max:
        violations.append({"kind": "THERMAL", "node": "divertor", "max_K": max(dv), "limit_K": T_div_max})

    meta = {
        "T_sink_K": T_sink,
        "dt_s": dt,
        "T_total_s": Ttot,
        "P_thermal_MW": P_thermal,
        "P_fw_MW": P_fw0,
        "P_div_MW": P_div0,
        "P_cryo_MW": P_cryo0,
        "note": "Deterministic lumped thermal diagnostic (non-authoritative).",
    }
    stamp = _sha256_json({"meta": meta, "violations": violations})

    return ThermalNetworkDiagnostics(
        t_s=t_s,
        nodes_K={"fw": fw, "divertor": dv, "cryo": cr},
        violations=violations,
        meta=meta,
        stamp_sha256=stamp,
    )
