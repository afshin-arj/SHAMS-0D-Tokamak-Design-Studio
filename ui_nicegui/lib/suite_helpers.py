"""System Suite shared helpers — run-lock, tab summaries, authority ledger, handoffs."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.lib.systems_plant_authority import build_exhaust_authority_bundle, exhaust_table_row
from ui_nicegui.session import DesignSession

SUITE_RUNLOCK_OWNER = "SystemSuite"


def _fin(v: Any, fmt: str = ".2f") -> str:
    try:
        f = float(v)
        if not math.isfinite(f):
            return "-"
        return format(f, fmt)
    except (TypeError, ValueError):
        return "-"


def try_acquire_suite_lock(session: DesignSession, task: str) -> bool:
    locked, existing, is_owner = runlock_status(SUITE_RUNLOCK_OWNER)
    if locked and not is_owner:
        ui.notify(f"Blocked — {existing or 'another task'} is running.", type="warning")
        return False
    if not runlock_acquire(task, SUITE_RUNLOCK_OWNER):
        ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
        return False
    session.suite_running = True
    return True


def release_suite_lock(session: DesignSession) -> None:
    runlock_release(SUITE_RUNLOCK_OWNER)
    session.suite_running = False


def authority_version_badges(out: dict) -> List[str]:
    if not isinstance(out, dict):
        return []
    checks = [
        ("magnet_v400_enabled", "v400 magnets"),
        ("nm_authority_v401_enabled", "v401 neutronics"),
        ("nuclear_data_authority_v407_enabled", "v407 nuclear data"),
        ("structural_stress_v389_enabled", "v389 structural"),
        ("tritium_authority_v405_enabled", "v405 tritium"),
        ("cd_mix_plant_ledger_v408_enabled", "v408 plant ledger"),
    ]
    return [label for key, label in checks if bool(out.get(key))]


def lifetime_binding_summary(lr) -> Dict[str, Any]:
    margins = {
        "FW dpa": getattr(lr, "fw_dpa_margin", float("nan")),
        "Pulse cycles": getattr(lr, "cycles_margin", float("nan")),
        "TBR": getattr(lr, "tbr_margin", float("nan")),
    }
    binding = []
    worst_name = ""
    worst_val = float("inf")
    for name, m in margins.items():
        if math.isfinite(m) and m < 0:
            binding.append(name)
            if m < worst_val:
                worst_val = m
                worst_name = name
    return {
        "binding": binding,
        "worst_name": worst_name,
        "worst_margin": worst_val if binding else float("nan"),
        "posture": "LIFETIME BINDING" if binding else "WITHIN BUDGET",
    }


def envelope_posture_summary(session: DesignSession) -> str:
    pc = session.profile_contracts_v362_last if isinstance(session.profile_contracts_v362_last, dict) else {}
    parts: List[str] = []
    if pc:
        rob = "robust YES" if pc.get("robust_feasible") else "robust NO"
        opt = "optimistic YES" if pc.get("optimistic_feasible") else "optimistic NO"
        parts.append(f"Profile corners: {opt}, {rob}")
    if isinstance(session.suite_parity_last_report, dict):
        rows = session.suite_parity_last_report.get("summary_rows") or []
        n = len(rows)
        parts.append(f"Parity: {n} case(s) on record")
    if isinstance(session.suite_campaign_summary, dict):
        n_f = session.suite_campaign_summary.get("n_feasible", "?")
        n_t = session.suite_campaign_summary.get("n_total", "?")
        parts.append(f"Campaign: {n_f}/{n_t} feasible")
    return " · ".join(parts) if parts else "Run envelope tools or exports to populate posture."


def render_tab_summary_strip(posture: str, *, detail: str = "", kpis: Optional[List[tuple[str, str]]] = None) -> None:
    verdict_banner(posture, detail=detail)
    if kpis:
        kpi_row(kpis)


def render_authority_ledger(point_out: dict, *, expert: bool = False) -> None:
    from ui_nicegui.lib.pd_parity_helpers import magnet_v400_summary, power_ledger_badged_rows

    ui.label("Authority ledger (from last Point Designer evaluation)").classes("text-subtitle2")
    ui.label("Read-only drill-down — authority modules run at evaluate time, not in Suite.").classes(
        "text-caption q-mb-sm"
    )

    mag = magnet_v400_summary(point_out)
    if mag:
        kpi_row([
            ("Magnet v400 tier", str(mag.get("tier", "-"))),
            ("Combined margin", _fin(mag.get("combined_margin"), ".3f")),
            ("Dominant limiter", str(mag.get("dominant", "-"))),
        ])
    else:
        ui.label("Magnet v400 authority not enabled on this point.").classes("text-caption text-grey")

    exh = build_exhaust_authority_bundle(point_out)
    row = exhaust_table_row(exh)
    if any(math.isfinite(float(v)) if isinstance(v, (int, float)) else False for v in row.values()):
        kpi_row([(k, _fin(v, ".3g") if isinstance(v, (int, float)) else str(v)) for k, v in list(row.items())[:4]])
    else:
        ui.label("Exhaust authority fields not populated.").classes("text-caption text-grey")

    kpi_row([
        ("TBR", _fin(point_out.get("TBR", point_out.get("tbr_proxy")))),
        ("FW dpa/yr", _fin(point_out.get("fw_dpa_per_year"))),
        ("TF struct margin v389", _fin(point_out.get("tf_struct_margin_v389"), ".3f")),
        ("NM margin v401", _fin(point_out.get("nm_min_margin_frac_v401"), ".3f")),
    ])

    if expert:
        with ui.expansion("Plasma power ledger", icon="bolt").classes("w-full q-mt-sm"):
            rows = power_ledger_badged_rows(point_out, include_radiation=True)
            if rows:
                ui.table(
                    columns=[
                        {"name": "item", "label": "Item", "field": "item", "align": "left"},
                        {"name": "MW", "label": "MW", "field": "MW", "align": "left"},
                        {"name": "type", "label": "Tier", "field": "type", "align": "left"},
                    ],
                    rows=rows,
                    row_key="item",
                ).classes("w-full")


def render_suite_handoffs(session: DesignSession, point_out: dict) -> None:
    from ui_nicegui.lib.compare_helpers import artifact_from_point, send_row_to_compare_slot, store_compare_slot
    from ui_nicegui.lib.navigation import switch_deck

    ui.label("Cross-deck handoffs").classes("text-subtitle2")
    ui.label(
        "Send the loaded point or a campaign row to Compare; open Control Room for audit on the same artifact."
    ).classes("text-caption text-grey q-mb-sm")

    def _point_compare(slot: str) -> None:
        art = artifact_from_point(session)
        if not art:
            ui.notify("No Point Designer evaluation loaded.", type="warning")
            return
        store_compare_slot(session, art, slot, label="System Suite point")
        ui.notify(f"Loaded point into Compare slot {slot}", type="positive")
        log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffCompare", {"slot": slot, "source": "point"})

    def _open_cr() -> None:
        if not isinstance(point_out, dict) or not point_out:
            ui.notify("No evaluation loaded.", type="warning")
            return
        switch_deck("Control Room")
        ui.notify("Opened Control Room — study uses pd_last_artifact.", type="info")
        log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffControlRoom", {})

    def _open_pd() -> None:
        switch_deck("Point Designer")
        ui.notify("Opened Point Designer — re-evaluate after input changes.", type="info")

    row_idx = ui.number("Campaign row # (for Compare)", value=0, min=0, step=1).classes("w-48")

    def _campaign_compare(slot: str) -> None:
        preview = session.suite_campaign_results_preview
        if not isinstance(preview, list) or not preview:
            ui.notify("Run campaign batch first.", type="warning")
            return
        ix = int(row_idx.value or 0)
        ix = max(0, min(ix, len(preview) - 1))
        row = preview[ix]
        if not isinstance(row, dict):
            ui.notify("Invalid campaign row.", type="negative")
            return
        try:
            send_row_to_compare_slot(session, dict(row), slot, label="System Suite campaign")
            ui.notify(f"Campaign row {ix} → Compare slot {slot} (re-evaluated)", type="positive")
            log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffCompare", {"slot": slot, "source": "campaign", "row": ix})
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 flex-wrap"):
        ui.button("Point → Compare A", icon="compare", on_click=lambda: _point_compare("A")).props("outline")
        ui.button("Point → Compare B", icon="compare", on_click=lambda: _point_compare("B")).props("outline")
        ui.button("Campaign row → Compare A", icon="compare", on_click=lambda: _campaign_compare("A")).props("flat outline")
        ui.button("Campaign row → Compare B", icon="compare", on_click=lambda: _campaign_compare("B")).props("flat outline")
        ui.button("Open Control Room", icon="gavel", on_click=_open_cr).props("flat outline")
        ui.button("Open Point Designer", icon="design_services", on_click=_open_pd).props("flat outline")


def render_export_bar(session: DesignSession) -> None:
    ui.label("Available exports").classes("text-subtitle2")
    with ui.row().classes("gap-2 flex-wrap q-mb-sm"):
        data = session.suite_campaign_jsonl_bytes
        if isinstance(data, (bytes, bytearray)):
            ui.button(
                "Download campaign results.jsonl",
                icon="download",
                on_click=lambda: ui.download(bytes(data), "campaign_results.jsonl"),
            ).props("color=primary outline")
        else:
            ui.button("Download campaign results.jsonl", icon="download").props("disable outline")
        rep = session.suite_parity_last_report
        if isinstance(rep, dict):
            from ui_nicegui.lib.suite_extended_helpers import parity_zip_bytes

            ui.button(
                "Download parity reviewer pack",
                icon="archive",
                on_click=lambda: ui.download(parity_zip_bytes(rep), "SHAMS_benchmark_parity_pack.zip"),
            ).props("outline")
        pc = session.profile_contracts_v362_last
        if isinstance(pc, dict) and pc:
            ui.badge("Profile corners report ready — export inside Tab 4", color="blue").props("outline")
