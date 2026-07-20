"""Systems Mode — Explore / feasible search (Streamlit parity)."""

from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.lib.systems_fs_helpers import FS_OBJECTIVE_OPTIONS, FS_START_SOURCES, fs_objective_label
from ui_nicegui.lib.systems_precheck import build_targets_and_variables
from ui_nicegui.lib.systems_workflow_helpers import (
    append_run_card,
    merge_multiseed_feasible_search,
    run_feasible_search,
    systems_run_payload,
    tuple_bounds_to_dict,
)
from ui_nicegui.session import DesignSession

_OBJ_KEYS = [k for k, _ in FS_OBJECTIVE_OPTIONS]


def _fs_start_values(session: DesignSession, search_vars: list[str], bounds: dict) -> dict:
    src = str(session.systems_fs_src or FS_START_SOURCES[0])
    start: dict = {}
    if src == "Last target solve":
        sol = session.systems_last_solve_result
        if isinstance(sol, dict) and sol.get("inp") is not None:
            inp = sol["inp"]
            for k in search_vars:
                if hasattr(inp, k):
                    try:
                        start[k] = float(getattr(inp, k))
                    except (TypeError, ValueError):
                        pass
    elif src == "Last seeded recovery":
        rec = session.systems_recovery_last
        if isinstance(rec, dict) and isinstance(rec.get("best_point"), dict):
            for k in search_vars:
                if k in rec["best_point"]:
                    start[k] = float(rec["best_point"][k])
    if not start:
        for k in search_vars:
            b = bounds.get(k, {})
            lo, hi = float(b.get("lo", 0)), float(b.get("hi", 1))
            start[k] = 0.5 * (lo + hi)
    return start


def render_explore_panel(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Feasible design search (top-K)").classes("text-subtitle1")
    ui.label(
        "Hard constraints must pass under active Design Intent; then optimize an engineering objective "
        "among feasible machines. Multi-seed merges Top-K across runs."
    ).classes("text-caption q-mb-sm")

    base = session.build_point_inputs()
    _, variables = build_targets_and_variables(session, base)
    if not variables:
        ui.label("Configure iteration variables in Setup first.").classes("text-orange")
        return

    default_bounds = tuple_bounds_to_dict(variables)
    var_opts = list(default_bounds.keys())
    if not session.systems_fs_vars:
        session.systems_fs_vars = list(var_opts)

    ui.select(
        FS_START_SOURCES,
        label="Starting point source",
        value=session.systems_fs_src if session.systems_fs_src in FS_START_SOURCES else FS_START_SOURCES[0],
        on_change=lambda e: setattr(session, "systems_fs_src", str(e.value)),
    ).classes("w-full q-mb-sm")

    ui.select(
        {k: lbl for k, lbl in FS_OBJECTIVE_OPTIONS},
        label="Objective",
        value=session.systems_fs_objective if session.systems_fs_objective in _OBJ_KEYS else _OBJ_KEYS[0],
        on_change=lambda e: setattr(session, "systems_fs_objective", str(e.value)),
    ).classes("w-full q-mb-sm")

    ui.select(
        var_opts,
        label="Variables to search",
        value=[v for v in session.systems_fs_vars if v in var_opts] or var_opts,
        multiple=True,
        on_change=lambda e: setattr(session, "systems_fs_vars", list(e.value or [])),
    ).classes("w-full q-mb-sm")

    with ui.row().classes("gap-4 flex-wrap"):
        ui.number(
            "Budget",
            value=session.systems_fs_budget,
            min=50,
            max=5000,
            step=50,
            on_change=lambda e: setattr(session, "systems_fs_budget", int(e.value or 150)),
        ).classes("w-24")
        ui.number(
            "Top-K",
            value=session.systems_fs_topk,
            min=1,
            max=50,
            on_change=lambda e: setattr(session, "systems_fs_topk", int(e.value or 8)),
        ).classes("w-20")
        ui.number(
            "Radius",
            value=session.systems_fs_radius,
            min=0.01,
            max=1.0,
            step=0.05,
            on_change=lambda e: setattr(session, "systems_fs_radius", float(e.value or 0.25)),
        ).classes("w-24")
        ui.number(
            "Seed",
            value=session.systems_fs_seed,
            min=0,
            max=999999,
            on_change=lambda e: setattr(session, "systems_fs_seed", int(e.value or 2026)),
        ).classes("w-24")
        ui.number(
            "Multi-seed runs",
            value=max(1, int(session.systems_fs_multiseed_n or 1)),
            min=1,
            max=20,
            on_change=lambda e: setattr(session, "systems_fs_multiseed_n", int(e.value or 1)),
        ).classes("w-28")

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        if session.systems_fs_running:
            ui.notify("Search already running", type="warning")
            return
        locked, task, is_owner = runlock_status("SystemsMode")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Systems Mode: Feasible search", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        session.systems_fs_running = True
        ui.notify("Running feasible search…", type="info")
        try:
            reactor = "reactor" in str(session.design_intent).lower()
            search_vars = [v for v in (session.systems_fs_vars or var_opts) if v in default_bounds]
            bounds = {k: default_bounds[k] for k in search_vars}
            start_vals = _fs_start_values(session, search_vars, bounds)
            nms = max(1, int(session.systems_fs_multiseed_n or 1))
            base_seed = int(session.systems_fs_seed)

            def _one_run(seed_off: int):
                return run_feasible_search(
                    session.build_point_inputs(),
                    variables,
                    rng_seed=base_seed + seed_off,
                    budget=session.systems_fs_budget,
                    topk=session.systems_fs_topk,
                    radius=session.systems_fs_radius,
                    reactor_intent=reactor,
                    objective_key=session.systems_fs_objective,
                    search_vars=search_vars,
                    bounds_override=session.systems_fs_bounds or bounds,
                    start_vals=start_vals,
                    design_intent=session.design_intent,
                    input_overrides=dict(session.systems_inputs_overrides or {}),
                    trace_keep=session.systems_fs_trace_keep,
                )

            runs = []
            for j in range(nms):
                runs.append(await run.io_bound(_one_run, j))
            rep = merge_multiseed_feasible_search(
                runs,
                topk=session.systems_fs_topk,
                reactor_intent=reactor,
            ) if nms > 1 else runs[0]

            session.systems_feasible_search_last = rep
            append_run_card(
                session,
                kind="FeasibleSearch",
                settings={
                    "budget": session.systems_fs_budget,
                    "topk": session.systems_fs_topk,
                    "objective": session.systems_fs_objective,
                    "multi_seed": nms,
                },
                outcome={"ok": bool(rep.get("ok")), "reason": str(rep.get("reason", ""))},
                payload=systems_run_payload(session),
            )
            ui.notify(
                f"Search complete — {len(rep.get('candidates') or [])} candidates",
                type="positive" if rep.get("ok") else "warning",
            )
            _results.refresh()
            _trace_plot.refresh()
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Search failed: {exc}", type="negative")
        finally:
            session.systems_fs_running = False
            runlock_release("SystemsMode")

    ui.button("Run feasible search", icon="travel_explore", on_click=_run).props("outline q-mb-sm")
    _results(session)
    _trace_plot(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    rep = session.systems_feasible_search_last
    if not isinstance(rep, dict):
        return
    ui.label(
        f"Search: {rep.get('reason', '-')} | objective={rep.get('objective', '-')} | "
        f"candidates={len(rep.get('candidates') or [])} | trace={len(rep.get('trace') or [])}"
    ).classes("text-body2")
    rows = []
    for i, c in enumerate(rep.get("candidates") or []):
        if not isinstance(c, dict):
            continue
        h = c.get("headline") or {}
        rows.append(
            {
                "rank": i + 1,
                "feasible": c.get("feasible"),
                "obj": c.get("obj"),
                "Q": h.get("Q"),
                "H98": h.get("H98"),
                "P_net": h.get("P_net"),
                "Pfus": h.get("Pfus"),
                "V": c.get("V"),
            }
        )
    if rows:
        ui.table(
            columns=[
                {"name": "rank", "label": "#", "field": "rank"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
                {"name": "obj", "label": "Objective", "field": "obj"},
                {"name": "Q", "label": "Q", "field": "Q"},
                {"name": "H98", "label": "H98", "field": "H98"},
                {"name": "P_net", "label": "P_net", "field": "P_net"},
                {"name": "Pfus", "label": "Pfus", "field": "Pfus"},
                {"name": "V", "label": "V", "field": "V"},
            ],
            rows=rows,
            row_key="rank",
        ).classes("w-full")


@ui.refreshable
def _trace_plot(session: DesignSession) -> None:
    rep = session.systems_feasible_search_last
    if not isinstance(rep, dict):
        return
    trace = rep.get("trace") or []
    if not trace:
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    feas_x, feas_y, infeas_x, infeas_y = [], [], [], []
    for t in trace:
        m = t.get("metrics") or {}
        q = m.get("Q_DT_eqv", m.get("Q"))
        h = m.get("H98")
        try:
            qv, hv = float(q), float(h)
        except (TypeError, ValueError):
            continue
        if not (qv == qv and hv == hv):
            continue
        if t.get("feasible"):
            feas_x.append(qv)
            feas_y.append(hv)
        else:
            infeas_x.append(qv)
            infeas_y.append(hv)

    fig = go.Figure()
    if infeas_x:
        fig.add_trace(
            go.Scatter(
                x=infeas_x,
                y=infeas_y,
                mode="markers",
                name="Infeasible",
                marker=dict(color="rgba(160,160,160,0.35)", size=5),
            )
        )
    if feas_x:
        fig.add_trace(
            go.Scatter(
                x=feas_x,
                y=feas_y,
                mode="markers",
                name="Feasible",
                marker=dict(color="#2e7d32", size=6),
            )
        )
    fig.update_layout(
        height=360,
        margin=dict(l=48, r=20, t=36, b=48),
        xaxis_title="Q_DT_eqv",
        yaxis_title="H98",
        title="Search trace (Q vs H98)",
        legend=dict(orientation="h"),
    )
    ui.plotly(fig).classes("w-full q-mt-sm")
