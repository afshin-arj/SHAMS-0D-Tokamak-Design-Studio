"""Publication Benchmarks shared helpers — run-lock, pack summary, handoffs."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.session import DesignSession

PUB_RUNLOCK_OWNER = "PublicationBenchmarks"

_EVIDENCE_SOURCE_LABELS = {
    "pd_last_outputs": "Point Designer run",
    "systems_last_solution": "Systems Mode solution",
    "scan_last_artifact": "Scan Lab cartography",
    "pareto_last_front": "Pareto Lab frontier",
    "extopt_last_run": "External optimizer run",
    "surrogate_v386_last_screening_run": "Surrogate screening",
    "pub_atlas_last": "Publication Atlas case",
    "pub_bench_last_outdir": "Publication pack outdir",
    "pub_crosscode_last": "Cross-code semantics compare",
}


def evidence_source_label(key: str) -> str:
    return _EVIDENCE_SOURCE_LABELS.get(key, key)


def try_acquire_pub_lock(session: DesignSession, task: str) -> bool:
    locked, existing, is_owner = runlock_status(PUB_RUNLOCK_OWNER)
    if locked and not is_owner:
        ui.notify(f"Blocked — {existing or 'another task'} is running.", type="warning")
        return False
    if not runlock_acquire(task, PUB_RUNLOCK_OWNER):
        ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
        return False
    session.pub_running = True
    return True


def release_pub_lock(session: DesignSession) -> None:
    runlock_release(PUB_RUNLOCK_OWNER)
    session.pub_running = False
    session.pub_atlas_running = False
    session.pub_atlas_fragility_running = False
    session.pub_bench_running = False


def pack_summary_from_outdir(outdir: Optional[str]) -> Dict[str, Any]:
    """Read summary/topology/CSV for pack verdict KPIs."""
    if not outdir:
        return {"loaded": False}
    root = Path(outdir)
    summary: Dict[str, Any] = {}
    topo: Dict[str, Any] = {}
    sp = root / "summary.json"
    tp = root / "topology.json"
    if sp.is_file():
        try:
            import json

            summary = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            summary = {}
    if tp.is_file():
        try:
            import json

            topo = json.loads(tp.read_text(encoding="utf-8"))
        except Exception:
            topo = {}
    fr = (topo.get("fractions") or {}) if isinstance(topo, dict) else {}
    n_rows = int(summary.get("n_rows") or topo.get("n_rows") or 0)
    n_pass = int(summary.get("n_pass_blocking") or topo.get("n_pass_blocking") or 0)
    n_fail = int(summary.get("n_fail_blocking") or topo.get("n_fail_blocking") or max(n_rows - n_pass, 0))
    posture = "PACK PASS" if n_rows and n_fail == 0 else ("PACK FAIL" if n_fail else "PACK READY")
    if n_rows and 0 < n_fail < n_rows:
        posture = "PACK MIXED"
    return {
        "loaded": True,
        "posture": posture,
        "n_rows": n_rows,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "pass_frac": float(fr.get("pass", (n_pass / n_rows) if n_rows else 0.0)),
        "fail_frac": float(fr.get("fail", (n_fail / n_rows) if n_rows else 0.0)),
        "robust_frac": float(fr.get("robust", 0.0)),
        "fragile_frac": float(fr.get("fragile", 0.0)),
        "shams_version": str(summary.get("shams_version") or ""),
        "outdir": outdir,
        "csv": str(summary.get("csv") or (root / "point_designer_benchmark_table.csv")),
        "topology": topo,
        "summary": summary,
    }


def zip_pack_outdir(outdir: str) -> bytes:
    root = Path(outdir)
    if not root.is_dir():
        raise FileNotFoundError(f"Pack outdir missing: {outdir}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(root)).replace("\\", "/"))
    return buf.getvalue()


def promote_atlas_inputs_to_point_designer(session: DesignSession) -> int:
    """Copy atlas artifact inputs into session.inputs (explicit promote; no auto-eval)."""
    res = session.pub_atlas_last
    if not isinstance(res, dict):
        raise ValueError("No atlas result — evaluate a preset first.")
    run = res.get("run") if isinstance(res.get("run"), dict) else {}
    art = run.get("artifact") if isinstance(run.get("artifact"), dict) else {}
    inputs = art.get("inputs") if isinstance(art.get("inputs"), dict) else {}
    if not inputs:
        raise ValueError("Atlas artifact has no inputs to promote.")
    n = 0
    for k, v in inputs.items():
        if k not in session.inputs:
            continue
        try:
            session.inputs[k] = float(v) if isinstance(v, (int, float)) else v
            n += 1
        except (TypeError, ValueError):
            session.inputs[k] = v
            n += 1
    return n


def handoff_to_system_suite(session: DesignSession) -> None:
    """Open System Suite for numeric PROCESS parity (documentation Cross-Code stays on this deck)."""
    from ui_nicegui.lib.navigation import switch_deck

    switch_deck("System Suite")
    ui.notify("Opened System Suite — use Tab 5 Benchmark parity for numeric PROCESS cases.", type="info")
    log_ui_event(session, PUB_RUNLOCK_OWNER, "HandoffSystemSuite", {})


def render_pub_suite_handoff_shortcut(session: DesignSession) -> None:
    """Always-visible Suite jump — works even when Cross-deck handoffs expansion is closed."""
    ui.button(
        "System Suite (numeric parity)",
        icon="fact_check",
        on_click=lambda: handoff_to_system_suite(session),
    ).props("outline dense color=primary data-testid=pb-handoff-system-suite")


def render_pub_handoffs(session: DesignSession) -> None:
    from ui_nicegui.lib.navigation import switch_deck

    ui.label("Cross-deck handoffs").classes("text-subtitle2")
    ui.label(
        "Promote atlas inputs to Point Designer, open Systems Mode, or jump to System Suite for numeric PROCESS parity."
    ).classes("text-caption text-grey q-mb-sm")

    def _to_pd() -> None:
        try:
            n = promote_atlas_inputs_to_point_designer(session)
            switch_deck("Point Designer")
            ui.notify(f"Promoted {n} atlas inputs → Point Designer (re-evaluate there).", type="positive")
            log_ui_event(session, PUB_RUNLOCK_OWNER, "HandoffPointDesigner", {"n": n})
        except Exception as exc:
            ui.notify(f"Promote failed: {exc}", type="negative")

    def _to_systems() -> None:
        switch_deck("Systems Mode")
        ui.notify("Opened Systems Mode — evaluate or solve, then return for governance packs.", type="info")
        log_ui_event(session, PUB_RUNLOCK_OWNER, "HandoffSystemsMode", {})

    def _to_cr() -> None:
        switch_deck("Control Room")
        ui.notify("Opened Control Room for study seal / evidence.", type="info")

    with ui.row().classes("gap-2 flex-wrap"):
        ui.button("Atlas → Point Designer", icon="upload", on_click=_to_pd).props(
            "outline color=primary data-testid=pb-handoff-point-designer"
        )
        ui.button("Open Systems Mode", icon="hub", on_click=_to_systems).props(
            "flat outline data-testid=pb-handoff-systems"
        )
        ui.button(
            "System Suite (numeric parity)",
            icon="fact_check",
            on_click=lambda: handoff_to_system_suite(session),
        ).props("flat outline data-testid=pb-handoff-system-suite-expansion")
        ui.button("Open Control Room", icon="gavel", on_click=_to_cr).props(
            "flat outline data-testid=pb-handoff-control-room"
        )


def render_pack_verdict_strip(session: DesignSession) -> None:
    summ = pack_summary_from_outdir(session.pub_bench_last_outdir)
    if not summ.get("loaded"):
        verdict_banner("UNKNOWN", detail="Acknowledge → Generate pack → download CSV/ZIP tables.")
        return
    detail = (
        f"{summ['n_pass']}/{summ['n_rows']} blocking-pass · "
        f"fail frac={100.0 * summ['fail_frac']:.0f}%"
    )
    if summ.get("shams_version"):
        detail += f" · SHAMS {summ['shams_version']}"
    verdict_banner(summ["posture"].replace("PACK ", ""), detail=detail)
    kpi_row([
        ("Rows", str(summ["n_rows"])),
        ("Blocking pass", str(summ["n_pass"])),
        ("Blocking fail", str(summ["n_fail"])),
        ("Pass frac", f"{100.0 * summ['pass_frac']:.0f}%"),
    ])
