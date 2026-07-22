"""Systems Mode verdict-first panels — posture strip + constraint ledger."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.json_view import render_json_blob
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints, design_intent_key
from ui_nicegui.lib.systems_artifact import (
    constraint_mechanism,
    constraint_margin,
    constraint_name,
    constraint_status,
    extract_constraints,
    fmt,
    pick_first,
)


def _physics_kpis(art: dict) -> dict:
    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    if not out and isinstance(art.get("ledger"), dict):
        out = art["ledger"].get("outputs") or {}
    return {
        "Q": out.get("Q_DT_eqv", out.get("Q")),
        "P_fus": out.get("Pfus_total_MW", out.get("Pfus_MW", out.get("P_fus_MW", out.get("P_fusion_MW")))),
        "P_net": out.get("P_e_net_MW", out.get("P_net_e_MW", out.get("P_net_MW"))),
        "H98": out.get("H98"),
        "beta_N": out.get("beta_N", out.get("betaN_proxy", out.get("betaN"))),
        "f_G": out.get("fG", out.get("greenwald_fraction")),
        "q95": out.get("q95_proxy", out.get("q95")),
        "mirage": bool(out.get("mirage_flag_v402")),
    }


def render_degraded_posture(*, next_action: str = "") -> None:
    ui.label("Design status").classes("text-subtitle1 q-mt-sm")
    kpi_row([
        ("Verdict", "NO BASELINE"),
        ("Dominant limit", "-"),
        ("Q", "-"),
        ("P_net [MW]", "-"),
    ])
    if next_action:
        ui.markdown(f"**Next:** {next_action}").classes("text-body2 q-mt-xs")


def render_posture_strip(
    art: dict,
    *,
    next_action: str = "",
    design_intent: str = "",
    fuel_mode: str = "DT",
) -> None:
    constraints = extract_constraints(art)
    verdict = pick_first(art, [["verdict"], ["summary", "verdict"], ["ledger", "verdict"]]) or "-"
    dom = pick_first(
        art, [["dominant_constraint"], ["summary", "dominant_constraint"], ["ledger", "dominant_constraint"]]
    )
    mech = pick_first(
        art, [["dominant_mechanism"], ["summary", "dominant_mechanism"], ["ledger", "dominant_mechanism"]]
    )
    dom_margin = None
    auth = "-"
    if dom:
        for c in constraints:
            if constraint_name(c) == str(dom):
                if not mech:
                    mech = constraint_mechanism(c)
                dom_margin = constraint_margin(c)
                auth = str(c.get("authority_tier") or c.get("authority") or "-")
                break

    kpis = _physics_kpis(art)
    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    if not out and isinstance(art.get("ledger"), dict):
        out = art["ledger"].get("outputs") or {}
    if not isinstance(out, dict):
        out = {}

    # PHYS-KPI-001 parity with Point Designer: suppress Q/H98/Pfus/P_net claims on INFEASIBLE.
    from ui_nicegui.lib.pd_hero_kpis import hero_diagnostic_notes, hero_kpi_cells
    from ui_nicegui.lib.verdict_core import verdict_summary

    summary = verdict_summary(out) if out else {
        "loaded": False,
        "feasible": str(verdict).upper() in ("FEASIBLE", "PASS", "PASS+DIAG"),
        "verdict": str(verdict or "UNKNOWN"),
        "q_label": f"Q={fmt(kpis.get('Q'))}",
        "nt_label": "n·T=n/a",
    }
    cells = hero_kpi_cells(
        out if out else {
            "Q_DT_eqv": kpis.get("Q"),
            "H98": kpis.get("H98"),
            "Pfus_total_MW": kpis.get("P_fus"),
            "P_net_e_MW": kpis.get("P_net"),
        },
        summary,
        design_intent=design_intent,
        fuel_mode=fuel_mode,
    )
    by_label = {c.label: c for c in cells}
    q_disp = by_label.get("Performance").display if "Performance" in by_label else fmt(kpis.get("Q"))
    h98_disp = by_label.get("H98(y,2)").display if "H98(y,2)" in by_label else fmt(kpis.get("H98"))
    pfus_disp = by_label.get("Pfus").display if "Pfus" in by_label else fmt(kpis.get("P_fus"))
    p_net_disp = by_label.get("P_net,e").display if "P_net,e" in by_label else fmt(kpis.get("P_net"))

    from ui_nicegui.components.verdict_banner import verdict_banner

    src = str(art.get("source") or "")
    if src == "point_designer_fallback":
        ui.badge("POINT DESIGNER BASELINE", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "This posture is the Point Designer evaluation — run Precheck / Target solve for a Systems Mode result."
        ).classes("text-caption text-orange q-mb-xs")
    elif src == "point_designer_apply":
        ui.badge("POINT DESIGNER APPLY (RE-EVAL)", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "This artifact is an Apply → Point Designer re-evaluation — not a Systems target solve."
        ).classes("text-caption text-orange q-mb-xs")
    elif src == "systems_recovery":
        ui.badge("SYSTEMS RECOVERY", color="blue").props("outline").classes("q-mb-xs")
        ui.label(
            "Recovery / best-effort Systems seed — promote only if feasible; otherwise continue diagnosing."
        ).classes("text-caption text-blue-8 q-mb-xs")

    detail_bits = []
    if src == "point_designer_fallback":
        detail_bits.append("PD baseline (not a Systems solve)")
    elif src == "point_designer_apply":
        detail_bits.append("PD Apply re-eval (not a Systems solve)")
    elif src == "systems_recovery":
        detail_bits.append("Systems recovery seed")
    elif src == "systems_solve":
        detail_bits.append("Systems target solve")
    if dom:
        detail_bits.append(f"Dominant: {fmt(dom, digits=32)}")
    if mech:
        detail_bits.append(f"Mechanism: {fmt(mech, digits=16)}")
    if dom_margin is not None:
        detail_bits.append(f"Margin: {fmt(dom_margin)}")
    if next_action:
        detail_bits.append(f"Next: {next_action}")
    verdict_banner(str(verdict or "UNKNOWN"), detail=" · ".join(detail_bits))
    if kpis.get("mirage"):
        ui.badge("MIRAGE / credibility-fragile", color="orange").props("outline").classes("q-mb-xs")
    kpi_row([
        ("Q", q_disp),
        ("H98", h98_disp),
        ("Pfus [MW]", pfus_disp),
        ("P_net [MW]", p_net_disp),
        ("q95 (cyl. proxy)", fmt(kpis.get("q95"))),
        ("β_N", fmt(kpis.get("beta_N"))),
        ("f_G", fmt(kpis.get("f_G"))),
    ])
    for note in hero_diagnostic_notes(
        out,
        summary,
        design_intent=design_intent,
        fuel_mode=fuel_mode,
    )[:2]:
        ui.markdown(note).classes("text-caption text-orange q-mt-xs")
    ui.label("Diagnostic only — does not modify frozen physics.").classes("text-caption text-grey q-mb-sm")


def render_verdict_bar(art: dict) -> None:
    render_posture_strip(art)


def render_causal_chain(art: dict, *, expert: bool = False, inline: bool = False) -> None:
    constraints = extract_constraints(art)
    verdict = pick_first(art, [["verdict"], ["summary", "verdict"], ["ledger", "verdict"]]) or "-"
    dom = pick_first(
        art, [["dominant_constraint"], ["summary", "dominant_constraint"], ["ledger", "dominant_constraint"]]
    )
    mech = pick_first(
        art, [["dominant_mechanism"], ["summary", "dominant_mechanism"], ["ledger", "dominant_mechanism"]]
    )
    dom_entry = None
    if dom:
        for c in constraints:
            if constraint_name(c) == str(dom):
                dom_entry = c
                break
    if dom_entry and not mech:
        mech = constraint_mechanism(dom_entry)

    drivers: list[str] = []
    if dom_entry:
        di = dom_entry.get("dominant_inputs")
        if isinstance(di, list) and di:
            for x in di[:4]:
                if isinstance(x, dict):
                    name = x.get("name") or x.get("input") or x.get("var") or "x"
                    sens = x.get("dmargin_dx") or x.get("sensitivity")
                    if isinstance(sens, (int, float)):
                        drivers.append(f"{name} (∂m/∂x={sens:+.3g})")
                    else:
                        drivers.append(str(name))
                else:
                    drivers.append(str(x))

    chain: list[str] = [f"**{verdict}**"]
    if mech:
        chain.append(f"↳ Mechanism: **{mech}**")
    if dom:
        chain.append(f"↳ Dominant constraint: **{dom}**")
    if drivers:
        chain.append("↳ Dominant drivers: " + ", ".join(drivers))
    if dom and "RWM" in str(dom).upper():
        chain.append("↳ RWM screening: required bandwidth/power must fit within CONTROL caps.")

    if inline:
        ui.label("Why-chain (dominant cause)").classes("text-subtitle2")
        with ui.card().classes("w-full p-3"):
            for line in chain:
                ui.markdown(line)
            if expert and isinstance(dom_entry, dict):
                ui.label("Raw dominant entry (expert):").classes("text-caption")
                render_json_blob(dom_entry)
    else:
        with ui.expansion("Why-chain (dominant cause)", icon="account_tree").classes("w-full"):
            for line in chain:
                ui.markdown(line)
            if expert and isinstance(dom_entry, dict):
                ui.label("Raw dominant entry (expert):").classes("text-caption")
                render_json_blob(dom_entry)


def render_constraint_cards(art: dict, *, design_intent: str = "", expert: bool = False) -> None:
    if not expert:
        return
    constraints = extract_constraints(art)
    if not constraints:
        return
    failed = [constraint_name(c) for c in constraints if constraint_status(c) == "FAIL"]
    cls = classify_failed_constraints(failed, design_intent=design_intent)
    blocking = set(cls.get("blocking", []))

    ui.label("Constraint cards (expert)").classes("text-subtitle2 q-mt-md")
    for c in constraints[:12]:
        nm = constraint_name(c)
        if blocking and nm not in blocking and design_intent_key(design_intent) == "reactor":
            continue
        with ui.card().classes("p-2 q-mb-xs"):
            ui.markdown(
                f"**{nm}** | {constraint_status(c)} | m={fmt(constraint_margin(c))} | "
                f"{constraint_mechanism(c)}"
            )


def _constraint_rows(constraints: list[dict], names: set[str] | None = None) -> list[dict]:
    rows = []
    for c in constraints:
        nm = constraint_name(c)
        if names is not None and nm not in names:
            continue
        rows.append({
            "name": nm,
            "status": constraint_status(c),
            "margin": fmt(constraint_margin(c)),
            "mechanism": constraint_mechanism(c),
        })
    return rows


def render_constraint_table(art: dict, *, design_intent: str = "") -> None:
    constraints = extract_constraints(art)
    if not constraints:
        return

    failed = [constraint_name(c) for c in constraints if constraint_status(c) == "FAIL"]
    cls = classify_failed_constraints(failed, design_intent=design_intent)
    blocking = set(cls.get("blocking", []))
    diagnostic = set(cls.get("diagnostic", []))

    cols = [
        {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "margin", "label": "Margin", "field": "margin"},
        {"name": "mechanism", "label": "Mechanism", "field": "mechanism"},
    ]

    with ui.tabs().classes("w-full") as tabs:
        t_block = ui.tab("Blocking")
        t_diag = ui.tab("Diagnostic")
        t_all = ui.tab("All")

    with ui.tab_panels(tabs, value=t_block).classes("w-full"):
        with ui.tab_panel(t_block):
            rows = _constraint_rows(constraints, blocking if blocking else None)
            if not rows and design_intent_key(design_intent) == "reactor":
                rows = _constraint_rows(constraints)
            ui.table(columns=cols, rows=rows[:40], row_key="name").classes("w-full")
        with ui.tab_panel(t_diag):
            ui.table(
                columns=cols,
                rows=_constraint_rows(constraints, diagnostic if diagnostic else None)[:40],
                row_key="name",
            ).classes("w-full")
        with ui.tab_panel(t_all):
            ui.table(columns=cols, rows=_constraint_rows(constraints)[:40], row_key="name").classes("w-full")
