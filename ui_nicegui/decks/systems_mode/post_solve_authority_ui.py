"""Post-solve plant & exhaust authority panels — inline under key results."""

from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.systems_cert_registry import CERT_REGISTRY, cert_to_table, run_certify
from ui_nicegui.lib.systems_cert_registry import EXHAUST_AUTHORITY_TITLE
from ui_nicegui.lib.systems_plant_authority import (
    build_exhaust_authority_bundle,
    exhaust_table_row,
    exhaust_unit_suspect,
    warm_post_solve_cert_cache,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

_PLANT_CERT_KEYS = (
    "impurity_detachment",
    "plant_economics",
    "industrial_cost",
    "structural_stress",
    "neutronics_activation",
)


def _fmt(x, *, digits: int = 3) -> str:
    try:
        v = float(x)
        if v != v:
            return "—"
        return f"{v:.{digits}g}"
    except (TypeError, ValueError):
        return "—"


def render_post_solve_authority(
    session: DesignSession,
    outs: dict,
    ins: dict,
    *,
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    _authority_body(session, outs, ins, on_refresh=on_refresh)


@ui.refreshable
def _authority_body(
    session: DesignSession,
    outs: dict,
    ins: dict,
    *,
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Plant & exhaust authority (post-solve)").classes("text-subtitle2 q-mt-md")
    ui.label("Algebraic bundles from the last solve — no hidden re-solve.").classes("text-caption q-mb-sm")

    warm_post_solve_cert_cache(session, outs, ins, keys=list(_PLANT_CERT_KEYS))
    bundle = getattr(session, "systems_exhaust_authority", None)
    if not isinstance(bundle, dict):
        bundle = build_exhaust_authority_bundle(outs)
        session.systems_exhaust_authority = bundle

    with ui.expansion(EXHAUST_AUTHORITY_TITLE, icon="whatshot").classes("w-full"):
        row = exhaust_table_row(bundle)
        ui.table(
            columns=[{"name": k, "label": k, "field": k} for k in row.keys()],
            rows=[row],
            row_key=list(row.keys())[0],
        ).classes("w-full")
        if exhaust_unit_suspect(bundle):
            ui.label(
                "Divertor heat flux magnitude looks unit-suspect (>10⁵ MW/m² flag). "
                "Screening flag only — physics truth unchanged."
            ).classes("text-orange text-caption")

    # Magnet / tritium strips from L0 outs (PROXY captions — not a second physics editor).
    from ui_nicegui.components.kpi_row import kpi_row
    from ui_nicegui.lib.pd_parity_helpers import magnet_v400_summary

    v400 = magnet_v400_summary(outs)
    has_magnet_proxy = any(
        outs.get(k) is not None
        for k in ("B_peak_T", "hts_margin", "sc_margin_v410", "sc_margin", "magnet_technology", "magnet_tech")
    ) or v400 is not None
    if has_magnet_proxy:
        with ui.expansion("Magnet technology margins (read-only PROXY)", icon="bolt").classes("w-full"):
            ui.markdown(
                "PROXY / screening fields from frozen outputs — enable magnet technology "
                "margins authority in Point Designer for full margins."
            ).classes("text-caption text-grey q-mb-xs")
            b_peak = outs.get("B_peak_T")
            b_allow = outs.get("B_peak_allow_T")
            b_margin = float("nan")
            try:
                bp = float(b_peak)
                ba = float(b_allow)
                if bp == bp and ba == ba and ba > 0.0:
                    b_margin = (ba - bp) / ba
            except (TypeError, ValueError):
                pass
            kpi_row([
                ("B_peak (T)", _fmt(b_peak)),
                ("B_peak allow (T)", _fmt(b_allow)),
                ("B-field margin", _fmt(b_margin, digits=3)),
                ("Magnet tech", str(outs.get("magnet_technology", outs.get("magnet_tech", "—")))),
            ])
            kpi_row([
                ("HTS margin", _fmt(outs.get("hts_margin"), digits=2)),
                ("SC margin", _fmt(outs.get("sc_margin_v410", outs.get("sc_margin")), digits=2)),
                ("", ""),
                ("", ""),
            ])
            if v400:
                kpi_row([
                    ("Combined magnet margin", _fmt(v400.get("combined_margin"), digits=3)),
                    ("Magnet margin tier", str(v400.get("tier") or "—")),
                    ("Dominant magnet limit", str(v400.get("dominant") or "—")),
                    ("Dominant margin", _fmt(v400.get("dominant_margin"), digits=3)),
                ])

    has_tbr = any(
        outs.get(k) is not None for k in ("TBR", "tbr_proxy_v403", "neutron_wall_load_MW_m2")
    ) or ins.get("TBR_min") is not None
    if has_tbr:
        with ui.expansion("Tritium / TBR (read-only PROXY)", icon="science").classes("w-full"):
            ui.markdown(
                "TBR is always a screening-level breeding-ratio **proxy** (analytic thickness/coverage fit) — "
                "no certified neutron-transport (MCNP/OpenMC-grade) TBR model exists in L0."
            ).classes("text-caption text-grey q-mb-xs")
            kpi_row([
                ("TBR (proxy)", _fmt(outs.get("TBR", outs.get("tbr_proxy_v403")), digits=2)),
                ("TBR min (input)", _fmt(outs.get("TBR_min", ins.get("TBR_min")), digits=2)),
                ("NWL (MW/m²)", _fmt(outs.get("neutron_wall_load_MW_m2"), digits=2)),
                ("Tight closure", "ON" if bool(outs.get("include_tritium_tight_closure")) else "off"),
            ])

    elm_on = bool(outs.get("include_elm_transient_heat_v409"))
    try:
        _elm_qf = float(outs.get("elm_transient_q_parallel_MW_m2_v409", float("nan")))
    except (TypeError, ValueError):
        _elm_qf = float("nan")
    if elm_on or _elm_qf == _elm_qf:
        with ui.expansion("ELM transient heat (screening)", icon="flash_on").classes("w-full"):
            ui.label(
                "Transient parallel heat-flux screening proxy — not a SOLPS ELM model."
            ).classes("text-caption text-grey q-mb-xs")
            elm_q = outs.get("elm_transient_q_parallel_MW_m2_v409")
            q_max = outs.get("elm_transient_q_parallel_max_MW_m2_v409")
            margin = float("nan")
            try:
                qq = float(elm_q)
                qm = float(q_max)
                if qq == qq and qm == qm and qm > 0.0:
                    margin = (qm - qq) / qm
            except (TypeError, ValueError):
                pass
            kpi_row([
                ("ELM overlay", "ON" if elm_on else "off"),
                ("ELM q∥ proxy (MW/m²)", _fmt(elm_q, digits=1)),
                ("ELM q∥ max", _fmt(q_max, digits=1)),
                ("ELM margin (frac)", _fmt(margin, digits=3)),
            ])

    cache = dict(session.systems_cert_cache or {})
    for key in _PLANT_CERT_KEYS:
        spec = next((s for s in CERT_REGISTRY if s[1] == key), None)
        if not spec:
            continue
        cert = cache.get(key)
        with ui.expansion(spec[0], icon="verified").classes("w-full"):
            if isinstance(cert, dict):
                table = cert_to_table(spec, cert)
                if table:
                    rows, cols = table
                    ui.table(
                        columns=[{"name": c, "label": c, "field": c} for c in cols],
                        rows=rows if rows and isinstance(rows[0], dict) else [],
                        row_key=cols[0] if cols else "name",
                    ).classes("w-full")
                else:
                    render_json_blob(cert)
            else:
                ui.label("Bundle unavailable for this artifact.").classes("text-caption text-grey")

    def _refresh() -> None:
        session.systems_exhaust_authority = build_exhaust_authority_bundle(outs)
        new_cache = dict(session.systems_cert_cache or {})
        for key in _PLANT_CERT_KEYS:
            spec = next((s for s in CERT_REGISTRY if s[1] == key), None)
            if not spec:
                continue
            try:
                new_cache[key] = run_certify(spec, outs, ins)
            except Exception as exc:
                ui.notify(f"{spec[0]} failed: {exc}", type="negative")
                return
        session.systems_cert_cache = new_cache
        ui.notify("Authority bundles refreshed", type="positive")
        _authority_body.refresh()
        if on_refresh:
            on_refresh()

    ui.button("Refresh authority bundles", icon="refresh", on_click=_refresh).props("outline dense q-mt-sm")
