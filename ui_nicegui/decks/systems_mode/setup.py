"""Systems Mode setup — target specification."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.pd_overlay_knobs import render_overlay_numeric_panels
from ui_nicegui.lib.pd_panel_labels import overlay_caption, overlay_display_label
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem, validate_systems_problem
from ui_nicegui.session import DesignSession

_TRANSPORT_OVERLAY_FLAGS = (
    "include_transport_contracts_v371",
    "include_transport_envelope_v396",
    "include_profile_proxy_v397",
)
_TRANSPORT_DEFAULTS = {
    "include_transport_contracts_v371": False,
    "include_transport_envelope_v396": True,
    "include_profile_proxy_v397": False,
}

_VAR_LABELS = {
    "Ip_MA": "I_p [MA]",
    "fG": "f_G [-]",
    "Paux_MW": "P_aux [MW]",
}


def _sync_solve_knobs(session: DesignSession) -> None:
    """Suggest coupled knobs when multiple performance targets are active."""
    if session.systems_use_h and not session.systems_solve_ip:
        session.systems_solve_ip = True
    if session.systems_use_q and session.systems_use_h and not session.systems_solve_fg:
        session.systems_solve_fg = True


def _set_bounds_override(session: DesignSession, key: str, field: str, value: float) -> None:
    bo = dict(session.systems_bounds_overrides or {})
    entry = dict(bo.get(key) or {})
    entry[field] = float(value)
    bo[key] = entry
    session.systems_bounds_overrides = bo


def _render_variable_bounds(session: DesignSession, variables: dict) -> None:
    if not variables:
        return
    ui.separator().classes("q-my-sm")
    ui.label("Search / solve bounds (x₀, lo, hi)").classes("text-subtitle2")
    ui.label("Defaults scale from the baseline; tighten or widen for precheck and Newton solve.").classes(
        "text-caption text-grey q-mb-sm"
    )
    for key, (x0, lo, hi) in variables.items():
        label = _VAR_LABELS.get(key, key)
        with ui.row().classes("gap-2 flex-wrap items-end q-mb-xs"):
            ui.number(
                f"{label} x₀",
                value=float(x0),
                step=0.01,
                on_change=lambda e, k=key: _set_bounds_override(session, k, "x0", float(e.value or 0)),
            ).classes("w-28")
            ui.number(
                "lo",
                value=float(lo),
                step=0.01,
                on_change=lambda e, k=key: _set_bounds_override(session, k, "lo", float(e.value or 0)),
            ).classes("w-28")
            ui.number(
                "hi",
                value=float(hi),
                step=0.01,
                on_change=lambda e, k=key: _set_bounds_override(session, k, "hi", float(e.value or 0)),
            ).classes("w-28")


def _render_transport_authority(session: DesignSession) -> None:
    ui.separator().classes("q-my-md")
    ui.label("Transport & profile authority caps").classes("text-subtitle2")
    ui.label(
        "Shared with Point Designer — when enabled, caps feed precheck and target solve through the frozen evaluator."
    ).classes("text-caption text-grey q-mb-sm")

    for flag in _TRANSPORT_OVERLAY_FLAGS:
        default = _TRANSPORT_DEFAULTS[flag]
        session.overlay.setdefault(flag, default)
        ui.checkbox(
            overlay_display_label(flag),
            value=bool(session.overlay.get(flag, default)),
            on_change=lambda e, k=flag: session.overlay.__setitem__(k, bool(e.value)),
        )
        ui.label(overlay_caption(flag)).classes("text-caption text-grey q-pl-lg q-mb-sm")

    render_overlay_numeric_panels(session, flags_filter=set(_TRANSPORT_OVERLAY_FLAGS))


def _render_baseline_summary(session: DesignSession) -> None:
    inp = session.inputs or {}
    ui.label("Starting point (Point Designer — edit under Starting machine →)").classes("text-caption q-mb-xs")
    with ui.row().classes("gap-3 flex-wrap q-mb-sm"):
        for key, label in (
            ("R0_m", "R₀ [m]"),
            ("Bt_T", "B₀ [T]"),
            ("Ip_MA", "I_p [MA]"),
            ("Paux_MW", "P_aux [MW]"),
            ("fG", "f_G [-]"),
        ):
            val = inp.get(key, "-")
            with ui.card().classes("p-2"):
                ui.label(label).classes("text-caption text-grey")
                ui.label(str(val)).classes("text-body2")


def render_setup(session: DesignSession) -> None:
    ui.label("Target specification").classes("text-subtitle1")
    ui.label(
        "Left: performance targets the solver must hit. Right: which plasma/plant knobs it may adjust within bounds."
    ).classes("text-caption text-grey q-mb-sm")

    if session.paux_for_q is not None:
        ui.label(
            f"Q definition uses P_aux for Q = {float(session.paux_for_q):.4g} MW "
            "(from Point Designer operating targets)."
        ).classes("text-caption text-info q-mb-sm")

    _render_baseline_summary(session)
    _, targets, variables = resolve_systems_problem(session)
    valid, msg = validate_systems_problem(targets, variables)

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("What should the point achieve?").classes("text-subtitle2")

            def _on_q(e) -> None:
                session.systems_use_q = bool(e.value)
                _sync_solve_knobs(session)

            def _on_h(e) -> None:
                session.systems_use_h = bool(e.value)
                _sync_solve_knobs(session)

            ui.checkbox(
                "Match fusion gain Q_DT_eqv",
                value=session.systems_use_q,
                on_change=_on_q,
            )
            ui.number(
                "Q_DT_eqv target [-]",
                value=session.systems_q_target,
                min=0.5,
                step=0.5,
                on_change=lambda e: setattr(session, "systems_q_target", float(e.value or 10.0)),
            ).classes("w-full")
            ui.checkbox(
                "Match confinement H98(y,2)",
                value=session.systems_use_h,
                on_change=_on_h,
            )
            ui.number(
                "H98(y,2) target [-]",
                value=session.systems_h_target,
                min=0.05,
                step=0.05,
                on_change=lambda e: setattr(session, "systems_h_target", float(e.value or 1.15)),
            ).classes("w-full")

            def _on_pnet(e) -> None:
                session.systems_use_pnet = bool(e.value)
                if session.systems_use_pnet:
                    session.systems_use_pfus = False

            def _on_pfus(e) -> None:
                session.systems_use_pfus = bool(e.value)
                if session.systems_use_pfus:
                    session.systems_use_pnet = False
                    session.systems_solve_paux = True

            ui.checkbox(
                "Match net electric P_net",
                value=session.systems_use_pnet,
                on_change=_on_pnet,
            )
            ui.number(
                "P_net target [MW(e)]",
                value=session.systems_pnet_target,
                min=5.0,
                step=5.0,
                on_change=lambda e: setattr(session, "systems_pnet_target", float(e.value or 50.0)),
            ).classes("w-full")
            ui.checkbox(
                "Match fusion power Pfus_DT_adj",
                value=session.systems_use_pfus,
                on_change=_on_pfus,
            )
            ui.number(
                "Pfus_DT_adj target [MW]",
                value=session.systems_pfus_target,
                min=10.0,
                step=10.0,
                on_change=lambda e: setattr(session, "systems_pfus_target", float(e.value or 200.0)),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.label("What may the solver adjust?").classes("text-subtitle2")
            ui.checkbox(
                "Plasma current I_p [MA]",
                value=session.systems_solve_ip,
                on_change=lambda e: setattr(session, "systems_solve_ip", bool(e.value)),
            )
            ui.checkbox(
                "Greenwald fraction f_G [-]",
                value=session.systems_solve_fg,
                on_change=lambda e: setattr(session, "systems_solve_fg", bool(e.value)),
            )
            ui.checkbox(
                "Auxiliary power P_aux [MW]",
                value=session.systems_solve_paux,
                on_change=lambda e: setattr(session, "systems_solve_paux", bool(e.value)),
            )
            _, targets2, variables2 = resolve_systems_problem(session)
            _render_variable_bounds(session, variables2)

    _, targets, variables = resolve_systems_problem(session)
    valid, msg = validate_systems_problem(targets, variables)
    if valid:
        ui.label(
            f"Ready: targets={', '.join(targets.keys())} | adjustable={', '.join(variables.keys())}"
        ).classes("text-caption text-positive q-mt-sm")
    elif targets or variables:
        ui.label(msg).classes("text-caption text-orange q-mt-sm")
    else:
        ui.label("Enable at least one target and one adjustable variable.").classes("text-orange q-mt-sm")

    _render_transport_authority(session)
