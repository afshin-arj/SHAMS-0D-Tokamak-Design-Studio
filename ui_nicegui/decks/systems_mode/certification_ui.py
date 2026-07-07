"""Systems Mode certifications — full authority bundle registry (expert titles)."""

from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.lib.systems_artifact import fetch_systems_artifact
from ui_nicegui.lib.systems_cert_registry import CERT_REGISTRY, cert_tab_label, cert_to_table, run_certify
from ui_nicegui.lib.systems_plant_authority import warm_post_solve_cert_cache
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_certification_panels(session: DesignSession) -> None:
    art = fetch_systems_artifact(session)
    outs = (art or {}).get("outputs") if isinstance(art, dict) else None
    ins = (art or {}).get("inputs") if isinstance(art, dict) else None
    can = isinstance(outs, dict) and isinstance(ins, dict)

    ui.label("Authority certifications").classes("text-subtitle2 q-mt-md")
    ui.label("Algebraic audit bundles from the last solve — no re-solve.").classes("text-caption q-mb-sm")
    if not can:
        ui.label("Run target solve first.").classes("text-grey")
        return

    warm_post_solve_cert_cache(session, outs, ins)
    cache = dict(session.systems_cert_cache or {})

    with ui.tabs().classes("w-full") as tabs:
        tab_objs = [ui.tab(cert_tab_label(title)) for title, *_ in CERT_REGISTRY]

    with ui.tab_panels(tabs, value=tab_objs[0]).classes("w-full"):
        for i, spec in enumerate(CERT_REGISTRY):
            title, key, *_ = spec
            with ui.tab_panel(tab_objs[i]):
                cert = cache.get(key)

                async def _compute(_spec=spec, _key=key, _title=title) -> None:
                    def _run():
                        return run_certify(_spec, outs, ins)

                    try:
                        result = await run.io_bound(_run)
                        if hasattr(result, "to_dict") and callable(result.to_dict):
                            result = result.to_dict()
                        elif hasattr(result, "__dict__") and not isinstance(result, dict):
                            result = dict(result.__dict__)
                        c = dict(session.systems_cert_cache or {})
                        c[_key] = result
                        session.systems_cert_cache = c
                        ui.notify(f"{_title} computed", type="positive")
                    except Exception as exc:
                        ui.notify(f"Certification failed: {exc}", type="negative")

                ui.button("Compute (cache)", on_click=_compute).props("outline dense q-mb-sm")
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
                    ui.button(
                        "Download JSON",
                        on_click=lambda c=cert, k=key: ui.download(
                            json.dumps(c, indent=2, sort_keys=True, default=str).encode("utf-8"),
                            f"authority_{k}.json",
                        ),
                    ).props("flat dense")
                elif cert is not None:
                    render_json_blob(cert if isinstance(cert, dict) else str(cert))
                else:
                    ui.label("Not computed — click Compute (cache).").classes("text-caption text-grey")
