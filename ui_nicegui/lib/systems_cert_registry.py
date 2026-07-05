"""Certification registry for Systems Mode — expert-facing titles, no version codes."""

from __future__ import annotations

from typing import Any, List, Tuple

# (title, cache_key, module, certify_fn, table_fn, mode)
# mode: io | out_only | out_pos | out_fn | out_call | io_call
CERT_REGISTRY: List[Tuple[str, str, str, str, str, str]] = [
    ("Stability & control margins", "stability_control", "src.certification.stability_control_certification_v374", "certify_stability_control_margins", "certification_table_rows", "io"),
    ("Control & actuation authority", "control_actuation", "src.certification.control_actuation_certification_v378", "certify_control_actuation", "certification_table_rows", "io"),
    ("Transport & confinement credibility", "transport_confinement", "src.certification.transport_confinement_certification_v376", "certify_transport_confinement", "certification_table_rows", "io"),
    ("Transport profile proxies", "transport_profile", "src.certification.transport_profile_certification_v382", "certify_transport_profile", "certification_table_rows", "io"),
    ("Materials & lifetime tightening", "materials_lifetime", "src.certification.materials_lifetime_certification_v384", "certify_materials_lifetime_v384", "certification_table_rows", "io"),
    ("Current drive authority", "current_drive", "src.certification.current_drive_certification_v381", "evaluate_current_drive_authority", "certification_table_rows", "out_pos"),
    ("Current drive actuator mix", "cd_library", "src.certification.current_drive_library_certification_v395", "certify_current_drive_library_v395", "certification_table_rows", "out_only"),
    ("Disruption & quench severity", "disruption_quench", "src.certification.disruption_quench_certification_v377", "certify_disruption_quench", "certification_table_rows", "io"),
    ("Structural stress limits", "structural_stress", "src.certification.structural_stress_certification_v389", "certify_structural_stress_v389", "", "out_fn"),
    ("Neutronics & activation", "neutronics_activation", "src.certification.neutronics_activation_certification_v390", "certify_neutronics_activation_v390", "", "out_fn"),
    ("Shield attenuation", "shield_attenuation", "src.certification.neutronics_shield_attenuation_certification_v392", "certify_neutronics_shield_attenuation_v392", "", "out_fn"),
    ("Plant availability & reliability", "availability", "src.certification.availability_reliability_certification_v391", "certify_availability_reliability_v391", "", "out_fn"),
    ("Impurity radiation & detachment", "impurity_detachment", "src.certification.impurity_radiation_detachment_certification_v380", "evaluate_impurity_radiation_detachment_authority", "certification_table_rows", "out_call"),
    ("Plant economics (CAPEX / OPEX / LCOE)", "plant_economics", "src.certification.plant_economics_certification_v383", "evaluate_plant_economics_authority_v383", "certification_table_rows", "io_call"),
    ("Industrial cost depth", "industrial_cost", "src.certification.cost_authority_certification_v388", "evaluate_cost_authority_v388", "certification_table_rows", "io_call"),
]

# Post-solve bundle derived directly from solver outputs (not a separate cert module).
EXHAUST_AUTHORITY_TITLE = "Divertor & exhaust heat flux"


def import_attr(module_path: str, name: str):
    try:
        mod = __import__(module_path, fromlist=[name])
    except ImportError:
        mod = __import__(module_path.replace("src.", ""), fromlist=[name])
    return getattr(mod, name)


def _normalize_cert_result(result: Any) -> Any:
    if hasattr(result, "to_dict") and callable(result.to_dict):
        return result.to_dict()
    if hasattr(result, "__dict__") and not isinstance(result, dict):
        return dict(result.__dict__)
    return result


def run_certify(spec: Tuple[str, str, str, str, str, str], outs: dict, ins: dict) -> Any:
    _, _, mod_path, fn_name, _, mode = spec
    fn = import_attr(mod_path, fn_name)
    if mode == "io":
        return _normalize_cert_result(fn(outputs=dict(outs), inputs=dict(ins)))
    if mode == "io_call":
        return _normalize_cert_result(fn(dict(outs), dict(ins)))
    if mode == "out_only":
        return _normalize_cert_result(fn(outputs=dict(outs)))
    if mode == "out_pos":
        return _normalize_cert_result(fn(dict(outs)))
    if mode == "out_call":
        return _normalize_cert_result(fn(dict(outs)))
    if mode == "out_fn":
        return _normalize_cert_result(fn(dict(outs)))
    return _normalize_cert_result(fn(outputs=dict(outs), inputs=dict(ins)))


def cert_to_table(spec: Tuple[str, str, str, str, str, str], cert: Any) -> tuple[list, list] | None:
    _, _, mod_path, _, rows_fn, _mode = spec
    if not rows_fn:
        return None
    try:
        table_fn = import_attr(mod_path, rows_fn)
        raw = cert if isinstance(cert, dict) else cert.__dict__ if hasattr(cert, "__dict__") else cert
        result = table_fn(raw)
        if isinstance(result, dict):
            return [result], list(result.keys())
        if isinstance(result, tuple) and len(result) == 2:
            rows, cols = result
            if rows and isinstance(rows[0], dict):
                return rows, list(rows[0].keys())
            if rows and cols:
                return [dict(zip(cols, r)) for r in rows], list(cols)
    except Exception:
        pass
    return None


def cert_tab_label(title: str, *, max_len: int = 22) -> str:
    t = str(title or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"
