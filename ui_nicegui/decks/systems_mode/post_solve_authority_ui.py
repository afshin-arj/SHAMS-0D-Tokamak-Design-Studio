"""Post-solve plant & exhaust authority panels — inline under key results."""

from __future__ import annotations

import json
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

_PLANT_CERT_KEYS = ("impurity_detachment", "plant_economics", "industrial_cost")


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
