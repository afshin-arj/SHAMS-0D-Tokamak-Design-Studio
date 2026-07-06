"""Session helpers mirroring ui/session_api.py for NiceGUI."""

from __future__ import annotations



import time

from typing import Any, Dict, List, Optional



from ui_nicegui.lib.pd_artifact_helpers import build_point_artifact
from ui_nicegui.lib.pd_overlay_catalog import ALL_OVERLAY_KEYS
from ui_nicegui.lib.pd_run_summary import compute_run_summary_from_out

from ui_nicegui.lib.verdict_core import constraint_table_rows

from ui_nicegui.session import DesignSession





def set_point_evaluation(

    session: DesignSession,

    *,

    outputs: Dict[str, Any],

    inputs: Optional[Dict[str, Any]] = None,

    constraints: Optional[List[Any]] = None,

) -> None:

    session.last_eval = dict(outputs)

    session.pd_last_outputs = dict(outputs)
    subs = session.knobs.get("_subsystem_enabled")
    if isinstance(subs, dict):
        outputs = dict(outputs)
        outputs["_subsystem_enabled"] = dict(subs)
    for key in ("_warn_frac_max", "_warn_frac_min"):
        if key in session.knobs:
            outputs = dict(outputs)
            outputs[key] = float(session.knobs[key])
    session.pd_last_outputs = outputs
    session.last_eval = outputs

    inp_dict = dict(inputs or session.inputs)

    if inputs is not None:

        session.inputs.update(inputs)



    forensics = session.pd_last_forensics if isinstance(session.pd_last_forensics, dict) else None

    artifact = build_point_artifact(

        inputs=inp_dict,

        outputs=dict(outputs),

        design_intent=str(session.design_intent),

        forensics=forensics if forensics and forensics.get("status") != "error" else None,

    )

    if constraints is not None and not artifact.get("constraints"):

        artifact["constraints"] = list(constraints)

    elif not artifact.get("constraints"):

        rows = constraint_table_rows(outputs)

        artifact["constraints"] = rows

    if isinstance(outputs, dict) and outputs:
        artifact["run_summary"] = compute_run_summary_from_out(outputs)

    session.pd_last_artifact = artifact

    session.pd_last_run_ts = time.time()
    if inputs is not None:
        from ui_nicegui.lib.pd_solver_helpers import compute_pd_inputs_hash

        session.pd_last_inputs_hash = compute_pd_inputs_hash(session)


def clear_point_designer(session: DesignSession) -> None:
    """Reset Point Designer cached evaluation (mirrors Streamlit Control Deck clear)."""
    session.last_eval = None
    session.pd_last_outputs = None
    session.pd_last_artifact = None
    session.pd_last_run_ts = None
    session.pd_last_forensics = None
    session.last_error = None
    session.phase_envelopes_last = None
    session.uq_contract_last = None
    session.pd_solver_trace = []
    session.pd_last_log_lines = []
    session.pd_last_inputs_hash = None
    session.pd_current_inputs_hash = None
    session.pd_frontier_last = None
    session.pd_last_summary_pdf_bytes = None
    session.pd_pert_scan_rows = []
    session.pd_last_radial_png_bytes = None


def apply_template_overrides(session: DesignSession, overrides: dict[str, Any]) -> None:
    """Merge industrial template overrides into session inputs + overlay."""
    if not isinstance(overrides, dict):
        return
    seed_overlay_defaults(session.overlay)
    for key, val in overrides.items():
        if key in session.inputs or key in {
            "R0_m", "a_m", "kappa", "delta", "Bt_T", "Ip_MA", "Ti_keV", "fG", "Paux_MW",
            "Ti_over_Te", "magnet_technology", "Tcoil_K", "t_shield_m", "fuel_mode",
            "confinement_scaling", "zeff", "dilution_fuel",
        }:
            session.inputs[key] = val
        elif key in ALL_OVERLAY_KEYS or key.startswith("include_"):
            session.overlay[key] = val
        else:
            session.knobs[key] = val





def get_point_outputs(session: DesignSession) -> Optional[Dict[str, Any]]:

    out = session.pd_last_outputs or session.last_eval

    return dict(out) if isinstance(out, dict) else None

