"""Central user-facing labels for Point Designer Configure & Telemetry.

Plain physics/engineering names for Point Designer Configure & Telemetry UI.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configure deck — expansion sections (expert workflow order)
# ---------------------------------------------------------------------------
# section_id -> (title, icon, one-line help)
CONFIGURE_SECTIONS: Dict[str, Tuple[str, str, str]] = {
    "templates": (
        "Industrial scenario templates",
        "factory",
        "Pre-built reference machines from industrial scenario templates.",
    ),
    "machine_geometry": (
        "Machine geometry",
        "architecture",
        "Major/minor radius, elongation, triangularity, and toroidal field B₀.",
    ),
    "plasma_state": (
        "Plasma current, density & impurities",
        "science",
        "Plasma current, Greenwald fraction, effective charge, and fuel dilution.",
    ),
    "heating_fuel": (
        "Heating & fuel",
        "local_fire_department",
        "Auxiliary heating power and fuel species mode.",
    ),
    "model_options": (
        "Model options (transport & profiles)",
        "tune",
        "Confinement scaling, transport envelopes, and profile authority proxies.",
    ),
    "power_composition": (
        "Power & composition",
        "bolt",
        "Radiation, exhaust, alpha loss, H-mode, and non-inductive screens.",
    ),
    "engineering_plant": (
        "Engineering & plant feasibility",
        "precision_manufacturing",
        "Confidence presets, subsystem toggles, build, magnets, CD, and control.",
    ),
    "magnets_shielding": (
        "Magnets & neutron shielding",
        "electrical_services",
        "Coil technology class, operating temperature, and in-vessel shield thickness.",
    ),
    "operating_targets": (
        "Operating targets & solver",
        "gps_fixed",
        "Target Q and H98, evaluation mode, and Ip/fG search bounds.",
    ),
}

CONFIGURE_SECTION_ORDER: List[str] = [
    "templates",
    "machine_geometry",
    "plasma_state",
    "heating_fuel",
    "model_options",
    "power_composition",
    "magnets_shielding",
    "engineering_plant",
    "operating_targets",
]

# ---------------------------------------------------------------------------
# Authority / physics overlay toggles
# ---------------------------------------------------------------------------
# overlay_key -> (display_label, traceability_code | None, one_line_caption)
OVERLAY_LABELS: Dict[str, Tuple[str, Optional[str], str]] = {
    # Core plasma physics
    "include_radiation": (
        "Core radiation & impurities",
        None,
        "Line radiation, bremsstrahlung, and impurity dilution in the core model.",
    ),
    "include_alpha_loss": (
        "Alpha-particle loss fraction",
        None,
        "Fraction of alpha heating lost before coupling to the plasma.",
    ),
    "include_hmode_physics": (
        "H-mode access threshold (P_LH)",
        None,
        "L–H transition power threshold and H-mode confinement multiplier.",
    ),
    "include_synchrotron": (
        "Synchrotron radiation",
        None,
        "Wall-facing synchrotron power loss from relativistic electrons.",
    ),
    "include_bootstrap_pressure_selfconsistency": (
        "Bootstrap–pressure self-consistency",
        None,
        "Coupled bootstrap current fraction and pressure profile consistency.",
    ),
    "include_tritium_tight_closure": (
        "Tritium breeding tight closure",
        "PHYS-010",
        "Strict tritium balance without breeding slack (PHYS-010 contract).",
    ),
    # Transport & profiles
    "include_transport_contracts_v371": (
        "Transport feasibility contracts",
        "v371",
        "Optimistic vs robust bounds on required H-factor for confinement.",
    ),
    "include_transport_envelope_v396": (
        "Multi-scaling confinement envelope",
        "v396",
        "Min/max τE spread across multiple confinement scaling laws.",
    ),
    "include_profile_proxy_v397": (
        "Kinetic profile peaking proxy",
        "v397",
        "T/n profile shape, peaking limits, and q95 proxy bounds.",
    ),
    "include_profile_family_v358": (
        "Profile family selector",
        "v358",
        "Discrete profile-shape families for peaking sensitivity studies.",
    ),
    # Authority & stability
    "include_magnet_technology_authority_v400": (
        "Magnet technology margins",
        "v400",
        "Field, current density, and stress margins vs coil technology limits.",
    ),
    "include_magnet_sc_system_authority_v410": (
        "TF/PF/CS SC system depth",
        "v410",
        "Per-family TF/PF/CS superconducting and engineering margins beyond v400 (proxy).",
    ),
    "include_authority_dominance_v402": (
        "Global authority dominance engine",
        "v402",
        "Ranks which constraint family binds the point design.",
    ),
    "include_control_stability_authority_v398": (
        "Control & stability margins",
        "v398",
        "Vertical stability budget, VDE headroom, and RWM proximity.",
    ),
    "include_impurity_v399": (
        "Multi-species impurity radiation",
        "v399",
        "Zeff ceiling, core radiation fraction, and detachment margin.",
    ),
    "include_structural_life_v404": (
        "Structural life & fatigue",
        "v404",
        "Component lifetime under cyclic thermal and mechanical loads.",
    ),
    # Neutronics & materials
    "include_neutronics_materials_coupling_v372": (
        "Neutronics–materials coupling",
        "v372",
        "TBR and dose feedback into materials replacement requirements.",
    ),
    "include_neutronics_materials_library_v403": (
        "Nuclear materials library",
        "v403",
        "Activation inventories, dose rates, and replacement catalogs.",
    ),
    "include_nuclear_data_authority_v407": (
        "Nuclear data authority",
        "v407",
        "Cross-section and decay-data provenance for neutronics.",
    ),
    "include_neutronics_materials_authority_v401": (
        "Neutronics contract tiers",
        "v401",
        "Tiered neutronics feasibility contracts (TBR, dose, shielding).",
    ),
    "include_neutronics_activation_v390": (
        "Activation & waste routing",
        "v390",
        "Afterheat, waste class, and decay-heat routing estimates.",
    ),
    "include_neutronics_shield_attenuation_v392": (
        "Shield attenuation model",
        "v392",
        "Gamma and neutron attenuation through in-vessel shielding.",
    ),
    # Plant & engineering
    "include_control_contracts": (
        "Control system contracts",
        None,
        "Vertical stability, poloidal field, SOL, and RWM control contracts.",
    ),
    "include_current_drive": (
        "Non-inductive current drive closure",
        None,
        "Current-drive power and efficiency for NI fraction closure.",
    ),
    "include_economics_v360": (
        "Plant economics (capital & LCOE)",
        "v360",
        "Capital cost and levelized cost of electricity proxies.",
    ),
    "include_economics_v383": (
        "Plant economics depth model",
        "v383",
        "Extended O&M, replacement, and lifecycle cost detail.",
    ),
    "include_cost_authority_v388": (
        "Cost authority & escalation",
        "v388",
        "Cost uncertainty bands and escalation assumptions.",
    ),
    "include_structural_stress_v389": (
        "Structural stress limits",
        "v389",
        "Stress margins on in-vessel and structural components.",
    ),
    "include_availability_replacement_v359": (
        "Component replacement ledger",
        "v359",
        "Scheduled replacement intervals and associated costs.",
    ),
    "include_availability_reliability_v391": (
        "Availability & reliability envelope",
        "v391",
        "Planned outage, failure-rate, and capacity-factor envelope.",
    ),
    "include_materials_lifetime_v384": (
        "Materials lifetime ledger",
        "v384",
        "Fluence- and dose-limited component service lifetimes.",
    ),
    "include_maintenance_scheduling_v368": (
        "Maintenance scheduling model",
        "v368",
        "Outage windows, maintenance cadence, and crew loading.",
    ),
    "include_damage_strength_coupling_v393": (
        "Irradiation damage → strength coupling",
        "v393",
        "DPA-driven degradation of structural allowables (derived margins).",
    ),
    "include_structural_life_authority_v404": (
        "Structural life authority",
        "v404",
        "Component lifetime under cyclic thermal and mechanical loads.",
    ),
    "include_elm_transient_heat_v409": (
        "ELM transient heat authority",
        "v409",
        "Transient heat-flux envelope from ELM energy dumps.",
    ),
    "include_profile_contracts_v397": (
        "Profile feasibility contracts",
        "v397",
        "Explicit profile-shape feasibility contracts (governance).",
    ),
    "cd_mix_enable": (
        "CD multi-channel actuator mix",
        "v395",
        "Split launched CD power across ECCD/LHCD/NBI/ICRF channels.",
    ),
}

# group_id -> (title, one-line help)
OVERLAY_GROUP_LABELS: Dict[str, Tuple[str, str]] = {
    "core_physics": (
        "Core plasma physics",
        "Radiation, H-mode, alpha loss, and tritium closure models.",
    ),
    "transport_profiles": (
        "Transport & profile models",
        "Confinement contracts, τE envelopes, and profile peaking proxies.",
    ),
    "authority_stability": (
        "Authority & stability engines",
        "Magnet margins, global dominance, control stability, and impurity limits.",
    ),
    "neutronics_materials": (
        "Neutronics & activation",
        "TBR, shielding, materials libraries, and nuclear data provenance.",
    ),
    "plant_engineering": (
        "Plant & engineering overlays",
        "Economics, availability, structural stress, and maintenance scheduling.",
    ),
}

# Expert workflow: physics modules before plant/engineering
OVERLAY_GROUP_SPECS: List[Tuple[str, List[Tuple[str, bool]]]] = [
    (
        "core_physics",
        [
            ("include_radiation", False),
            ("include_alpha_loss", True),
            ("include_hmode_physics", True),
            ("include_synchrotron", True),
            ("include_bootstrap_pressure_selfconsistency", False),
            ("include_tritium_tight_closure", False),
        ],
    ),
    (
        "transport_profiles",
        [
            ("include_transport_contracts_v371", False),
            ("include_transport_envelope_v396", True),
            ("include_profile_proxy_v397", False),
            ("include_profile_family_v358", False),
            ("include_profile_contracts_v397", False),
        ],
    ),
    (
        "authority_stability",
        [
            ("include_magnet_technology_authority_v400", True),
            ("include_magnet_sc_system_authority_v410", False),
            ("include_authority_dominance_v402", True),
            ("include_control_stability_authority_v398", False),
            ("include_impurity_v399", False),
            ("include_structural_life_v404", False),
            ("include_structural_life_authority_v404", False),
            ("include_elm_transient_heat_v409", False),
            ("include_damage_strength_coupling_v393", False),
        ],
    ),
    (
        "neutronics_materials",
        [
            ("include_neutronics_materials_coupling_v372", False),
            ("include_neutronics_materials_library_v403", False),
            ("include_nuclear_data_authority_v407", False),
            ("include_neutronics_materials_authority_v401", False),
            ("include_neutronics_activation_v390", False),
            ("include_neutronics_shield_attenuation_v392", False),
        ],
    ),
    (
        "plant_engineering",
        [
            ("include_control_contracts", False),
            ("include_current_drive", False),
            ("cd_mix_enable", False),
            ("include_economics_v360", False),
            ("include_economics_v383", False),
            ("include_cost_authority_v388", False),
            ("include_structural_stress_v389", False),
            ("include_availability_replacement_v359", False),
            ("include_availability_reliability_v391", False),
            ("include_materials_lifetime_v384", False),
            ("include_maintenance_scheduling_v368", False),
        ],
    ),
]

# Numeric sub-knob panel titles (parent overlay key -> title)
OVERLAY_NUMERIC_TITLES: Dict[str, str] = {
    "include_transport_contracts_v371": "Transport feasibility contracts",
    "include_transport_envelope_v396": "Multi-scaling confinement envelope",
    "include_profile_proxy_v397": "Kinetic profile peaking proxy",
    "include_magnet_technology_authority_v400": "Magnet technology margins",
    "include_magnet_sc_system_authority_v410": "TF/PF/CS SC system depth",
    "include_control_stability_authority_v398": "Control & stability margins",
    "include_impurity_v399": "Multi-species impurity radiation",
    "include_profile_family_v358": "Profile family library",
    "include_neutronics_materials_coupling_v372": "Neutronics–materials coupling",
    "include_bootstrap_pressure_selfconsistency": "Bootstrap–pressure self-consistency",
    "include_damage_strength_coupling_v393": "Damage → strength coupling",
}

# ---------------------------------------------------------------------------
# Telemetry views (verdict-first order)
# ---------------------------------------------------------------------------
TELEMETRY_VIEWS: List[str] = [
    "Verdict & KPIs",
    "Power balance plots",
    "Authority dominance & closures",
    "Control system contracts",
    "Plant & materials ledgers",
    "Parameter sensitivity",
    "Run history & export",
]

# Legacy Streamlit / Phase-19 names → current labels (session migration)
_TELEMETRY_VIEW_ALIASES: Dict[str, str] = {
    "Mission Snapshot": "Verdict & KPIs",
    "Plot Deck": "Power balance plots",
    "Dominance & Closures": "Authority dominance & closures",
    "Control Contracts": "Control system contracts",
    "Ledgers": "Plant & materials ledgers",
    "Sensitivity Lab": "Parameter sensitivity",
    "Chronicle & Export": "Run history & export",
}


def overlay_display_label(key: str) -> str:
    return OVERLAY_LABELS[key][0]


def overlay_traceability(key: str) -> Optional[str]:
    code = OVERLAY_LABELS[key][1]
    if code and str(code).lower().startswith("v") and str(code)[1:].replace(".", "").isdigit():
        return None
    return code


def overlay_caption(key: str) -> str:
    return OVERLAY_LABELS[key][2]


def overlay_group_title(group_id: str) -> str:
    return OVERLAY_GROUP_LABELS[group_id][0]


def overlay_group_caption(group_id: str) -> str:
    return OVERLAY_GROUP_LABELS[group_id][1]


def overlay_numeric_title(flag: str) -> str:
    return OVERLAY_NUMERIC_TITLES.get(flag, overlay_display_label(flag))


def normalize_telemetry_view(view: str) -> str:
    """Map legacy view names to current labels."""
    return _TELEMETRY_VIEW_ALIASES.get(view, view)
