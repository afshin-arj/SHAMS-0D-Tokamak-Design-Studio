from __future__ import annotations

from typing import Any, Dict, List


def default_model_registry() -> Dict[str, Any]:
    """Return a transparent list of model options.

    This is SHAMS' PROCESS-inspired analogue to selecting model "switches",
    but kept explicit, explainable, and maturity-tagged.
    
    NOTE: This is a starter registry. As SHAMS adds alternative submodels,
    new options can be appended here without changing existing IDs.
    """

    options = {
        "confinement": [
            {
                "id": "H98_proxy_v1",
                "description": "Transparent H98 proxy computed from internal power balance + scaling placeholder.",
                "maturity": "low",
                "validity": "Exploration proxy; do not treat as predictive.",
            }
        ],
        "bootstrap": [
            {
                "id": "bootstrap_proxy_v1",
                "description": "Simple bootstrap current fraction proxy.",
                "maturity": "low",
                "validity": "Proxy; validate against higher-fidelity tools before decision-grade use.",
            }
,
            {
                "id": "bootstrap_improved_proxy_v1",
                "description": "Improved 0-D bootstrap proxy (beta_p/q/eps trend-aware).",
                "maturity": "exploratory",
                "validity": "Still a proxy; intended for deterministic screening and trend studies.",
            },
            {
                "id": "bootstrap_sauter_proxy_v1",
                "description": "Sauter-inspired bootstrap proxy with analytic profile sensitivity (no collisionality fit tables).",
                "maturity": "exploratory",
                "validity": "Not a full Sauter implementation; coefficients are simplified but monotone and bounded.",
            },
        ],
        "profiles": [
            {
                "id": "profiles_off_v1",
                "description": "Pure 0-D; no analytic profile scaffold.",
                "maturity": "stable",
                "validity": "Matches legacy SHAMS behavior.",
            },
            {
                "id": "profiles_analytic_v1",
                "description": "Analytic (parabolic/pedestal) profiles used for diagnostics and bootstrap sensitivity.",
                "maturity": "exploratory",
                "validity": "Profile shapes are declared; used for consistent bookkeeping, not predictive transport.",
            },
            {
                "id": "profiles_pedestal_two_zone_v1",
                "description": "Explicit two-zone pedestal scaffold (core+pedestal piecewise) for trend studies.",
                "maturity": "beta",
                "validity": "Deterministic scaffold; intended for audit-grade trend studies (not predictive transport).",
            },
        ],
        "current_drive": [
            {
                "id": "cd_fixed_gamma_v1",
                "description": "Legacy fixed γ_CD (A/W) current-drive proxy.",
                "maturity": "stable",
                "validity": "Bookkeeping proxy; set γ explicitly from external tools/experience.",
            },
            {
                "id": "cd_actuator_scaling_v1",
                "description": "Actuator-scaled γ_CD proxy with monotone Te/(ne·R0) trend and actuator baselines.",
                "maturity": "beta",
                "validity": "Trend-correct scoping for ECCD/LHCD/NBI; not predictive CD physics.",
            },
        ],
        "exhaust": [
            {
                "id": "divertor_wetted_area_proxy_v1",
                "description": "Legacy wetted-area q_par proxy: q ≈ Psep / [(2πR0)(2πaλq)].",
                "maturity": "stable",
                "validity": "Very simple mapping; treat as conservative screening only.",
            },
            {
                "id": "divertor_two_point_proxy_v1",
                "description": "Two-point-style proxy: q ≈ Psep / (2πR0·λq·f_exp).",
                "maturity": "beta",
                "validity": "More interpretable dependence on λq and flux expansion; still no detachment physics.",
            },
        ],
        "radiation": [
            {
                "id": "radiation_off_v1",
                "description": "Radiation bookkeeping disabled (Prad_core = 0).",
                "maturity": "stable",
                "validity": "Reviewer-safe default for scoping; enable explicitly when needed.",
            },
            {
                "id": "radiation_fractional_v1",
                "description": "Core radiation as a fixed fraction of Pin (legacy).",
                "maturity": "low",
                "validity": "Proxy knob; not impurity-physics-based.",
            },
            {
                "id": "radiation_impurity_mix_v1",
                "description": "Core radiation via brem + sync + impurity line emission with Lz(Te) tables.",
                "maturity": "exploratory",
                "validity": "Bookkeeping model; requires explicit impurity mix and an Lz(Te) database with provenance.",
            },
            {
                "id": "radiation_lz_db_proxy_v1",
                "description": "Lz(Te) database: proxy_v1 (repo-local JSON, hashed).",
                "maturity": "low",
                "validity": "Not validated; replace database with ADAS/experiment-informed curves for publication claims.",
            },
            {
                "id": "radiation_lz_db_radas_openadas_v1",
                "description": "Lz(Te) database: radas_openadas_v1 (RADAS/OpenADAS-derived, hashed).",
                "maturity": "beta",
                "validity": "Authoritative tier: generated from OpenADAS atomic data via a documented pipeline (e.g. RADAS). Hash and source catalog must accompany publication claims.",
            },
            {
                "id": "radiation_lz_db_external_v1",
                "description": "Lz(Te) database: external/custom (hashed at runtime).",
                "maturity": "unknown",
                "validity": "User-supplied tables; review provenance and hash in artifacts.",
            },
        ],
        "magnets": [
            {
                "id": "magnet_tech_axis_v1",
                "description": "Explicit TF technology axis (HTS/LTS/Cu) with SC-margin proxy and copper I^2R coupling.",
                "maturity": "exploratory",
                "validity": "SC margin uses simplified critical-surface proxies; copper I^2R uses winding-pack geometry proxy.",
            }
        ],
        "economics": [
            {
                "id": "coe_proxy_v1",
                "description": "Soft economics proxy (post-feasibility only).",
                "maturity": "exploratory",
                "validity": "Not for procurement/capex decisions; use for trade-space intuition.",
            }
        ],
    }

    return {"schema_version": "model_registry.v1", "options": options}


def selected_model_set(outputs: Dict[str, Any] | None = None, *, overrides: Dict[str, str] | None = None) -> Dict[str, Any]:
    """Determine which model options were used for this run.

    Today, SHAMS is mostly single-path; this function provides the stable
    interface so future upgrades can add choices without breaking artifacts.
    """
    overrides = overrides or {}
    o = outputs or {}

    # Bootstrap selection from inputs->outputs echo
    bs_mode = str(o.get("bootstrap_model", "proxy")).strip().lower()
    if bs_mode == "improved":
        bs_id = "bootstrap_improved_proxy_v1"
    elif bs_mode == "sauter":
        bs_id = "bootstrap_sauter_proxy_v1"
    else:
        bs_id = "bootstrap_proxy_v1"

    # Profiles selection
    prof_mode = str(o.get("profile_model", "none")).strip().lower()
    prof_flag = bool(o.get("profile_mode", False))
    if prof_flag or prof_mode not in ("", "none"):
        prof_id = "profiles_analytic_v1"
    else:
        prof_id = "profiles_off_v1"

    # Radiation selection
    if not bool(o.get("include_radiation", False)):
        rad_id = "radiation_off_v1"
        rad_db_id = "radiation_lz_db_proxy_v1"
    else:
        rmode = str(o.get("radiation_model", "fractional")).strip().lower()
        rad_id = "radiation_impurity_mix_v1" if rmode in ("impurity", "impurity_mix", "mix") else "radiation_fractional_v1"
        db_used = str(o.get("radiation_db_id_used", "")).strip().lower()
        if db_used in ("proxy_v1", "builtin_proxy"):
            rad_db_id = "radiation_lz_db_proxy_v1"
        else:
            rad_db_id = "radiation_lz_db_external_v1"

    
    # Current-drive selection
    cd_used = str(o.get("cd_model_used", o.get("cd_model", "fixed_gamma"))).strip().lower()
    cd_id = "cd_actuator_scaling_v1" if cd_used in ("actuator_scaling", "actuator", "scaled") else "cd_fixed_gamma_v1"

    # Exhaust / divertor selection
    div_mode = str(o.get("divertor_tech_mode", "")).strip().lower()
    ex_id = "divertor_two_point_proxy_v1" if "two_point" in div_mode or "two-point" in div_mode else "divertor_wetted_area_proxy_v1"

    # Profiles: distinguish pedestal variant when analytic profiles are enabled
    try:
        pm = o.get("profile_meta", {}) or {}
        ped_model = str(pm.get("pedestal_model", "")).strip().lower()
        if ped_model == "two_zone":
            prof_id = "profiles_pedestal_two_zone_v1"
    except Exception:
        pass

    selected = {
        "confinement": overrides.get("confinement", "H98_proxy_v1"),
        "bootstrap": overrides.get("bootstrap", bs_id),
        "profiles": overrides.get("profiles", prof_id),
        "current_drive": overrides.get("current_drive", cd_id),
        "exhaust": overrides.get("exhaust", ex_id),
        "radiation": overrides.get("radiation", rad_id),
        "radiation_db": overrides.get("radiation_db", rad_db_id),
        "magnets": overrides.get("magnets", "magnet_tech_axis_v1"),
        "economics": overrides.get("economics", "coe_proxy_v1"),
    }
    return {"schema_version": "model_set.v1", "selected": selected}