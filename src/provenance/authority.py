from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class AuthorityContract:
    """Subsystem authority metadata.

    Small, deterministic, and JSON-serializable via ``asdict``.
    """

    subsystem: str
    tier: str  # proxy | semi-authoritative | authoritative
    validity_domain: str
    equations: List[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subsystem"] = str(d.get("subsystem", ""))
        d["tier"] = str(d.get("tier", ""))
        d["validity_domain"] = str(d.get("validity_domain", ""))
        d["equations"] = [str(x) for x in (d.get("equations", []) or [])]
        d["notes"] = str(d.get("notes", ""))
        return d


# Frozen, human-readable contracts (conservative). These do not compute physics.
AUTHORITY_CONTRACTS: Dict[str, AuthorityContract] = {
    "plasma.confinement": AuthorityContract(
        subsystem="plasma.confinement",
        tier="semi-authoritative",
        validity_domain="H-mode tokamak confinement scalings; 0-D global IPB98(H98) with explicit H-factor; L-mode handled via ITER89P proxy when enabled.",
        equations=["tau_E = H98 * tau_IPB98", "(optional) tau_E_L = H_L * tau_ITER89P"],
        notes="No transport or time evolution; intended for feasibility screening and trade-space mapping.",
    ),
    "plasma.profiles": AuthorityContract(
        subsystem="plasma.profiles",
        tier="proxy",
        validity_domain="Analytic 1/2-D profiles with deterministic pedestal scaffold; bounded and monotone by construction.",
        equations=["p(r)=p0*(1-(r/a)^2)^alpha (core)", "two-zone core+pedestal integration"],
        notes="Profile shape is a scaffold for stored energy, bootstrap sensitivity, and radiation integrals.",
    ),
    "plasma.profile_contracts": AuthorityContract(
        subsystem="plasma.profile_contracts",
        tier="semi-authoritative",
        validity_domain=(
            "Certified optimistic vs robust envelopes over v358 profile-family knobs (peaking, pedestal proxy, "
            "confinement and bootstrap multipliers), evaluated by finite hypercube corners (C8/C16/C32)."
        ),
        equations=[
            "x_i = clamp(x0_i*(1±span_i)) or clamp(x0_i±span_i) per axis",
            "robust_feasible = AND_over_corners( hard_constraints_pass )",
            "mirage = feasible_optimistic AND (NOT feasible_robust)",
        ],
        notes="Governance overlay only; does not modify frozen truth; no solvers/iteration.",
    ),
    "current.bootstrap": AuthorityContract(
        subsystem="current.bootstrap",
        tier="semi-authoritative",
        validity_domain="Bootstrap fraction estimated from pressure-gradient proxies; optional Sauter-inspired mode with collisionality proxies.",
        equations=["I_bs ~ f(grad p, q, kappa, nu*)"],
        notes="Not a full neoclassical solver; output tagged with mode and validity flags.",
    ),
    "current.drive": AuthorityContract(
        subsystem="current.drive",
        tier="proxy",
        validity_domain="Actuator-scaled CD efficiency trends (NBI/ECCD/LHCD) with deterministic coupling into recirculating power.",
        equations=["P_CD = I_CD / eta_CD", "P_recirc includes P_CD"],
        notes="No ray tracing or deposition physics.",
    ),
    "radiation.core": AuthorityContract(
        subsystem="radiation.core",
        tier="authoritative",
        validity_domain="Line-radiation via Lz(T) cooling curves; external DB ingestion with SHA256 provenance; OFF by default.",
        equations=["P_rad = ∫ n_e^2 * Lz(T) dV"],
        notes="Authority drops to proxy if DB missing and fallback curve used.",
    ),
    "exhaust.divertor": AuthorityContract(
        subsystem="exhaust.divertor",
        tier="semi-authoritative",
        validity_domain="Two-point-style SOL/divertor proxy with optional Eich14 lambda_q; unified exhaust API ensures single-source outputs.",
        equations=["q_parallel ~ P_SOL/(2πR λ_q f_exp)", "two-regime attached/detached proxy"],
        notes="Not a SOL code replacement; used for feasibility screens and dominant-mechanism mapping.",
    ),
    "engineering.radial_build": AuthorityContract(
        subsystem="engineering.radial_build",
        tier="semi-authoritative",
        validity_domain="PROCESS-inspired explicit inboard stack closure (sum of thicknesses) with signed margin; no CAD.",
        equations=["inboard_space = R0 - a*(1-δ_proxy)", "margin = inboard_space - Σ thickness"],
        notes="Constraint enforcement is opt-in to preserve legacy behavior.",
    ),
    "engineering.magnets": AuthorityContract(
        subsystem="engineering.magnets",
        tier="semi-authoritative",
        validity_domain="Technology-aware TF proxies (Bpeak, stress, HTS critical-surface margin; copper I^2R loss coupling).",
        equations=["Bpeak ~ B0*(R0/R_inner)*factor", "sigma ~ B^2/(2μ0) * R/t", "hts_margin=Jc(B,T)/Jop"],
        notes="Monotone, bounded proxies; not a detailed FEM.",
    ),
    "neutronics.proxy": AuthorityContract(
        subsystem="neutronics.proxy",
        tier="proxy",
        validity_domain=(
            "Neutron wall load and TBR proxies with optional radial-stack attenuation and "
            "nuclear heating shares parameterized by region materials tags."
        ),
        equations=[
            "NWL ~ 0.8*P_fus/A_FW",
            "TBR_proxy ~ f(t_blanket, coverage)",
            "atten_stack = exp(-Σ mu_n_i * t_i)",
        ],
        notes="Not a Monte-Carlo neutronics replacement; used for feasibility screens and transparent bookkeeping.",
    ),

    "materials.damage_proxy": AuthorityContract(
        subsystem="materials.damage_proxy",
        tier="proxy",
        validity_domain="First-wall/blanket dpa and lifetime proxies derived from neutron wall load and a small materials library.",
        equations=["dpa_fw/y ~ 5 * NWL", "life_fw ~ dpa_limit / dpa_fw/y", "dpa_blanket/y ~ 0.6*dpa_fw/y"],
        notes="Screening-only; does not represent irradiation campaigns, temperature dependence, or transmutation.",
    ),

    "materials.lifetime_closure": AuthorityContract(
        subsystem="materials.lifetime_closure",
        tier="semi-authoritative",
        validity_domain=(
            "Deterministic replacement cadence + cost-rate bookkeeping derived from existing FW/blanket lifetime proxies "
            "and plant design lifetime policy. No time-domain simulation; no RAMI model."
        ),
        equations=[
            "replace_interval = max(lifetime_proxy, interval_min)",
            "replacements = ceil(plant_life / replace_interval) - 1",
            "annual_cost_rate ~ capex_component * install_factor / replace_interval",
        ],
        notes="Post-processing-only closure; does not modify neutronics/materials lifetime proxy physics.",
    ),

    # v367.0: deterministic replacement cadence + annualized cost-rate closure.
    "materials.lifetime_closure": AuthorityContract(
        subsystem="materials.lifetime_closure",
        tier="semi-authoritative",
        validity_domain=(
            "Deterministic post-processing over neutronics/materials lifetime proxies to produce replacement cadence, "
            "counts over plant life, and annualized replacement cost-rate proxies."
        ),
        equations=[
            "years_to_limit := lifetime_proxy_yr",
            "interval_y := clamp(years_to_limit, min_interval, plant_life)",
            "n_repl := ceil(plant_life/interval_y) - 1",
            "cost_rate := capex_component * install_factor / interval_y",
        ],
        notes="Pure bookkeeping overlay; does not modify frozen truth or time-step component degradation.",
    ),
    "fuel_cycle.tritium": AuthorityContract(
        subsystem="fuel_cycle.tritium",
        tier="proxy",
        validity_domain="T burn and inventory proxies from fusion power; processing efficiency and reserve days.",
        equations=["T_burn ∝ P_fus/17.6MeV", "inventory_proxy ~ processing_rate*reserve_days"],
        notes="Used for feasibility/risk screening only.",
    ),
    "plant.availability": AuthorityContract(
        subsystem="plant.availability",
        tier="proxy",
        validity_domain="Scheduled outage from replacement intervals (dpa/erosion proxies) + forced trips.",
        equations=["A = 1 - downtime_sched - downtime_trips"],
        notes="Not a plant operations simulator.",
    ),
    "scan.cartography": AuthorityContract(
        subsystem="scan.cartography",
        tier="authoritative",
        validity_domain="Deterministic mapping over frozen Point Designer evaluator; no optimization.",
        equations=["dominant constraint = argmin(margin) over hard constraints"],
        notes="Cartography semantics are frozen; new derived layers must be purely post-processing.",
    ),

    "control.actuators": AuthorityContract(
        subsystem="control.actuators",
        tier="semi-authoritative",
        validity_domain="Power-supply and actuator capacity caps: PF/CS envelope (I, V, P, dI/dt, pulse energy), CS loop-voltage ramp proxy, auxiliary+CD wallplug draw, and CD actuator capacity to meet NI target.",
        equations=[
            "P_aux_total_el = Paux/eta_aux + P_cd_launch/eta_cd",
            "P_cd_required = (I_cd_required/gamma_cd)/1e6",
            "PF envelope: V_peak = L dI/dt + R I; P_peak = V_peak I",
            "P_supply_peak = max(PF_peak, Aux/CD_wallplug, VS_control, RWM_control)",
        ],
        notes="Deterministic capacity gating. Enforced only when corresponding *_max caps are finite; otherwise recorded as diagnostics.",
    ),
    "control.rwm": AuthorityContract(
        subsystem="control.rwm",
        tier="proxy",
        validity_domain="RWM screening proxy between no-wall and ideal-wall beta limits; uses wall-time constant tau_w and bounded parametric scalings in (kappa, delta, q95, li).",
        equations=[
            "betaN_NW = C_NW * F(kappa,delta,q95,li)",
            "betaN_IW = C_IW * F(kappa,delta,q95,li)",
            "chi=(beta_N-betaN_NW)/(betaN_IW-betaN_NW)",
            "gamma_rwm ~ Phi(chi)*Psi(rot)/tau_w",
            "f_req ~ gamma_rwm/(2π)",
            "P_req ~ C_P * W_pf * gamma_rwm",
        ],
        notes="PROCESS-class screening: deterministic, no MHD simulation; intended for feasibility gating of control authority.",
    ),
}


def authority_snapshot_from_outputs(out: Dict[str, Any]) -> Dict[str, Any]:
    """Return an authority snapshot with dynamic tier adjustments.

    Dynamic downgrades:
      - radiation.core: authoritative -> proxy if DB hash missing/unknown while radiation is enabled.

    This function is deterministic and safe to call in the evaluator.
    """
    snap: Dict[str, Any] = {}
    for key, c in AUTHORITY_CONTRACTS.items():
        cd = c.to_dict()
        snap[key] = cd

    # Radiation downgrade logic
    try:
        rad_on = bool(out.get("include_radiation", False))
        rad_hash = str(out.get("radiation_db_sha256", ""))
        rad_model = str(out.get("radiation_model", ""))
        if rad_on:
            if (not rad_hash) or ("fallback" in rad_model.lower()) or ("proxy" in rad_model.lower()):
                snap["radiation.core"]["tier"] = "semi-authoritative" if rad_hash else "proxy"
                snap["radiation.core"]["notes"] = (snap["radiation.core"].get("notes", "") + " Downgraded: DB hash missing or fallback curve used.").strip()
    except Exception:
        pass

    return {
        "schema_version": "authority_contracts.v1",
        "subsystems": snap,
    }
