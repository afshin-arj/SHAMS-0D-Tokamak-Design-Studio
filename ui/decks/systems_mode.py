"""Systems Mode deck -- extracted from ui/app.py (UI redesign batch 3).

Feasibility-first system explanation around the frozen Point Designer truth.
Deterministic, audit-safe, no hidden solvers. Read-only explanation layer: it
may propose explicit, user-controlled *what would need to change* narratives but
never modifies physics truth, constraints, or evaluator behavior.

Pure move (commit 3A): no logic change. Both original `if _deck == "Systems Mode":`
blocks (main UI + freeze-readiness helpers/stateful results) are merged into this
single function, preserving execution order. The block runs with app.py module
globals injected (namespace bridge) so every bare name resolves exactly as it did
inline; this bridge is temporary tech debt to be replaced with explicit
imports/ctx in a later cleanup commit. No physics, constraint, solver,
evaluator, session-state key, or routing-ID changes.
"""
from __future__ import annotations
import streamlit as st
import sys


def render_systems_mode(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name (st, pd, math, json, REPO_ROOT, render_mode_scope,
    # Dict, List, Any, Tuple, helpers, ...) exactly as it did when it lived inline
    # in app.py. Pure move. To be replaced with explicit dependencies in a later commit.
    _g = globals()
    for _k, _v in vars(_app_module).items():
        if not _k.startswith("__"):
            _g[_k] = _v

    from ui.components import empty_state

    # DSG: auto edge-kind tagging by active panel (exploration only)
    if bool(st.session_state.get("dsg_edge_kind_auto", True)):
        st.session_state["dsg_context_edge_kind"] = "systems_eval"

    # Ensure core solver knobs exist in session state even before the user opens any controls.
    # This prevents unbound-name failures on first entry/reruns when downstream blocks execute.
    st.session_state.setdefault("systems_max_iter", 35)

    st.header("Systems Mode")
    st.caption("Feasibility-first system explanation around the frozen Point Designer truth. Deterministic, audit-safe, no hidden solvers.")
    render_mode_scope("systems")

    # --- Systems Mode solver parameter discipline (UI stabilization Phase 1) ---
    # Never define solver knobs conditionally inside tabs/expanders; always read from session_state safely.
    tol: float = float(st.session_state.get("systems_tol", 1e-3))
    damping: float = float(st.session_state.get("systems_damping", 0.6))
    max_iter: int = int(st.session_state.get("systems_max_iter", 35))
    # Optional trust-region cap (scaled space); None means disabled.
    trust_delta = st.session_state.get("systems_trust_delta", None)
    if trust_delta is not None:
        try:
            trust_delta = float(trust_delta)
        except Exception:
            trust_delta = None


    with st.expander("About this mode", expanded=False):
        st.info(
            "This is an **explanation layer** around the frozen evaluator: it may propose explicit, user-controlled *what would need to change* narratives, "
            "but it **never modifies** physics truth, constraints, or evaluator behavior.",
        )
        st.caption("Apply actions (when used) are reversible (undo/redo).")

    st.session_state.setdefault("systems_run_cards", [])

    # Compact Cockpit moved to post-run diagnostics (v374.1)

    def _sys_get_in(d: Any, path: List[str]) -> Any:
        cur: Any = d
        for k in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    def _sys_pick_first(d: Any, paths: List[List[str]]) -> Any:
        for p in paths:
            v = _sys_get_in(d, p)
            if v is not None:
                return v
        return None

    def _sys_fmt(v: Any, *, digits: int = 3) -> str:
        try:
            if v is None:
                return "-"
            if isinstance(v, bool):
                return "true"if v else "false"
            if isinstance(v, (int, float)):
                if not math.isfinite(float(v)):
                    return "-"
                return f"{float(v):.{digits}g}"
            s = str(v)
            return s if s.strip() else "-"
        except Exception:
            return "-"

    def _sys_compact_next_action(verdict: str, dom: str, step: str) -> str:
        v = str(verdict or '').upper()
        stp = str(step or '')
        if v.startswith('PASS'):
            if 'Explore' in stp:
                return "Explore feasible neighborhood (Scan/Feasible Search)"
            return "Apply → Compare → Export dossier"
        # FAIL
        if 'Recover' in stp:
            return "Run Seeded Recovery (increase budget if needed)"
        if 'Diagnose' in stp:
            return f"Inspect dominant limiter: {dom or 'unknown'}"
        return "Run Diagnose → then Recover"

    def _sys_render_compact_cockpit() -> None:
        """Render an above-the-fold summary bar for expert operators.

        Rules:
        - No auto-expanding panels.
        - Never throws.
        - Uses cached artifacts when available.
        """
        try:
            s = _v92_state_get()
            art = st.session_state.get('systems_last_solve_artifact')
            if not isinstance(art, dict):
                art = getattr(s, 'last_systems_result', None)
            if not isinstance(art, dict):
                art = getattr(s, 'last_point_artifact', None)
            if not isinstance(art, dict):
                return

            # Resolve top-level summary keys (schema-tolerant).
            verdict = _sys_pick_first(art, [
                ['verdict'], ['summary','verdict'], ['point','verdict'], ['result','verdict']
            ])
            dom = _sys_pick_first(art, [
                ['dominant_constraint'], ['summary','dominant_constraint'], ['ledger','dominant_hard'], ['decision','dominant_hard']
            ])
            mech = _sys_pick_first(art, [
                ['dominant_mechanism'], ['summary','dominant_mechanism'], ['ledger','dominant_mechanism']
            ])
            step = st.session_state.get('_pending_workflow_step') or _sys_pick_first(art, [['ui_state','workflow_step'], ['workflow_step']]) or 'Diagnose'

            # Key physics/plant KPIs (optional; shown if available).
            Pfus = _sys_pick_first(art, [['P_fus_MW'], ['physics','P_fus_MW'], ['point','P_fus_MW'], ['plasma','P_fus_MW']])
            Pnet = _sys_pick_first(art, [['P_net_MW'], ['plant','P_net_MW'], ['point','P_net_MW'], ['summary','P_net_MW']])
            Qpl = _sys_pick_first(art, [['Q_plasma'], ['physics','Q_plasma'], ['point','Q_plasma'], ['summary','Q_plasma'], ['Q']])
            betaN = _sys_pick_first(art, [['beta_N'], ['physics','beta_N'], ['plasma','beta_N'], ['summary','beta_N']])
            q95 = _sys_pick_first(art, [['q95'], ['physics','q95'], ['plasma','q95'], ['summary','q95']])
            nGW = _sys_pick_first(art, [['n_over_nGW'], ['physics','n_over_nGW'], ['plasma','n_over_nGW'], ['summary','n_over_nGW']])

            # v256.0: design confidence class (trust ledger)
            try:
                ac = (art.get("authority_confidence") or {}) if isinstance(art, dict) else {}
                dc = str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
            except Exception:
                dc = "UNKNOWN"

            # v257.0: decision consequences (advisory; post-processing only)
            try:
                _dec = (art.get("decision_consequences") or {}) if isinstance(art, dict) else {}
                decision_posture = str(_dec.get("decision_posture", "UNKNOWN"))
                primary_risk = str(_dec.get("primary_risk_driver", "") or "")
            except Exception:
                decision_posture = "UNKNOWN"
                primary_risk = ""

            # v258.0: epoch feasibility (Startup / Nominal / End-of-Life)
            try:
                _ef = (art.get("epoch_feasibility") or {}) if isinstance(art, dict) else {}
                epoch_overall = str(_ef.get("overall", "UNKNOWN"))
            except Exception:
                epoch_overall = "UNKNOWN"


            # Build a copyable markdown summary (deterministic, audit-friendly).
            md_lines = [
                "# Systems Compact Cockpit",
                "",
                f"- Verdict: {str(verdict)}",
                f"- Design confidence: {str(dc)}",
                f"- Decision posture: {str(decision_posture)}",
                f"- Epoch feasibility (overall): {str(epoch_overall)}",
                f"- Primary risk driver: {primary_risk if primary_risk else '-'}",
                f"- Workflow step: {str(step)}",
                f"- Dominant constraint: {str(dom)}",
                f"- Dominant mechanism: {str(mech)}",
                "",
                "## Key KPIs",
                f"- P_fus [MW]: {Pfus if Pfus is not None else '-'}",
                f"- P_net [MW]: {Pnet if Pnet is not None else '-'}",
                f"- Q_plasma [-]: {Qpl if Qpl is not None else '-'}",
                f"- beta_N [-]: {betaN if betaN is not None else '-'}",
                f"- q95 [-]: {q95 if q95 is not None else '-'}",
                f"- n/nGW [-]: {nGW if nGW is not None else '-'}",
                "",
                "## Next action (diagnostic only)",
                f"- {_sys_compact_next_action(str(verdict), str(dom), str(step))}",
            ]
            cockpit_md = "\n".join(md_lines)

            # Optional: show copy-ready markdown and a one-click download.
            if bool(st.session_state.get("systems_cockpit_show_md", False)):
                with st.expander("Copy-ready cockpit summary (markdown)", expanded=False):
                    st.code(cockpit_md, language="markdown")
                    st.download_button(
                        "Download cockpit summary (MD)",
                        data=cockpit_md.encode("utf-8"),
                        file_name="systems_compact_cockpit.md",
                        mime="text/markdown",
                        use_container_width=True,
                        key="systems_cockpit_md_download",
                    )

            # Optional: pin a mini-cockpit in the sidebar (Streamlit-safe 'sticky').
            if bool(st.session_state.get("systems_cockpit_pin", False)):
                with st.sidebar:
                    st.markdown("### Systems Cockpit (pinned)")
                    st.caption("Diagnostic only - external to truth.")
                    st.write(f"**Verdict:** {str(verdict)}")
                    st.write(f"**Confidence:** {str(dc)}")
                    st.write(f"**Posture:** {str(decision_posture)}")
                    if primary_risk:
                        st.write(f"**Risk driver:** {str(primary_risk)}")
                    st.write(f"**Step:** {str(step)}")
                    if dom:
                        st.write(f"**Dominant:** {str(dom)}")
                    if mech:
                        st.write(f"**Mechanism:** {str(mech)}")
                    st.write(f"**P_net:** {(_sys_fmt(Pnet) + ' MW') if Pnet is not None else '-'}")
                    st.write(f"**Q:** {_sys_fmt(Qpl) if Qpl is not None else '-'}")

            # Compact header
            c0, c1, c2, c3, c4, c5 = st.columns([1.1, 1.0, 1.0, 1.0, 1.0, 1.2])
            with c0:
                st.markdown("#### Compact Cockpit")
                st.caption("Above-the-fold operator summary")
            with c5:
                st.caption("Next action")
                st.write(_sys_compact_next_action(str(verdict), str(dom), str(step)))

            # Metrics row
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1:
                st.metric("Verdict", _sys_fmt(verdict, digits=12))
            with m2:
                st.metric("Workflow", _sys_fmt(step, digits=12))
            with m3:
                st.metric("Dominant", _sys_fmt(dom, digits=12))
            with m4:
                st.metric("Mechanism", _sys_fmt(mech, digits=12))
            with m5:
                st.metric("P_fus", f"{_sys_fmt(Pfus)} MW"if Pfus is not None else "-")
            with m6:
                st.metric("P_net", f"{_sys_fmt(Pnet)} MW"if Pnet is not None else "-")

            _pr = f"• risk: **{primary_risk}**"if primary_risk else ""
            st.caption(
                f"Trust layer (post-processing): confidence = **{dc}**, posture = **{decision_posture}**{_pr}. Truth unchanged."
            )

            # Secondary metrics row (only if at least one is present)
            if any(v is not None for v in [Qpl, betaN, q95, nGW]):
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    st.metric("Q_plasma", _sys_fmt(Qpl))
                with s2:
                    st.metric("β_N", _sys_fmt(betaN))
                with s3:
                    st.metric("q95", _sys_fmt(q95))
                with s4:
                    st.metric("n/nGW", _sys_fmt(nGW))

            st.divider()
        except Exception:
            return

    # Render the compact cockpit as early as possible.
    # _sys_render_compact_cockpit()  # moved to post-run diagnostics (v374.1)
    # -----------------------------
    # Systems Console (v231 bundle): Verdict Bar + Mechanism Filter + Constraint Cards + Causal Chain + Expert Toggle
    #
    # This is UI-only: it never changes physics, constraints, or truth. It renders from cached artifacts.
    def _sys_fetch_latest_systems_artifact() -> dict | None:
        try:
            s = _v92_state_get()
        except Exception:
            s = None
        cand = None
        try:
            if isinstance(st.session_state.get("systems_last_solve_artifact"), dict):
                cand = st.session_state.get("systems_last_solve_artifact")
        except Exception:
            cand = None
        if cand is None and s is not None:
            try:
                if isinstance(getattr(s, "last_systems_result", None), dict):
                    cand = getattr(s, "last_systems_result")
            except Exception:
                pass
        if cand is None and s is not None:
            try:
                if isinstance(getattr(s, "last_point_artifact", None), dict):
                    cand = getattr(s, "last_point_artifact")
            except Exception:
                pass
        return cand if isinstance(cand, dict) else None

    def _sys_extract_constraints(art: dict) -> list[dict]:
        # Try multiple schema paths (graceful across versions)
        paths = [
            ["ledger", "constraints"],
            ["constraint_ledger", "constraints"],
            ["constraints"],
            ["ledger_entries"],
        ]
        for p in paths:
            v = _sys_get_in(art, p)
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                return v
        return []

    def _sys_constraint_kind(c: dict) -> str:
        # Prefer explicit kind/status flags, fall back to common fields
        for k in ["kind", "tier", "severity", "class"]:
            v = c.get(k)
            if isinstance(v, str) and v:
                vv = v.lower()
                if "block"in vv or vv == "hard":
                    return "blocking"
                if "diag"in vv or "soft"in vv:
                    return "diagnostic"
                if "ignore"in vv or "off"in vv:
                    return "ignored"
        status = str(c.get("status") or c.get("verdict") or "").lower()
        if status in ("fail", "pass", "pass+diag"):
            # kind not inferable from status
            return str(c.get("kind") or "blocking"if status == "fail"else "diagnostic")
        return "diagnostic"

    def _sys_constraint_name(c: dict) -> str:
        return str(c.get("name") or c.get("constraint") or c.get("id") or c.get("key") or "constraint")

    def _sys_constraint_margin(c: dict) -> float | None:
        for k in ["signed_margin", "margin", "m", "delta"]:
            v = c.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        # some ledgers store margin under 'metrics'
        mv = c.get("metrics") if isinstance(c.get("metrics"), dict) else None
        if isinstance(mv, dict):
            for k in ["signed_margin", "margin"]:
                v = mv.get(k)
                if isinstance(v, (int, float)):
                    return float(v)
        return None

    def _sys_constraint_status(c: dict) -> str:
        v = c.get("status") or c.get("verdict") or c.get("result")
        if isinstance(v, str) and v:
            return v.upper()
        # infer from margin if possible
        m = _sys_constraint_margin(c)
        if isinstance(m, (int, float)):
            return "FAIL"if m < 0 else "PASS"
        return "-"

    def _sys_constraint_mechanism(c: dict) -> str:
        for k in ["mechanism_group", "mechanism", "group"]:
            v = c.get(k)
            if isinstance(v, str) and v:
                return v.upper()
        return "OTHER"

    def _sys_constraint_authority(c: dict) -> str:
        for k in ["authority_tier", "authority", "tier_authority"]:
            v = c.get(k)
            if isinstance(v, str) and v:
                return v
        return "-"

    def _sys_constraint_validity(c: dict) -> str:
        for k in ["validity_domain", "validity", "domain"]:
            v = c.get(k)
            if isinstance(v, str) and v:
                return v
        return "-"

    def _sys_constraint_inputs(c: dict) -> list[str]:
        for k in ["inputs", "dominant_inputs", "drivers"]:
            v = c.get(k)
            if isinstance(v, list) and v:
                return [str(x if not isinstance(x, dict) else x.get("name") or x.get("input") or x.get("var") or x) for x in v][:6]
        return []

    def _sys_render_verdict_bar(art: dict, *, constraints: list[dict]) -> None:
        verdict = _sys_pick_first(art, [[ "verdict"], [ "summary", "verdict"], [ "ledger", "verdict"]]) or "-"
        dom = _sys_pick_first(art, [[ "dominant_constraint"], [ "summary", "dominant_constraint"], [ "ledger", "dominant_constraint"]])
        mech = _sys_pick_first(art, [[ "dominant_mechanism"], [ "summary", "dominant_mechanism"], [ "ledger", "dominant_mechanism"]])
        # If mechanism missing, infer from dominant constraint entry
        if (not mech) and dom:
            for c in constraints:
                if _sys_constraint_name(c) == str(dom):
                    mech = _sys_constraint_mechanism(c)
                    break
        # Signed margin for dominant (if present)
        dom_margin = None
        if dom:
            for c in constraints:
                if _sys_constraint_name(c) == str(dom):
                    dom_margin = _sys_constraint_margin(c)
                    break

        cols = st.columns([1.1, 1.2, 2.2, 1.2, 1.1, 1.2])
        with cols[0]:
            st.markdown("#### Systems Verdict Bar")
        with cols[1]:
            st.metric("Verdict", _sys_fmt(verdict, digits=16))
        with cols[2]:
            st.metric("Dominant constraint", _sys_fmt(dom, digits=48) if dom else "-")
        with cols[3]:
            st.metric("Mechanism", _sys_fmt(mech, digits=16) if mech else "-")
        with cols[4]:
            st.metric("Signed margin", _sys_fmt(dom_margin) if dom_margin is not None else "-")
        with cols[5]:
            # show authority for dominant if known
            auth = "-"
            if dom:
                for c in constraints:
                    if _sys_constraint_name(c) == str(dom):
                        auth = _sys_constraint_authority(c)
                        break
            st.metric("Authority", _sys_fmt(auth, digits=16))
            # v256.0: design confidence class (trust ledger)
            try:
                ac = (art.get("authority_confidence") or {}) if isinstance(art, dict) else {}
                dc = str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
            except Exception:
                dc = "UNKNOWN"
            st.metric("Confidence", dc)

        # Policy contract summary (explicit enforcement tiering)
        try:
            pol = out.get("_policy_contract") or {}
            q95_pol = str(pol.get("q95_enforcement", "hard")).strip().lower()
            fg_pol = str(pol.get("greenwald_enforcement", "hard")).strip().lower()
            if (q95_pol != "hard") or (fg_pol != "hard"):
                st.caption(f"Policy contract: q95={q95_pol.upper()} · Greenwald(fG)={fg_pol.upper()} (tiering only; physics unchanged)")
        except Exception:
            pass
        st.caption("Verdict Bar is diagnostic only; it does not modify physics, constraints, or truth.")
        st.divider()

    def _sys_render_causal_chain(art: dict, *, constraints: list[dict], expert: bool) -> None:
        verdict = _sys_pick_first(art, [[ "verdict"], [ "summary", "verdict"], [ "ledger", "verdict"]]) or "-"
        dom = _sys_pick_first(art, [[ "dominant_constraint"], [ "summary", "dominant_constraint"], [ "ledger", "dominant_constraint"]])
        mech = _sys_pick_first(art, [[ "dominant_mechanism"], [ "summary", "dominant_mechanism"], [ "ledger", "dominant_mechanism"]])
        dom_entry = None
        if dom:
            for c in constraints:
                if _sys_constraint_name(c) == str(dom):
                    dom_entry = c
                    break
        if dom_entry and (not mech):
            mech = _sys_constraint_mechanism(dom_entry)

        drivers = []
        if dom_entry:
            di = dom_entry.get("dominant_inputs")
            if isinstance(di, list) and di:
                for x in di[:4]:
                    if isinstance(x, dict):
                        name = x.get("name") or x.get("input") or x.get("var") or "x"
                        sens = x.get("dmargin_dx") or x.get("sensitivity") or None
                        if isinstance(sens, (int, float)):
                            drivers.append(f"{name} (∂m/∂x={sens:+.3g})")
                        else:
                            drivers.append(str(name))
                    else:
                        drivers.append(str(x))
        chain = []
        chain.append(f"**{str(verdict)}**")
        if mech:
            chain.append(f"↳ Mechanism: **{str(mech)}**")
        if dom:
            chain.append(f"↳ Dominant constraint: **{str(dom)}**")
        if drivers:
            chain.append("↳ Dominant drivers: "+ ", ".join(drivers))
        # Add a minimal RWM hint when relevant (no additional physics, purely explanatory)
        if dom and "RWM"in str(dom).upper():
            chain.append("↳ RWM screening: required bandwidth/power must fit within CONTROL caps (see Control Contracts).")
        with st.expander("Why-chain (dominant cause)", expanded=False):
            for line in chain:
                st.markdown(line)
            if expert and isinstance(dom_entry, dict):
                st.markdown("**Raw dominant entry (expert):**")
                st.json(dom_entry)

    def _sys_render_constraint_cards(art: dict, *, constraints: list[dict]) -> None:
        # Expert density toggle
        ex = st.toggle("Expert view", value=st.session_state.get("systems_expert_view", False), key="systems_expert_view")
        # Mechanism filter
        mechs = sorted({ _sys_constraint_mechanism(c) for c in constraints } | {"ALL"})
        mech_sel = st.selectbox("View by mechanism", options=mechs, index=0, key="systems_mech_filter")
        # Kind tabs
        t_block, t_diag, t_all = st.tabs(["Blocking", "Diagnostic", "All"])
        # common renderer
        def render_kind(kind: str | None):
            rows = []
            for c in constraints:
                k = _sys_constraint_kind(c)
                if kind and k != kind:
                    continue
                if mech_sel != "ALL"and _sys_constraint_mechanism(c) != mech_sel:
                    continue
                rows.append(c)
            # sort: worst margin first (None last), then FAIL first
            def keyfn(c):
                m = _sys_constraint_margin(c)
                stt = _sys_constraint_status(c)
                return (0 if stt == "FAIL"else 1, 1e9 if m is None else m)
            rows.sort(key=keyfn)
            max_cards = st.slider("Max cards", min_value=5, max_value=60, value=min(20, max(5, len(rows))), step=5, key=f"systems_max_cards_{kind or 'all'}")
            for c in rows[:max_cards]:
                name = _sys_constraint_name(c)
                status = _sys_constraint_status(c)
                margin = _sys_constraint_margin(c)
                mech = _sys_constraint_mechanism(c)
                auth = _sys_constraint_authority(c)
                sub = str(c.get("subsystem") or "-")
                val = _sys_constraint_validity(c)
                inp = _sys_constraint_inputs(c)

                header = f"{name}"
                badge = f"{status}"
                if margin is not None:
                    badge += f"| m={margin:+.4g}"
                badge += f"| {mech}"

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2.3, 1.0, 1.0, 1.2])
                    with c1:
                        st.markdown(f"**{header}**")
                        st.caption(sub)
                    with c2:
                        st.metric("Status", badge)
                    with c3:
                        st.metric("Authority", auth)
                    with c4:
                        st.metric("Mechanism", mech)
                    # compressed details
                    if inp:
                        st.caption("Inputs: "+ ", ".join(inp))
                    if ex:
                        d1, d2 = st.columns([1,1])
                        with d1:
                            st.caption("Validity")
                            st.write(val)
                        with d2:
                            st.caption("Raw (expert)")
                            st.json(c)
        with t_block:
            render_kind("blocking")
        with t_diag:
            render_kind("diagnostic")
        with t_all:
            render_kind(None)
    # Systems Console rendering moved to post-run diagnostics (v374.1)


    # v185: additional Systems Mode freeze-grade state
    st.session_state.setdefault('systems_restore_rid', None)

    def _systems_restore_ui_from_artifact(obj2: dict, *, rerun: bool = True, source: str = "artifact") -> None:
        """Restore full Systems UI state from a Systems artifact (schema-stable).
        This must be rerun-safe and must never throw.
        """
        import streamlit as st
        try:
            st.session_state["systems_last_solve_artifact"] = obj2
            try:
                _v92_state_get().last_systems_result = obj2
            except Exception:
                pass

            ui = obj2.get("ui_state") if isinstance(obj2.get("ui_state"), dict) else obj2

            for k in ["systems_run_cards","systems_journal","v178_last_precheck","v178_last_recovery","v178_fs_last","systems_last_feasible_search"]:
                if isinstance(ui, dict) and (k in ui):
                    st.session_state[k] = ui.get(k)

            st.session_state["_pending_workflow_step"] = str((ui.get("workflow_step") if isinstance(ui, dict) else "") or "Diagnose")
            if isinstance(ui, dict) and ui.get("design_intent"):
                st.session_state["design_intent"] = ui.get("design_intent")

            # Keep a breadcrumb
            st.session_state["systems_last_restore_source"] = source
            if rerun:
                st.rerun()
        except Exception:
            pass

    # If a run-id reproduction is pending, resolve it now (before rendering panels).
    try:
        _rid = st.session_state.get('systems_restore_rid')
        if _rid:
            st.session_state['systems_restore_rid'] = None
            try:
                s = _v98_state_init_runlists()
                rec = next((x for x in (getattr(s,'run_history',[]) or []) if x.get('id') == _rid), None)
                if rec and isinstance(rec.get('payload'), dict):
                    _systems_restore_ui_from_artifact(rec.get('payload'), rerun=True, source=f"run:{_rid}")
            except Exception:
                pass
    except Exception:
        pass


    def _sys_now_iso() -> str:
        try:
            import datetime as _dt
            return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        except Exception:
            return ''

    def _sys_failure_taxonomy(reason: str) -> Dict[str, Any]:
        r = str(reason or '').strip()
        mapping = {
            'precheck_infeasible': {
                'title': 'Infeasible within declared bounds (precheck)',
                'next': ['Expand bounds for key variables', 'Switch intent to Research to diagnose without blocking', 'Run Seeded Recovery near your seed'],
            },
            'no_feasible_found': {
                'title': 'No feasible point found (budget exhausted)',
                'next': ['Increase budget/multi-start', 'Allow more variables to change', 'Widen bounds around the seed'],
            },
            'no_variables': {
                'title': 'No variables provided',
                'next': ['Select at least one variable with valid bounds'],
            },
            'nonfinite_range': {
                'title': 'Non-finite model outputs in sampled region',
                'next': ['Narrow bounds to avoid numerically invalid region', 'Check inputs for physical plausibility'],
            },
        }
        return dict(mapping.get(r, {'title': r or 'unknown', 'next': []}))

    def _sys_levers_from_limiters(limiters: List[str]) -> List[str]:
        # Rule-of-thumb levers (diagnostic; does not change physics)
        lever_map = {
            'q_div': ['Increase R0', 'Increase a (if allowed)', 'Increase radiation fraction / detach proxy (Research)', 'Lower power density (reduce Paux or targets)'],
            'sigma_vm': ['Lower Bt', 'Increase coil build/size (increase R0)', 'Relax stress allowables only if policy permits'],
            'HTS margin': ['Increase shield thickness', 'Reduce peak field (lower Bt or increase R0)', 'Adjust coil pack assumptions (if exposed)'],
            'TBR': ['Increase shield/blanket thickness', 'Increase R0 (more blanket volume)', 'Reduce inboard build consumption'],
            'q95': ['Increase Bt or reduce Ip (if Ip is variable)', 'Increase size (R0/a)'],
            'B_peak': ['Lower Bt', 'Increase R0 / coil radius'],
            'NWL': ['Increase R0', 'Reduce fusion power density (targets/temperature)'],
        }
        out: List[str] = []
        for lm in (limiters or []):
            for s in lever_map.get(str(lm), []):
                if s not in out:
                    out.append(s)
        return out[:8]

    def _sys_validate_bounds(bounds: Dict[str, Dict[str, float]]) -> Tuple[bool, List[str], List[str]]:
        errs: List[str] = []
        warns: List[str] = []
        # basic physical sanity envelopes (warnings only)
        phys = {
            'R0_m': (0.5, 30.0),
            'a_m': (0.1, 10.0),
            'kappa': (1.0, 3.2),
            'delta': (0.0, 0.8),
            'Bt_T': (0.5, 25.0),
            'Ti_keV': (0.5, 50.0),
            'Ti_over_Te': (0.5, 5.0),
            't_shield_m': (0.0, 3.0),
            'Paux_MW': (0.0, 2000.0),
        }
        for k, b in (bounds or {}).items():
            try:
                lo = float(b.get('lo'))
                hi = float(b.get('hi'))
            except Exception:
                errs.append(f"{k}: bounds not numeric")
                continue
            if not (math.isfinite(lo) and math.isfinite(hi)):
                errs.append(f"{k}: non-finite bounds")
                continue
            if hi <= lo:
                errs.append(f"{k}: hi must be > lo")
            if k in phys:
                plo, phi = phys[k]
                if lo < plo or hi > phi:
                    warns.append(f"{k}: bounds [{lo:g}, {hi:g}] exceed typical envelope [{plo:g}, {phi:g}] (warning only)")
        return (len(errs) == 0), errs, warns

    def _sys_append_run_card(*, kind: str, settings: Dict[str, Any], outcome: Dict[str, Any]) -> None:
        try:
            card = {
                'schema_version': SYS_RUN_CARD_SCHEMA_VERSION,
                'ts': _sys_now_iso(),
                'kind': str(kind),
                'status': 'fail' if str((outcome or {}).get('event','')).lower() == 'fail' else 'ok',
                'reason_code': str((outcome or {}).get('reason', (outcome or {}).get('reason_code',''))),
                'settings': dict(settings or {}),
                'outcome': dict(outcome or {}),
            }
            st.session_state['systems_run_cards'] = (st.session_state.get('systems_run_cards') or []) + [card]
            st.session_state['systems_run_cards'] = st.session_state['systems_run_cards'][-50:]
        except Exception:
            pass

    try:
        _v93_stateful_systems_panel()
    except Exception:
        pass

    st.subheader("Constraint Solver Cockpit")
    st.markdown(
        "Solve for a self-consistent operating point by adjusting **iteration variables** "
        "to hit **targets** (e.g., Q, H98, net electric) while reporting engineering and physics margins. "
        "This is inspired by external systems codes's constraint-driven workflow, but remains SHAMS-native and transparent."
    )

    # v182.1: Persist and re-render the latest Systems *solve* results across reruns.
    # Streamlit download_button triggers a rerun; if results are only rendered inside the
    # `if run:` block, they will appear to "disappear"after downloads.
    try:
        _cached = st.session_state.get('systems_last_solve_artifact')
        if not isinstance(_cached, dict):
            _cached = getattr(_v92_state_get(), 'last_systems_result', None)
        if isinstance(_cached, dict):
            with st.expander('Last solve snapshot (cached)', expanded=False):
                _v182_render_latest_systems_solve_results(artifact=_cached, point_artifact=getattr(_v92_state_get(), 'last_point_artifact', None), key_prefix="latest_cached")
            # v184.9: Persist and re-render the latest Feasible Search results across reruns.
            # Users often run the search inside Explore, then move workflow steps; this cached view
            # keeps the results discoverable and downloadable.
            try:
                _fs_cached = st.session_state.get('systems_last_feasible_search')
                if not isinstance(_fs_cached, dict):
                    _fs_cached = getattr(_v92_state_get(), 'last_feasible_search_artifact', None)
                if isinstance(_fs_cached, dict):
                    _t = _fs_cached.get('ts_unix')
                    try:
                        _tstr = datetime.datetime.fromtimestamp(float(_t)).strftime('%Y-%m-%d %H:%M:%S') if _t else 'unknown time'
                    except Exception:
                        _tstr = 'unknown time'
                    st.caption(f"Latest feasible-search cache: **{_fs_cached.get('reason','')}** at **{_tstr}** (see expander below)")
                    # Above-the-fold discoverability: don't auto-expand panels, but make new results obvious.
                    if bool(st.session_state.get('systems_fs_new', False)):
                        _b1, _b2 = st.columns([5,1])
                        with _b1:
                            st.info("New feasible-search candidates are ready. Click **Show now** to open them below.")
                        with _b2:
                            if st.button('Show now', key='systems_fs_show_now_btn'):
                                st.session_state['systems_show_fs_cached'] = True
                                st.session_state['systems_fs_new'] = False
                                st.rerun()
                    _exp_fs = bool(st.session_state.get('systems_show_fs_cached', False))
                    with st.expander('Latest cached Feasible Design Search results', expanded=_exp_fs):
                        _v184_render_latest_feasible_search_results(report=_fs_cached, key_prefix="fs_latest_cached")
            except Exception:
                pass
    except Exception:
        pass

    # -----------------------------
    # Decision State + Teaching Mode (SHOULD/COULD)
    # -----------------------------
    st.session_state.setdefault('systems_decision_state', 'Diagnose infeasibility')
    st.session_state.setdefault('systems_teaching_mode', False)
    _ds_opts = [
        'Diagnose infeasibility',
        'Recover feasibility near seed',
        'Choose a compromise (best-compromise)',
        'Explore trade space (scan/frontier)',
        'Apply & iterate (update Base/x0)',
    ]
    _c_ds1, _c_ds2 = st.columns([3,2])
    with _c_ds1:
        st.selectbox('Design decision state', options=_ds_opts, index=_ds_opts.index(st.session_state.get('systems_decision_state', _ds_opts[0])) if st.session_state.get('systems_decision_state') in _ds_opts else 0,
                     key='systems_decision_state',
                     help='This does not change physics. It clarifies what you are trying to do right now and tunes guidance text.')
    with _c_ds2:
        st.checkbox('Teaching / narrated mode', value=bool(st.session_state.get('systems_teaching_mode', False)),
                    key='systems_teaching_mode',
                    help='Shows extra guidance and step-by-step hints (diagnostic only).')
    try:
        if st.session_state.get('systems_teaching_mode', False):
            st.info(
                f"**Narrated mode:** You are in **{st.session_state.get('systems_decision_state')}**. "
                "Recommended flow: Precheck → Recovery (if needed) → Search/Compare → Apply to Base/x0 → Recheck."
            )
    except Exception:
        pass

    # -----------------------------

    # -----------------------------
    
    # -----------------------------
    # Negotiation Chronicle (v218) - transcript + dominance switching (read-only)
    # -----------------------------
    try:
        run_cards = st.session_state.get('systems_run_cards', []) or []
        journal = st.session_state.get('systems_journal', []) or []
        # Build a compact, reviewer-safe transcript
        transcript = []
        for k, rc in enumerate(run_cards):
            if not isinstance(rc, dict):
                continue
            art = rc.get("artifact") or rc.get("payload") or {}
            cons = None
            try:
                cons = (art.get("constraints") or []) if isinstance(art, dict) else None
            except Exception:
                cons = None
            # Dominant (first failing) hard constraint name if available
            dom = None
            try:
                if isinstance(art, dict) and isinstance(art.get("constraint_ledger"), dict):
                    tb = (art["constraint_ledger"].get("top_blockers") or [])
                    if isinstance(tb, list) and tb and isinstance(tb[0], dict):
                        dom = tb[0].get("name")
            except Exception:
                dom = None
            if dom is None and isinstance(cons, list):
                try:
                    # fallback: smallest margin_frac among failed hard constraints
                    failed = [c for c in cons if isinstance(c, dict) and (not bool(c.get("passed", True))) and str(c.get("severity","hard")).lower()=="hard"]
                    failed.sort(key=lambda c: float(c.get("margin_frac", 0.0)))
                    dom = failed[0].get("name") if failed else None
                except Exception:
                    dom = None

            transcript.append({
                "k": int(k),
                "ts": rc.get("ts") or rc.get("timestamp") or None,
                "label": rc.get("label") or rc.get("name") or f"run_{k}",
                "action": rc.get("action") or rc.get("reason") or "",
                "design_intent": (art.get("design_intent") if isinstance(art, dict) else None),
                "dominant_constraint": dom,
                "ok_hard": bool((art.get("kpis") or {}).get("feasible_hard")) if isinstance(art.get("kpis"), dict) else None,
            })

        # Dominance switching analysis
        dom_seq = [t.get("dominant_constraint") for t in transcript if t.get("dominant_constraint")]
        switches = []
        last = None
        for i, d in enumerate(dom_seq):
            if last is None:
                last = d
                continue
            if str(d) != str(last):
                switches.append({"at": int(i), "from": str(last), "to": str(d)})
                last = d

        with st.expander("Negotiation Chronicle - audit transcript (read-only)", expanded=False):
            st.caption("A compact, reviewer-safe log of Systems Mode actions and what constraint dominated each step. This does not change any physics or state.")
            if transcript:
                try:
                    import pandas as _pd
                    st.dataframe(_pd.DataFrame(transcript), use_container_width=True, hide_index=True, height=260)
                except Exception:
                    st.json(transcript[:40], expanded=False)
                st.download_button(
                    "Download Systems transcript (JSON)",
                    data=_shams_json_dumps({"schema":"systems_transcript.v1","transcript":transcript,"switches":switches}, indent=2).encode("utf-8"),
                    file_name="shams_systems_transcript_v1.json",
                    mime="application/json",
                    use_container_width=True,
                    key="systems_transcript_dl",
                )
            else:
                st.info("No Systems run cards yet. Run a workflow step (Precheck/Recovery/Search) to generate transcript entries.")

        with st.expander("Dominance Switchboard - regime boundary hints", expanded=False):
            st.caption("Where the dominant blocker changes, you crossed a regime boundary in the local feasibility landscape.")
            if switches:
                try:
                    import pandas as _pd
                    st.dataframe(_pd.DataFrame(switches), use_container_width=True, hide_index=True, height=220)
                except Exception:
                    st.json(switches, expanded=False)
            else:
                st.info("No dominance switches detected in the current Systems run history (or not enough runs).")
    except Exception:
        pass

# Workflow navigator (v180)
    # -----------------------------
    # Workflow navigator (v180) - session-safe (no widget/state conflict)
    # -----------------------------
    # Derive local defaults from session state without setting widget value.
    _default_step = str(st.session_state.get('systems_workflow_step', 'Diagnose'))
    # Back-compat: older builds stored emoji in the raw workflow value.
    if _default_step == "Export":
        _default_step = "Export"
    _default_power = bool(st.session_state.get('systems_workflow_power_user', False))

    # Apply pending workflow changes BEFORE widget instantiation, without directly setting widget state.
    try:
        if '_pending_workflow_step' in st.session_state:
            _default_step = str(st.session_state.pop('_pending_workflow_step'))
        if '_pending_workflow_power_user' in st.session_state:
            _default_power = bool(st.session_state.pop('_pending_workflow_power_user'))
    except Exception:
        pass



    c_wf1, c_wf2 = st.columns([3, 1])
    with c_wf1:
        _wf_keys = ["Setup", "Diagnose", "Recover", "Explore", "Compare/Apply", "Export", "Advanced"]
        _wf_labels = {
            "Setup": "Setup",
            "Diagnose": "Diagnose",
            "Recover": "Recover",
            "Explore": "Explore",
            "Compare/Apply": "Compare/Apply",
            "Export": "Export",
            "Advanced": "Advanced",
        }

        # Normalize legacy stored state if present.
        try:
            _legacy = st.session_state.get("systems_workflow_step")
            if _legacy == "Export":
                st.session_state["systems_workflow_step"] = "Export"
        except Exception:
            pass

        st.radio(
            "Workflow",
            options=_wf_keys,
            index=_wf_keys.index(_default_step) if _default_step in _wf_keys else 1,
            horizontal=True,
            format_func=lambda k: _wf_labels.get(str(k), str(k)),
            key="systems_workflow_step",
            help="Guided workflow view. Enable Power-user to show all panels at once.",
        )
    with c_wf2:
        st.toggle(
            "Power-user",
            value=_default_power,
            key="systems_workflow_power_user",
            help="Show all Systems panels (advanced/debug).",
        )

    def _sys_show(*steps: str) -> bool:
        """Whether to render a Systems panel in the current workflow view.

        SHAMS UI law: avoid long scroll. Systems Mode is workflow-guided.
        - Power-user: show everything (debug/forensics).
        - Guided view: show only panels relevant to the selected step.

        This must never make Systems Mode "empty"; core headers and the workflow selector
        remain outside step-gated panels.
        """
        try:
            if bool(st.session_state.get("systems_workflow_power_user", False)):
                return True
            step = str(st.session_state.get("systems_workflow_step", "Diagnose") or "Diagnose")
            if not steps:
                return True
            return step in set(map(str, steps))
        except Exception:
            return True

    # ---- Verdict-first banner (UI redesign batch 3): promote the verdict bar and
    # compact cockpit above the solve controls so the latest cached verdict is
    # visible on entry. Read-only: renders from the latest cached Systems artifact;
    # it triggers no solve and modifies no physics/constraints/state.
    try:
        _sys_vf_art = st.session_state.get("systems_last_solve_artifact") or _sys_fetch_latest_systems_artifact()
        if isinstance(_sys_vf_art, dict):
            _sys_vf_cons = _sys_extract_constraints(_sys_vf_art)
            _sys_render_verdict_bar(_sys_vf_art, constraints=_sys_vf_cons)
            _sys_render_compact_cockpit()
        else:
            empty_state("No cached Systems artifact yet. Run Precheck / Solve below to populate the verdict.", kind="info")
    except Exception:
        st.caption("Verdict banner unavailable (non-fatal).")

    # --- Systems Mode freeze-readiness helpers (v180+) ---
    SYS_RUN_CARD_SCHEMA_VERSION = 1
    SYS_TRACE_SCHEMA_VERSION = 1
    SYS_ARTIFACT_SCHEMA_VERSION = 1

    _WIDGET_KEYS_PREFIXES = ("v178_", "v179_", "v180_", "systems_")
    def _is_widget_owned_key(k: str) -> bool:
        # Heuristic: any key that is used as a widget key should never be mutated after instantiation.
        # We track a registry of widget keys touched by st.* widgets in this run.
        try:
            reg = set(st.session_state.get("_widget_key_registry", set()) or set())
            return str(k) in reg
        except Exception:
            return False

    def _register_widget_key(k: str) -> None:
        try:
            reg = set(st.session_state.get("_widget_key_registry", set()) or set())
            reg.add(str(k))
            st.session_state["_widget_key_registry"] = reg
        except Exception:
            pass

    def safe_state_set(key: str, value, *, allow_widget_keys: bool = False) -> None:
        # Prevent accidental Streamlit widget-key mutation errors.
        if (not allow_widget_keys) and _is_widget_owned_key(key):
            raise RuntimeError(f"Attempted to modify widget-owned session_state key: {key}")
        st.session_state[key] = value

    def _sys_run_card(kind: str, status: str, reason_code: str, message: str, **fields) -> dict:
        rc = {
            "schema_version": SYS_RUN_CARD_SCHEMA_VERSION,
            "kind": str(kind),
            "status": str(status),
            "reason_code": str(reason_code),
            "message": str(message),
            "ts_unix": float(time.time()),
        }
        for k, v in fields.items():
            rc[k] = v
        return rc

    def _sys_state() -> dict:
        st.session_state.setdefault("systems_state", {})
        s = st.session_state["systems_state"]
        if not isinstance(s, dict):
            s = {}
            st.session_state["systems_state"] = s
        s.setdefault("schema_version", SYS_ARTIFACT_SCHEMA_VERSION)
        s.setdefault("history", [])
        s.setdefault("history_index", -1)
        s.setdefault("stories", {})
        return s

    def _sys_push_history(label: str, payload: dict) -> None:
        s = _sys_state()
        h = list(s.get("history", []) or [])
        idx = int(s.get("history_index", -1))
        # drop redo tail
        if idx < len(h) - 1:
            h = h[: idx + 1]
        h.append({"label": str(label), "payload": payload, "ts_unix": float(time.time())})
        s["history"] = h
        s["history_index"] = len(h) - 1
        st.session_state["systems_state"] = s

    def _sys_validate_invariants(require_precheck: bool = False, require_candidates: bool = False) -> tuple[bool, str]:
        # Minimal invariants: base point exists; evaluator contract is fixed; assumption lock matches if enabled.
        try:
            if st.session_state.get("base_last_eval") is None and st.session_state.get("v178_base_last_eval") is None:
                return False, "Missing Base evaluation. Run Point Designer once or evaluate Base in Systems Mode."
        except Exception:
            pass
        if require_precheck:
            if not isinstance(st.session_state.get("v178_last_precheck"), dict):
                return False, "No Precheck results found. Run Precheck first."
        if require_candidates:
            rep = st.session_state.get("v178_fs_last") or st.session_state.get("v178_last_recovery")
            cands = []
            if isinstance(rep, dict):
                cands = list(rep.get("candidates", []) or [])
            if not cands:
                return False, "No candidates available yet. Run Recovery or Feasible Search first."
        # Assumption lock (if enabled)
        try:
            if bool(st.session_state.get("systems_assumption_lock_enabled", False)):
                lock_hash = st.session_state.get("systems_assumption_lock_hash")
                cur_hash = st.session_state.get("systems_assumption_current_hash")
                if lock_hash and cur_hash and str(lock_hash) != str(cur_hash):
                    return False, "Assumptions drifted while lock is enabled. Unlock to edit or restore locked assumptions."
        except Exception:
            pass
        return True, ""

    def _sys_primary_action_header(step: str, title: str, subtitle: str, action_label: str, action_key: str) -> bool:
        st.markdown(f"### {title}")
        st.caption(subtitle)
        return st.button(action_label, use_container_width=True, key=action_key)

    # Assumption lock (SHOULD): lock key Systems settings across runs
    # -----------------------------
    st.session_state.setdefault('systems_assumption_lock', {'locked': False, 'snapshot': {}})
    if _sys_show('Setup','Advanced'):
        with st.expander('Assumption lock (Systems settings)', expanded=False):
            _lock = bool(st.session_state.get('systems_assumption_lock', {}).get('locked', False))
            _lock = st.checkbox('Lock key Systems settings across runs', value=_lock, key='systems_assumption_lock_locked',
                                help='Locks intent/objective/diagnostic relaxations to prevent accidental drift between runs.')
            snap = dict((st.session_state.get('systems_assumption_lock', {}) or {}).get('snapshot', {}) or {})
            if st.button('Capture lock snapshot = current', use_container_width=True, key='systems_assumption_lock_capture'):
                snap = {
                    'design_intent': st.session_state.get('design_intent'),
                    'fs_objective': st.session_state.get('v178_fs_obj'),
                    'diag_relax': st.session_state.get('systems_diag_relax', {}),
                }
                st.session_state['systems_assumption_lock'] = {'locked': _lock, 'snapshot': snap}
                st.success('Captured snapshot.')
            if st.button('Clear snapshot', use_container_width=True, key='systems_assumption_lock_clear'):
                st.session_state['systems_assumption_lock'] = {'locked': _lock, 'snapshot': {}}
                st.success('Cleared.')
            # persist lock flag
            st.session_state['systems_assumption_lock'] = {'locked': _lock, 'snapshot': snap}
            if snap:
                st.caption('Locked snapshot')
                st.json(snap)
    
    # v176.0: Systems Mode contract + latest summary
    s = _v92_state_get()
    last_point_art = getattr(s, 'last_point_artifact', None)
    last_sys_art = getattr(s, 'last_systems_result', None)

    def _artifact_sha(obj):
        try:
            return _v152_artifact_sha(obj)
        except Exception:
            try:
                import json, hashlib
                return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode('utf-8')).hexdigest()
            except Exception:
                return None

    if _sys_show('Setup','Advanced'):
        with st.expander('Systems Mode contract (inputs -> solve -> artifact)', expanded=False):
            st.markdown(
                "**Contract**: Systems Mode produces a traceable run artifact from (base inputs, targets, variable bounds, solver options). "
                "If a solve fails, SHAMS reports why (precheck infeasible, continuation step failure, nonconvergence) and shows actionable guidance."
            )
            cols = st.columns(3)
            with cols[0]:
                st.caption('Latest Point artifact')
                if isinstance(last_point_art, dict):
                    st.code(((_artifact_sha(last_point_art) or '(sha unavailable)')[:12]), language='text')
                else:
                    st.write('-')
            with cols[1]:
                st.caption('Latest Systems artifact')
                if isinstance(last_sys_art, dict):
                    st.code(((_artifact_sha(last_sys_art) or '(sha unavailable)')[:12]), language='text')
                else:
                    st.write('-')
            with cols[2]:
                st.caption('State')
                st.write(f"Point={'yes' if isinstance(last_point_art, dict) else 'no'} | Systems={'yes' if isinstance(last_sys_art, dict) else 'no'}")
    
            # Bundle export (point + systems)
            import io, zipfile, json as _json
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                if isinstance(last_point_art, dict):
                    z.writestr('run_artifact_point.json', _shams_json_dumps(last_point_art, indent=2, sort_keys=True))
                if isinstance(last_sys_art, dict):
                    z.writestr('run_artifact_systems.json', _shams_json_dumps(last_sys_art, indent=2, sort_keys=True))
            buf.seek(0)
            st.download_button(
                'Download latest Point+Systems bundle (zip)',
                data=buf.getvalue(),
                file_name='shams_latest_point_systems_bundle.zip',
                mime='application/zip',
                use_container_width=True,
                key='v176_dl_latest_bundle',
            )
    
    # -----------------------------
    
    # -----------------------------
    # Primary Action (workflow-first)
    # -----------------------------
    try:
        _step = str(_default_step)
        _power = _default_power
        if not _power:
            if _step == "Setup":
                st.info("**Setup**: Choose targets and variables, then run **Precheck** in *Diagnose*.")
            elif _step == "Diagnose":
                if _sys_primary_action_header("Diagnose", "Diagnose feasibility", "Run Precheck to see dominant limiters and whether targets/bounds can reach feasibility.", "Run Precheck", "sys_primary_precheck"):
                    safe_state_set("_sys_action", "precheck", allow_widget_keys=True)
                    st.rerun()
            elif _step == "Recover":
                ok, msg = _sys_validate_invariants(require_precheck=True)
                if not ok:
                    st.warning(msg)
                if _sys_primary_action_header("Recover", "Recover feasibility", "Try seeded recovery to find the nearest feasible (or best compromise for Research intent).", "Run Recovery", "sys_primary_recovery"):
                    safe_state_set("_sys_action", "recovery", allow_widget_keys=True)
                    st.rerun()
            elif _step == "Explore":
                ok, msg = _sys_validate_invariants(require_precheck=True)
                if not ok:
                    st.warning(msg)
                if _sys_primary_action_header("Explore", "Explore feasible designs", "Run feasible-only search to generate top-K candidates and a frontier/trace.", "Run Feasible Search", "sys_primary_search"):
                    safe_state_set("_sys_action", "search", allow_widget_keys=True)
                    st.rerun()
            elif _step == "Compare/Apply":
                ok, msg = _sys_validate_invariants(require_candidates=True)
                if not ok:
                    st.warning(msg)
                else:
                    st.info("Compare candidates and apply the selected one to **Base** or **x0**, then re-run Precheck.")
            elif _step == "Export":
                st.info("Export the full Systems bundle (run cards, traces, logs, and point artifacts if present).")
            elif _step == "Advanced":
                st.info("Advanced view shows all tools. Use with care.")
    except Exception:
        pass


# -------------------------------------------------------------------------
# World-class Systems Mode decision support (v183)
# -------------------------------------------------------------------------
    # Persistent decision journal (Design Stories 2.0)
    st.session_state.setdefault("systems_journal", [])
    def _sys_journal_append(kind: str, payload: dict | None = None):
        try:
            entry = {
                "ts_unix": float(time.time()),
                "kind": str(kind),
                "workflow_step": str(st.session_state.get("systems_workflow_step", "")),
                "design_intent": str(st.session_state.get("design_intent", "")),
                "payload": payload or {},
            }
            st.session_state["systems_journal"].append(entry)
        except Exception:
            pass

    # Limiter graph: curated causal map (0-D explainability)
    _LIMITER_GRAPH = {
        "q95": ["Ip_MA (-)", "Bt_T (+)", "R0_m (+)", "kappa (+)", "li (proxy)"],
        "q_div": ["P_SOL_MW (+)", "lambda_q_mm (-)", "R0_m (+) via wetted area", "kappa (+)"],
        "sigma_vm": ["B_peak_T (+)", "R0_m (-) (structure leverage)", "tf_wp geometry"],
        "B_peak": ["Bt_T (+)", "R0_m (-)", "coil build"],
        "HTS margin": ["B_peak_T (+)", "T_op (fixed)", "Jop (proxy)", "wp_fill_factor"],
        "TBR": ["R0_m (+)", "blanket fraction (+)", "A (proxy)", "shield thickness (-)"],
        "P_SOL/R": ["P_SOL_MW (+)", "R0_m (-)"],
        "NWL": ["P_fus (+)", "wall area (-)", "R0_m (+)"],
    }

    # Determine the latest available Systems artifact (rerun-safe)
    try:
        _sys_latest_art = st.session_state.get("systems_last_solve_artifact") or getattr(s, "last_systems_result", None)
    except Exception:
        _sys_latest_art = None



    # Always render the latest cached Systems solve results (rerun-safe).
    # Streamlit download/export triggers a rerun; results must persist from session_state cache.
    if isinstance(_sys_latest_art, dict):
        st.markdown("### Latest Systems results (cached)")
        try:
            _outs = (_sys_latest_art.get("headline") or _sys_latest_art.get("outputs") or {})
            _kc = st.columns(4)
            def _m(_col, _k):
                try:
                    v = float(_outs.get(_k, float("nan")))
                except Exception:
                    v = float("nan")
                with _col:
                    st.metric(_k, f"{v:.3g}"if v == v else "NaN")
            _m(_kc[0], "Q_DT_eqv")
            _m(_kc[1], "H98")
            _m(_kc[2], "P_e_net_MW")
            _m(_kc[3], "q_div_MW_m2")
        except Exception:
            pass
        with st.expander("Downloads, export bundle, and full details", expanded=False):
            _v182_render_latest_systems_solve_results(
                artifact=_sys_latest_art,
                point_artifact=getattr(_v92_state_get(), 'last_point_artifact', None),
                key_prefix="downloads",
            )

    # Candidate sources (recovery/search)
    def _sys_get_candidates():
        cands = []
        try:
            rec = st.session_state.get("v178_last_recovery")
            if isinstance(rec, dict) and isinstance(rec.get("candidates"), list):
                cands += list(rec["candidates"])
        except Exception:
            pass
        try:
            fs = st.session_state.get("v178_fs_last")
            if isinstance(fs, dict) and isinstance(fs.get("candidates"), list):
                cands += list(fs["candidates"])
        except Exception:
            pass
        # de-dup by hash if present
        seen=set()
        out=[]
        for c in cands:
            try:
                hid = c.get("inputs_hash") or c.get("hash") or json.dumps(c.get("x",{}), sort_keys=True, default=str)
            except Exception:
                hid = str(id(c))
            if hid in seen:
                continue
            seen.add(hid)
            out.append(c)
        return out

    # Ranking profiles (transparent + deterministic)
    _RANKING_PROFILES = {
        "Balanced": {"feasible_only": False, "w_margin": 1.0, "w_perf": 1.0, "w_compact": 0.3},
        "Margin-first": {"feasible_only": True, "w_margin": 2.0, "w_perf": 0.5, "w_compact": 0.2},
        "Performance-first": {"feasible_only": False, "w_margin": 0.6, "w_perf": 2.0, "w_compact": 0.1},
        "Compactness-first": {"feasible_only": False, "w_margin": 0.8, "w_perf": 0.8, "w_compact": 2.0},
    }
    st.session_state.setdefault("systems_ranking_profile", "Balanced")

    def _cand_margin_score(c: dict) -> float:
        # Prefer explicit margin dict; otherwise use best_margins
        try:
            m = c.get("margins") or c.get("best_margins") or {}
            if isinstance(m, dict) and m:
                return float(min(m.values()))
        except Exception:
            pass
        return float("nan")

    def _cand_perf_score(c: dict) -> float:
        # Use any headline metric if present
        for k in ("Q_DT_eqv", "H98", "P_e_net_MW", "Pfus_MW"):
            try:
                v = (c.get("headline") or {}).get(k)
                if v is not None:
                    return float(v)
            except Exception:
                pass
            try:
                v = c.get(k)
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return float("nan")

    def _cand_compact_score(c: dict) -> float:
        # smaller R0 is "more compact"; return negative R0 so higher is better
        for k in ("R0_m", "R0"):
            try:
                v = (c.get("x") or {}).get(k)
                if v is not None:
                    return -float(v)
            except Exception:
                pass
        return 0.0

    def _rank_candidates(cands: list[dict], profile_name: str) -> list[dict]:
        prof = _RANKING_PROFILES.get(profile_name, _RANKING_PROFILES["Balanced"])
        def key(c):
            ms = _cand_margin_score(c)
            ps = _cand_perf_score(c)
            cs = _cand_compact_score(c)
            # NaNs sort last deterministically
            ms2 = ms if (ms == ms) else -1e9
            ps2 = ps if (ps == ps) else -1e9
            score = prof["w_margin"]*ms2 + prof["w_perf"]*ps2 + prof["w_compact"]*cs
            # deterministic tie-breaker: inputs_hash string
            t = str(c.get("inputs_hash") or c.get("hash") or "")
            return (score, ms2, ps2, t)
        return sorted(cands, key=key, reverse=True)

    # Families: simple archetype grouping for cognitive load reduction
    def _candidate_family(c: dict) -> str:
        """Cluster candidates into families using constraint-signature first (beyond heuristics).

        Signature clustering is robust across different objective profiles and aligns with
        how systems engineers think: "these designs fail the same way".
        """
        # 1) Constraint-signature clustering (preferred)
        try:
            sig_parts = []
            for k in ["failed_blocking", "failed_hard", "failed_diagnostic", "failed_ignored", "failed"]:
                v = c.get(k)
                if isinstance(v, list) and v:
                    sig_parts.extend([str(x) for x in v if x is not None])
            sig_parts = sorted(set(sig_parts))
            if sig_parts:
                # Keep family names readable: first few constraints + count
                head = ", ".join(sig_parts[:3])
                more = (len(sig_parts) - 3)
                return f"Signature: {head}"+ (f"(+{more})"if more > 0 else "")
        except Exception:
            pass

        # 2) Dominant limiter grouping (fallback)
        try:
            lim = str(c.get("dominant_limiter") or c.get("limiter") or "")
            if lim:
                return f"Limiter: {lim}"
        except Exception:
            pass

        # 3) Compactness heuristic (last fallback)
        try:
            r0 = (c.get("x") or {}).get("R0_m", None)
            if r0 is not None:
                return "Compact"if float(r0) < 3.0 else "Large"
        except Exception:
            pass
        return "Other"

    # Validity / confidence panel: aggregate typical-range flags if present
    def _validity_summary(art: dict) -> dict:
        out = {"validity_score": None, "flags": []}
        try:
            flags = art.get("typical_range_flags") or art.get("flags") or []
            if isinstance(flags, dict):
                flags = [f"{k}:{v}"for k, v in flags.items() if v]
            if isinstance(flags, list):
                out["flags"] = list(flags)
                # Simple score: fewer flags => higher score
                out["validity_score"] = max(0.0, 1.0 - 0.1*len(out["flags"]))
        except Exception:
            pass
        return out

    with st.expander("World-class Systems Mode (Decision support & audit)", expanded=False):
        st.caption("Explainable feasibility, transparent ranking, families/frontier, decision journal, artifact viewer, and model validity - all 0-D friendly and audit-ready.")

        # Ranking profile selector
        st.selectbox("Ranking profile", options=list(_RANKING_PROFILES.keys()), key="systems_ranking_profile")

        # v185: Freeze-grade provenance badge (always visible in this audit panel)
        try:
            import hashlib as _hashlib, json as _json
            _art = _sys_latest_art if isinstance(_sys_latest_art, dict) else {}
            _ih = str(_art.get("inputs_hash") or "")
            _schema = str(_art.get("schema_version") or "1")
            _intent = str(st.session_state.get("design_intent") or "")
            _rankp = str(st.session_state.get("systems_ranking_profile") or "")
            _seed = str(st.session_state.get("v178_fs_seed", ""))

            _mini = {"inputs_hash": _ih, "schema_version": _schema, "intent": _intent, "ranking": _rankp, "seed": _seed}
            _mini_hash = _hashlib.sha256(_json.dumps(_mini, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
            st.caption(f"**Provenance** - schema={_schema} • inputs_hash={_ih[:12]} • intent={_intent} • ranking={_rankp} • seed={_seed} • badge={_mini_hash}")
        except Exception:
            pass

        # v185: Micro-onboarding (workflow guidance)
        with st.expander("What to do next (30-second workflow)", expanded=False):
            st.markdown("- **Diagnose**: Run *Precheck* to see dominant limiters and unreachable targets.\n- **Recover**: Run *Seeded Recovery* near your seed, then Apply to Base/x0.\n- **Explore**: Run *Feasible Design Search* to generate Top‑K candidates and families/frontier.\n- **Compare/Apply**: Pick a candidate, apply, and re-run precheck for confirmation.\n- **Export**: Download artifact + Decision Report PDF for audit-grade sharing.")

        # v185: Reproduce + Diff + Regression guardrails (no hidden state)
        with st.expander("Reproduce / Diff / Regression (freeze-grade)", expanded=False):
            try:
                s = _v98_state_init_runlists()
                runs = [r for r in (getattr(s,'run_history',[]) or []) if str(r.get("kind","")) == "systems"]
                runs = list(reversed(runs))  # newest first
                if not runs:
                    st.info("No recorded Systems runs yet. Run Precheck/Recovery/Search/Solve first.")
                else:
                    labels = [f"{r.get('id')} - {r.get('ts')} - {r.get('mode','')}"for r in runs]
                    _ids = [r.get('id') for r in runs]
                    rid = st.selectbox("Pick a recorded Systems run", options=_ids, format_func=lambda x: labels[_ids.index(x)], key="systems_repro_pick")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("Reproduce this run (restore full UI state)", use_container_width=True, key="systems_repro_btn"):
                            st.session_state["systems_restore_rid"] = rid
                            st.success("Restoring run…")
                            st.rerun()
                    with c2:
                        st.download_button("Download run artifact JSON", data=_shams_json_dumps(next((r for r in runs if r.get('id')==rid), {}).get('payload', {}), indent=2, sort_keys=True).encode("utf-8"),
                                           file_name=f"{rid}.json", mime="application/json", use_container_width=True, key="systems_repro_dl_json")

                    # Diff two runs
                    st.markdown("**Diff two runs (structural JSON diff)**")
                    rid_a = st.selectbox("Run A", options=_ids, key="systems_diff_a")
                    rid_b = st.selectbox("Run B", options=_ids, index=min(1, len(_ids)-1), key="systems_diff_b")
                    A = next((r.get("payload") for r in runs if r.get("id")==rid_a), {})
                    B = next((r.get("payload") for r in runs if r.get("id")==rid_b), {})
                    diffs = _v98_json_diff(A, B)
                    st.write(f"Changed fields: {len(diffs)}")
                    for d in diffs[:200]:
                        st.write("- "+ d)

                    # Regression guard: emit a minimal test case JSON
                    st.markdown("**Create regression test from Run A**")
                    reg = {
                        "rid": rid_a,
                        "schema_version": (A.get("schema_version") if isinstance(A, dict) else None),
                        "design_intent": (A.get("design_intent") if isinstance(A, dict) else None),
                        "inputs_hash": (A.get("inputs_hash") if isinstance(A, dict) else None),
                        "expected": {
                            "ok": (A.get("ok") if isinstance(A, dict) else None),
                            "reason": (A.get("reason") if isinstance(A, dict) else None),
                        },
                    }
                    st.download_button("Download regression JSON", data=_shams_json_dumps(reg, indent=2, sort_keys=True).encode("utf-8"),
                                       file_name=f"regression_{rid_a}.json", mime="application/json", use_container_width=True, key="systems_reg_dl")
            except Exception as _e:
                st.caption(f"Reproduce/Diff unavailable: {_e!r}")

        # v185: Preset QA harness (in-app, developer friendly)
        with st.expander("Preset QA harness (developer)", expanded=False):
            st.caption("Runs the repo-level smoke QA (scripts/run_systems_qa.py) inside the app process. PASS/FAIL only.")
            if st.button("Run Systems QA smoke check", use_container_width=True, key="systems_run_qa_btn"):
                try:
                    from scripts.run_systems_qa import main as _qa_main
                    rc = int(_qa_main())
                    if rc == 0:
                        st.success("SYSTEMS_QA: PASS")
                    else:
                        st.error(f"SYSTEMS_QA: FAIL (exit {rc})")
                except Exception as _e:
                    st.error(f"QA runner failed: {_e!r}")


        # Latest limiter explanations
        st.subheader("Limiter graph")
        st.write("Curated causal map: **what usually drives each constraint** (qualitative).")
        st.json(_LIMITER_GRAPH)

        # Local sensitivities (fast finite-difference around current Systems base)
        st.subheader("Local sensitivities (finite difference)")
        st.caption("Computes local sensitivities around the current Systems base point using the same evaluator as the point model (0-D).")
        _sens_knobs = st.multiselect("Knobs", ["R0_m","a_m","kappa","delta","Bt_T","Ip_MA","fG","Paux_MW"], default=["Ip_MA","fG","Paux_MW"])
        _sens_outputs = st.multiselect("Outputs", ["Q_DT_eqv","H98","Pfus_MW","Palpha_MW","beta_N","nbar20","Tbr","q95","q_div","B_peak_T","sigma_vm_MPa"], default=["Q_DT_eqv","H98","q95"])
        _h = st.number_input("Step size (absolute)", value=0.05, min_value=1e-6, format="%.6f", key="systems_sens_h")
        if st.button("Compute sensitivities", use_container_width=True, key="systems_sens_btn"):
            try:
                from solvers.sensitivity import local_sensitivities
                def _ev(x: PointInputs):
                    out = _ui_evaluate(x, origin="Systems")
                    return out if isinstance(out, dict) else {}
                sens = local_sensitivities(base, params=_sens_knobs, outputs=_sens_outputs, evaluator=_ev, h=float(_h))
                # render as table
                rows=[]
                for outk, dd in (sens or {}).items():
                    for pk, dv in (dd or {}).items():
                        rows.append({"output": outk, "param": pk, "d(output)/d(param)": float(dv)})
                if rows:
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                else:
                    st.info("No sensitivity data returned.")
                _sys_journal_append("sensitivities", {"knobs": _sens_knobs, "outputs": _sens_outputs, "h": float(_h)})
            except Exception as e:
                st.error(f"Sensitivity failed: {e}")

        # Candidates + frontier (Pareto) view
        st.subheader("Candidates, families, and frontier (Pareto)")
        cands = _sys_get_candidates()
        if not cands:
            st.info("No candidates available yet. Run Recovery or Feasible Search first.")
        else:
            ranked = _rank_candidates(cands, st.session_state.get("systems_ranking_profile","Balanced"))
            # v185: Explain why the top candidate wins (score breakdown)
            try:
                if ranked:
                    top = ranked[0]
                    st.subheader("Why the top candidate wins (explainable ranking)")
                    bd = top.get("score_breakdown") if isinstance(top, dict) else None
                    if not isinstance(bd, dict):
                        # Fallback: reconstruct minimal breakdown
                        bd = {
                            "perf_score": _cand_perf_score(top),
                            "margin_score": _cand_margin_score(top),
                            "distance_score": float(top.get("distance_score", 0.0)) if isinstance(top, dict) else 0.0,
                            "total_score": float(top.get("score", _cand_perf_score(top)+_cand_margin_score(top))) if isinstance(top, dict) else (_cand_perf_score(top)+_cand_margin_score(top)),
                            "tie_breakers": top.get("tie_breakers", []) if isinstance(top, dict) else [],
                        }
                    st.json(bd)

                    # v185: Research sanity rails - warn if best-compromise is outside validity regime
                    try:
                        if _design_intent_key() == "research":
                            vf = _validity_summary(_sys_latest_art if isinstance(_sys_latest_art, dict) else {})
                            flags = list(vf.get("flags") or [])
                            if len(flags) >= 4 or float(vf.get("validity_score", 1.0)) < 0.6:
                                st.warning("Sanity rail: candidate appears outside typical validated regime (many validity flags). Treat as exploratory only.")
                    except Exception:
                        pass
            except Exception:
                pass

            # Families
            fam={}
            for c in ranked:
                fam.setdefault(_candidate_family(c), []).append(c)
            st.write({k: len(v) for k,v in fam.items()})
            # Frontier axes
            xk = st.selectbox("Frontier X", ["perf_score","margin_score"], index=0, key="systems_frontier_x")
            yk = st.selectbox("Frontier Y", ["margin_score","perf_score"], index=1, key="systems_frontier_y")
            # Build points
            pts=[]
            for c in ranked:
                pts.append({
                    "id": str(c.get("inputs_hash") or c.get("hash") or ""),
                    "perf_score": _cand_perf_score(c),
                    "margin_score": _cand_margin_score(c),
                    "family": _candidate_family(c),
                })
            try:
                import pandas as _pd
                df=_pd.DataFrame(pts)
                st.dataframe(df, use_container_width=True, hide_index=True)
                # simple plotly scatter if available
                try:
                    import plotly.express as px
                    fig=px.scatter(df, x=xk, y=yk, hover_name="id", color="family")
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
            except Exception:
                pass

        # Decision journal
        st.subheader("Decision journal (Design Stories 2.0)")
        j = st.session_state.get("systems_journal", [])
        st.write(f"Entries: {len(j)}")
        if j:
            st.dataframe(list(reversed(j[-50:])), use_container_width=True, hide_index=True)
            # export as markdown
            try:
                import json as _json
                md = "# SHAMS Systems Mode - Decision Journal\n\n"
                for e in j:
                    md += f"- **{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.get('ts_unix',0)))}** [{e.get('kind','')}] step={e.get('workflow_step','')} intent={e.get('design_intent','')}\n"
                st.download_button("Download decision journal (md)", data=md.encode("utf-8"), file_name="systems_decision_journal.md", mime="text/markdown", use_container_width=True, key="systems_dl_journal_md")
                st.download_button("Download decision journal (json)", data=_json.dumps(j, indent=2, sort_keys=True, default=str).encode("utf-8"), file_name="systems_decision_journal.json", mime="application/json", use_container_width=True, key="systems_dl_journal_json")
                # Decision Report PDF (journal + top candidates + artifact hashes)
                try:
                    from tools.reports.decision_report import build_decision_report_pdf_bytes
                    _cand = _sys_get_candidates()
                    _ranked = _rank_candidates(_cand, st.session_state.get("systems_ranking_profile","Balanced")) if _cand else []
                    pdf_bytes = build_decision_report_pdf_bytes(
                        systems_artifact=_sys_latest_art if isinstance(_sys_latest_art, dict) else None,
                        point_artifact=getattr(_v92_state_get(), 'last_point_artifact', None),
                        journal=j,
                        top_candidates=_ranked[:10],
                    )
                    st.download_button("Download Decision Report (PDF)", data=pdf_bytes, file_name="shams_systems_decision_report.pdf", mime="application/pdf", use_container_width=True, key="systems_dl_decision_report_pdf")

                    # v185: Executive Summary (1-page PDF)
                    try:
                        from tools.reports.executive_summary import build_executive_summary_pdf_bytes
                        _cand = _sys_get_candidates()
                        _ranked = _rank_candidates(_cand, st.session_state.get("systems_ranking_profile","Balanced")) if _cand else []
                        pdf2 = build_executive_summary_pdf_bytes(
                            systems_artifact=_sys_latest_art if isinstance(_sys_latest_art, dict) else None,
                            point_artifact=getattr(_v92_state_get(), 'last_point_artifact', None),
                            top_candidate=_ranked[0] if _ranked else None,
                        )
                        st.download_button("Download Executive Summary (PDF, 1 page)", data=pdf2, file_name="shams_systems_executive_summary.pdf", mime="application/pdf", use_container_width=True, key="systems_dl_exec_summary_pdf")
                    except Exception as _e2:
                        st.caption(f"Executive summary unavailable: {_e2}")

                except Exception as _e:
                    st.caption(f"PDF report unavailable: {_e}")

            except Exception:
                pass
        else:
            st.caption("Journal entries are created when you run sensitivities or systems actions (precheck/recovery/search/apply/export).")

        # Artifact viewer (load JSON, upgrade schema, display)
        st.subheader("Artifact viewer (schema-stable)")
        up = st.file_uploader("Upload a Systems artifact JSON", type=["json"], key="systems_artifact_uploader")
        if up is not None:
            try:
                raw = up.read()
                obj = json.loads(raw.decode("utf-8"))
                from src.systems.schema import upgrade_systems_artifact
                obj2 = upgrade_systems_artifact(obj)
                st.success(f"Loaded artifact. schema_version={obj2.get('schema_version','?')}")
                if st.button("Restore full Systems UI state from this artifact", use_container_width=True, key="systems_restore_from_artifact_btn"):
                    try:
                        st.session_state["systems_last_solve_artifact"] = obj2
                        try:
                            _v92_state_get().last_systems_result = obj2
                        except Exception:
                            pass

                        ui = obj2.get("ui_state") if isinstance(obj2.get("ui_state"), dict) else obj2

                        # Restore common cached panels if present
                        for k in ["systems_run_cards","systems_journal","v178_last_precheck","v178_last_recovery","v178_fs_last"]:
                            if isinstance(ui, dict) and (k in ui):
                                st.session_state[k] = ui.get(k)

                        # Restore workflow/intention hints
                        st.session_state["_pending_workflow_step"] = str((ui.get("workflow_step") if isinstance(ui, dict) else "") or "Diagnose")
                        if isinstance(ui, dict) and ui.get("design_intent"):
                            st.session_state["design_intent"] = ui.get("design_intent")

                        st.success("Systems UI state restored from artifact.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Restore failed: {e}")

                st.json(obj2)
                _sys_journal_append("artifact_view", {"file": up.name, "schema_version": obj2.get("schema_version", None)})
            except Exception as e:
                st.error(f"Failed to load artifact: {e}")

        # Validity / confidence
        st.subheader("Model validity & confidence")
        if isinstance(_sys_latest_art, dict):
            vs = _validity_summary(_sys_latest_art)
            st.write(vs)
            if vs.get("flags"):
                st.warning("Some typical-range / validity flags are present. Treat results as assumption-dependent.")
        else:
            st.caption("No Systems artifact cached yet.")
# Run Cards (MUST): standardized summaries for every Systems action
    # -----------------------------
    with st.expander('Run cards (history)', expanded=False):
        cards = st.session_state.get('systems_run_cards', []) or []
        if not cards:
            st.info('No Systems run cards yet. Run precheck / recovery / search / solve to populate.')
        else:
            import pandas as _pd
            rows = []
            for c in list(cards)[::-1]:
                o = c.get('outcome', {}) or {}
                rows.append({
                    'ts': c.get('ts'),
                    'kind': c.get('kind'),
                    'status': o.get('status'),
                    'reason': o.get('reason'),
                    'dominant_limiter': o.get('dominant_limiter'),
                })
            st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True)
            # Detail view
            idx = st.number_input('Detail index (0 = most recent)', min_value=0, max_value=max(0, len(cards)-1), value=0, step=1)
            try:
                cc = list(cards)[-(int(idx)+1)]
                st.markdown('**Details**')
                st.json(cc)
            except Exception:
                pass


    # -----------------------------
    # Design stories (COULD): save/load decision-grade snapshots
    # -----------------------------
    st.session_state.setdefault('systems_design_stories', [])
    with st.expander('Design stories (save / load / export)', expanded=False):
        stories = st.session_state.get('systems_design_stories', []) or []
        name = st.text_input('Story name', value=f"Story {len(stories)+1}", key='systems_story_name')
        notes = st.text_area('Notes (optional)', value='', key='systems_story_notes', height=80)
        if st.button('Save current Systems story', use_container_width=True, key='systems_story_save'):
            try:
                story = {
                    'ts': _sys_now_iso(),
                    'name': str(name).strip() or f"Story {len(stories)+1}",
                    'notes': str(notes or ''),
                    'design_intent': st.session_state.get('design_intent'),
                    'base_overrides': dict(st.session_state.get('systems_base_overrides', {}) or {}),
                    'bounds_overrides': dict(st.session_state.get('systems_bounds_overrides', {}) or {}),
                    'inputs_overrides': dict(st.session_state.get('systems_inputs_overrides', {}) or {}),
                    'last_precheck': getattr(st.session_state.get('last_precheck_report', None), '__dict__', None),
                    'last_recovery': dict(st.session_state.get('v178_last_recovery', {}) or {}),
                    'last_feasible_search': dict(st.session_state.get('v178_fs_last', {}) or {}),
                    'last_run_card': (st.session_state.get('systems_run_cards', []) or [])[-1] if (st.session_state.get('systems_run_cards') or []) else None,
                }
                st.session_state['systems_design_stories'] = (stories + [story])[-50:]
                st.success('Saved.')
            except Exception as _e:
                st.error(f'Failed to save: {_e}')

        if stories:
            st.markdown('**Saved stories**')
            labels = [f"{i}: {s.get('name','(unnamed)')} ({s.get('ts','')})"for i, s in enumerate(stories)]
            sel = st.selectbox('Select', options=list(range(len(stories))), format_func=lambda i: labels[i], key='systems_story_sel')
            s = stories[int(sel)]
            c1, c2 = st.columns(2)
            with c1:
                if st.button('Load Base + x0 from story', use_container_width=True, key='systems_story_load'):
                    try:
                        # Load Base overrides (staged safely)
                        bo = dict(s.get('base_overrides', {}) or {})
                        st.session_state['systems_base_overrides'] = bo
                        st.session_state['systems_pending_base_apply'] = dict(bo)
                        st.session_state['systems_pending_base_apply_source'] = 'StoryLoadBase'
                        # Load x0 into bounds overrides if available
                        bdo = dict(s.get('bounds_overrides', {}) or {})
                        if bdo:
                            st.session_state['systems_bounds_overrides'] = bdo
                        # Load inputs overrides (diagnostic limits etc.)
                        io = dict(s.get('inputs_overrides', {}) or {})
                        if io:
                            st.session_state['systems_inputs_overrides'] = io
                        st.success('Loaded. Re-running precheck…')
                        st.session_state['systems_run_precheck_now'] = True
                        st.rerun()
                    except Exception as _e:
                        st.error(f'Load failed: {_e}')
            with c2:
                if st.button('Delete story', use_container_width=True, key='systems_story_delete'):
                    try:
                        st.session_state['systems_design_stories'] = [ss for j, ss in enumerate(stories) if j != int(sel)]
                        st.success('Deleted.')
                        st.rerun()
                    except Exception:
                        pass
            with st.expander('Story details', expanded=False):
                st.json(s)
            try:
                import json as _json
                st.download_button('Export stories JSON', data=_json.dumps(stories, indent=2, sort_keys=True, default=str),
                                   file_name='shams_systems_design_stories.json', mime='application/json', use_container_width=True)
            except Exception:
                pass
        else:
            st.caption('No stories yet. Save a story after a Recovery/Search run.')

    # -----------------------------
    # Constraint activity timeline (SHOULD): summarize what dominated during a run
    # -----------------------------
    with st.expander('Constraint activity timeline (dominant limiter over steps)', expanded=False):
        src_opts2 = ['Seeded Recovery (last)', 'Feasible Search (last)']
        src2 = st.radio('Source', src_opts2, index=0, horizontal=True, key='systems_timeline_src')
        rows_tl = []
        try:
            if src2 == 'Seeded Recovery (last)':
                rep = st.session_state.get('v178_last_recovery', {}) or {}
                tr = rep.get('trace') or []
                for i, t in enumerate(tr):
                    rows_tl.append({
                        'i': i,
                        'feasible': bool(t.get('feasible')),
                        'V': t.get('V'),
                        'dominant': t.get('dominant'),
                    })
            else:
                rep = st.session_state.get('v178_fs_last', {}) or {}
                tr = rep.get('trace') or []
                for i, t in enumerate(tr):
                    hf = list(t.get('hard_failed', []) or [])
                    dom = None
                    if hf:
                        dom = hf[0]
                    rows_tl.append({
                        'i': i,
                        'feasible': bool(t.get('feasible')),
                        'V': t.get('V'),
                        'dominant': dom,
                        'min_margin': t.get('min_margin'),
                    })
        except Exception:
            rows_tl = []

        if not rows_tl:
            st.info('No trace available yet. Run Seeded Recovery or Feasible Search with trace enabled.')
        else:
            import pandas as _pd
            df = _pd.DataFrame(rows_tl)
            st.dataframe(df, use_container_width=True, hide_index=True)
            # Aggregate view
            try:
                doms = [r.get('dominant') for r in rows_tl if r.get('dominant')]
                if doms:
                    from collections import Counter
                    cnt = Counter(doms)
                    top = cnt.most_common(5)
                    st.markdown('**Most frequent dominant limiters**')
                    st.write('\n'.join([f"- {k}: {v} steps"for k, v in top]))
            except Exception:
                pass


    # -----------------------------
    # Stability & control margin certification (v374.0)
    # -----------------------------
    with st.expander('Stability & control margin certification (vertical / RWM / volt-seconds)', expanded=False):
        st.caption(
            "Deterministic, algebraic certification derived from the last Systems artifact (no solves, no iteration). "
            "Reports vertical stability proxy margin, RWM proximity, and CS flux-swing (volt-seconds) headroom."
        )

        # Safe defaults (UI law): never conditionally define keys used later.
        st.session_state.setdefault('systems_stability_cert', None)
        eps_active = float(st.session_state.get('systems_stability_eps_active', 0.01))
        eps_tight = float(st.session_state.get('systems_stability_eps_tight', 0.10))
        probe_frac = float(st.session_state.get('systems_stability_probe_frac', 0.01))

        cA, cB, cC = st.columns([1, 1, 1])
        with cA:
            st.session_state['systems_stability_eps_active'] = st.number_input('ε_active', min_value=0.0, max_value=0.5, value=eps_active, step=0.005, format='%.3f')
        with cB:
            st.session_state['systems_stability_eps_tight'] = st.number_input('ε_tight', min_value=0.0, max_value=1.0, value=eps_tight, step=0.01, format='%.2f')
        with cC:
            _stability_probe_frac = st.number_input(
                'Probe fraction', min_value=0.0, max_value=0.1,
                value=float(st.session_state.get('systems_stability_probe_frac', probe_frac)),
                step=0.005, format='%.3f', key='systems_stability_probe_frac_input'
            )
            st.session_state['systems_stability_probe_frac'] = float(_stability_probe_frac)

        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_stability_cert_btn'):
                try:
                    from src.certification.stability_control_certification_v374 import (
                        certify_stability_control_margins,
                        certification_table_rows,
                    )

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    cert = certify_stability_control_margins(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                        eps_active=float(st.session_state['systems_stability_eps_active']),
                        eps_tight=float(st.session_state['systems_stability_eps_tight']),
                        probe_frac=float(st.session_state['systems_stability_probe_frac']),
                    )
                    st.session_state['systems_stability_cert'] = cert
                    st.success('Certification computed and cached (systems_stability_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_stability_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.stability_control_certification_v374 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                except Exception:
                    st.json(cert)

                # Download JSON
                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_stability_control_margin_certification_v374.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_stability_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    # -----------------------------
    # Control & actuation authority (v378.0)
    # -----------------------------
    with st.expander('Control & actuation authority (PF/RWM, certified) — actuator margins', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Computes actuator margin proxies: VS bandwidth/power caps, PF power cap, RWM power proxy vs cap, and CS/V-loop headroom."
        )

        st.session_state.setdefault('systems_control_actuation_cert', None)
        # Governance caps (UI inputs; do not mutate truth).
        st.session_state.setdefault('systems_v378_vs_bw_cap_Hz', 300.0)
        st.session_state.setdefault('systems_v378_vs_P_cap_MW', 50.0)
        st.session_state.setdefault('systems_v378_pf_P_cap_MW', 200.0)
        st.session_state.setdefault('systems_v378_rwm_P_cap_MW', 20.0)
        st.session_state.setdefault('systems_v378_rwm_P_ref_MW', 10.0)

        cap_cols = st.columns(5)
        with cap_cols[0]:
            st.session_state['systems_v378_vs_bw_cap_Hz'] = st.number_input(
                'VS BW cap (Hz)', min_value=1.0, max_value=5000.0,
                value=float(st.session_state.get('systems_v378_vs_bw_cap_Hz', 300.0)),
                step=10.0, format='%.1f'
            )
        with cap_cols[1]:
            st.session_state['systems_v378_vs_P_cap_MW'] = st.number_input(
                'VS P cap (MW)', min_value=0.1, max_value=2000.0,
                value=float(st.session_state.get('systems_v378_vs_P_cap_MW', 50.0)),
                step=5.0, format='%.2f'
            )
        with cap_cols[2]:
            st.session_state['systems_v378_pf_P_cap_MW'] = st.number_input(
                'PF P cap (MW)', min_value=0.1, max_value=5000.0,
                value=float(st.session_state.get('systems_v378_pf_P_cap_MW', 200.0)),
                step=10.0, format='%.2f'
            )
        with cap_cols[3]:
            st.session_state['systems_v378_rwm_P_cap_MW'] = st.number_input(
                'RWM P cap (MW)', min_value=0.1, max_value=2000.0,
                value=float(st.session_state.get('systems_v378_rwm_P_cap_MW', 20.0)),
                step=1.0, format='%.2f'
            )
        with cap_cols[4]:
            st.session_state['systems_v378_rwm_P_ref_MW'] = st.number_input(
                'RWM P ref (MW)', min_value=0.1, max_value=2000.0,
                value=float(st.session_state.get('systems_v378_rwm_P_ref_MW', 10.0)),
                step=1.0, format='%.2f'
            )

        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_control_actuation_cert_btn'):
                try:
                    from src.certification.control_actuation_certification_v378 import (
                        certify_control_actuation,
                        ActuationCaps,
                    )

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    caps = ActuationCaps(
                        vs_bandwidth_cap_Hz=float(st.session_state.get('systems_v378_vs_bw_cap_Hz', 300.0)),
                        vs_power_cap_MW=float(st.session_state.get('systems_v378_vs_P_cap_MW', 50.0)),
                        pf_power_cap_MW=float(st.session_state.get('systems_v378_pf_P_cap_MW', 200.0)),
                        rwm_power_cap_MW=float(st.session_state.get('systems_v378_rwm_P_cap_MW', 20.0)),
                        rwm_power_ref_MW=float(st.session_state.get('systems_v378_rwm_P_ref_MW', 10.0)),
                    )

                    cert = certify_control_actuation(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                        caps=caps,
                    )
                    st.session_state['systems_control_actuation_cert'] = cert
                    st.success('Certification computed and cached (systems_control_actuation_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_control_actuation_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.control_actuation_certification_v378 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    tier = (((cert.get('tiers') or {}).get('overall')) if isinstance(cert.get('tiers'), dict) else None)
                    if tier in ('BLOCK', 'TIGHT'):
                        st.warning('Actuation authority is tight or blocking (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_control_actuation_certification_v378.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_control_actuation_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    # -----------------------------
    # Confinement & transport certification (v376.0)
    # -----------------------------
    with st.expander('Confinement & transport authority (certified) — H98 credibility', expanded=False):
        st.caption(
            "Deterministic certification derived from the last Systems artifact (no solves, no iteration). "
            "Reports H98 vs a conservative credibility envelope (intent-aware) and optional τE terms if available."
        )

        # UI law: safe defaults; no conditional variable definitions.
        cA, cB = st.columns([1, 2])
        with cA:
            _transport_probe_frac = st.number_input(
                'Probe fraction', min_value=0.0, max_value=0.1,
                value=float(st.session_state.get('systems_transport_probe_frac', probe_frac)),
                step=0.005, format='%.3f', key='systems_transport_probe_frac_input'
            )
            st.session_state['systems_transport_probe_frac'] = float(_transport_probe_frac)
        with cB:
            st.caption('Envelope is intent-aware (reactor tighter than research). This is a credibility contract only; truth is unchanged.')

        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_transport_cert_btn'):
                try:
                    from src.certification.transport_confinement_certification_v376 import (
                        certify_transport_confinement,
                    )

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    cert = certify_transport_confinement(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                        probe_frac=float(st.session_state['systems_transport_probe_frac']),
                    )
                    st.session_state['systems_transport_cert'] = cert
                    st.success('Certification computed and cached (systems_transport_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_transport_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.transport_confinement_certification_v376 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    cls = ((cert.get('classification') or {}).get('H98_class') if isinstance(cert.get('classification'), dict) else None)
                    if cls == 'super-credible-viol':
                        st.warning('H98 exceeds the credibility envelope for this intent. This is a certification flag; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_transport_confinement_certification_v376.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_transport_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)




    # -----------------------------
    # Transport profile authority (v382.0)
    # -----------------------------
    with st.expander(' Transport profile authority (certified) — 1.5D-lite proxies', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Best-effort 1.5D-lite proxies: peaking-factor plausibility (central/avg) and internal inductance (li) bounds by intent tier. "
            "This is a credibility contract only; truth is unchanged."
        )

        st.session_state.setdefault('systems_transport_profile_cert', None)
        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_transport_profile_cert_btn'):
                try:
                    from src.certification.transport_profile_certification_v382 import (
                        certify_transport_profile,
                    )

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    cert = certify_transport_profile(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                    ).to_dict()

                    st.session_state['systems_transport_profile_cert'] = cert
                    st.success('Certification computed and cached (systems_transport_profile_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_transport_profile_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.transport_profile_certification_v382 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    tier = str(cert.get('tier') or '')
                    if tier in ('TIGHT', 'BLOCK'):
                        st.warning('Transport profile authority is tight/blocking (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_transport_profile_certification_v382.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_transport_profile_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)
    # -----------------------------
    # Current drive authority (v381.0)
    # -----------------------------
    # -----------------------------
    # Materials & lifetime tightening authority (v384.0.0)
    # -----------------------------
    with st.expander(' Materials & lifetime tightening (certified) — divertor+magnet + downtime→CF', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Summarizes the v384 lifetime proxies and the replacement-coupled capacity factor/cost proxy."
        )

        st.session_state.setdefault('systems_materials_lifetime_v384_cert', None)
        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_materials_life_v384_cert_btn'):
                try:
                    from src.certification.materials_lifetime_certification_v384 import (
                        certify_materials_lifetime_v384,
                    )

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    cert = certify_materials_lifetime_v384(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                    ).to_dict()

                    st.session_state['systems_materials_lifetime_v384_cert'] = cert
                    st.success('Certification computed and cached (systems_materials_lifetime_v384_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_materials_lifetime_v384_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.materials_lifetime_certification_v384 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    tier = str(cert.get('tier') or '')
                    if tier in ('BLOCK', 'TIGHT'):
                        st.warning('Materials/lifetime authority is tight/blocking (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_materials_lifetime_certification_v384.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_materials_life_v384_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    with st.expander(' Current drive authority (certified) — regime-aware credibility', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Certifies current-drive and non-inductive fraction claims with conservative efficiency bounds and density-based regime flags."
        )

        st.session_state.setdefault('systems_current_drive_cert', None)
        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_current_drive_cert_btn'):
                try:
                    from src.certification.current_drive_certification_v381 import evaluate_current_drive_authority

                    outs = dict(last_sys_art.get('outputs') or {})
                    _cert = evaluate_current_drive_authority(outs).to_dict()
                    st.session_state['systems_current_drive_cert'] = _cert
                    st.success('Certification computed and cached (systems_current_drive_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_current_drive_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.current_drive_certification_v381 import certification_table_rows
                    st.dataframe(_pd.DataFrame([certification_table_rows(cert)]), use_container_width=True, hide_index=True)
                    tier = str(cert.get('tier') or '')
                    if tier in ('BLOCK', 'TIGHT'):
                        st.warning('Current-drive authority is tight or blocking (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_current_drive_certification_v381.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_current_drive_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    # -----------------------------
    # Current drive multi-channel library certification (v395.0)
    # -----------------------------
    with st.expander(' Current drive library (v395) — multi-channel mix bookkeeping (certified)', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Summarizes v395 multi-channel (ECCD/LHCD/NBI/ICRF) CD bookkeeping if present; otherwise reports UNAVAILABLE."
        )

        st.session_state.setdefault('systems_current_drive_lib_v395_cert', None)
        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_current_drive_lib_v395_cert_btn'):
                try:
                    from src.certification.current_drive_library_certification_v395 import certify_current_drive_library_v395

                    outs = dict(last_sys_art.get('outputs') or {})
                    _cert = certify_current_drive_library_v395(outs).to_dict()
                    st.session_state['systems_current_drive_lib_v395_cert'] = _cert
                    st.success('Certification computed and cached (systems_current_drive_lib_v395_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_current_drive_lib_v395_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.current_drive_library_certification_v395 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    tier = str(cert.get('tier') or '')
                    if tier in ('BLOCK', 'TIGHT'):
                        st.warning('Current-drive library authority is tight/blocking (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_current_drive_library_certification_v395.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_current_drive_lib_v395_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    # -----------------------------
    # Disruption severity & quench proxy authority (v377.0)
    # -----------------------------
    with st.expander('Disruption & quench authority (certified) — severity proxies', expanded=False):
        st.caption(
            "Deterministic governance-only certification derived from the last Systems artifact (no solves, no iteration). "
            "Adds consequence-severity proxies: disruption proximity index, thermal quench severity W/A, and halo force proxy."
        )

        st.session_state.setdefault('systems_disruption_quench_cert', None)
        can_compute = isinstance(last_sys_art, dict) and isinstance(last_sys_art.get('outputs'), dict)
        if not can_compute:
            st.info('No Systems artifact available yet. Run a Systems solve first.')
        else:
            if st.button('Compute certification (cache)', use_container_width=True, key='systems_compute_disruption_quench_cert_btn'):
                try:
                    from src.certification.disruption_quench_certification_v377 import certify_disruption_quench

                    outs = dict(last_sys_art.get('outputs') or {})
                    ins = dict(last_sys_art.get('inputs') or {})
                    run_id = str(last_sys_art.get('run_id') or (last_sys_art.get('run') or {}).get('run_id') or '')
                    ih = str(last_sys_art.get('inputs_hash') or '')

                    cert = certify_disruption_quench(
                        outputs=outs,
                        inputs=ins,
                        run_id=(run_id or None),
                        inputs_hash=(ih or None),
                    )
                    st.session_state['systems_disruption_quench_cert'] = cert
                    st.success('Certification computed and cached (systems_disruption_quench_cert).')
                except Exception as _e:
                    st.error(f'Certification failed: {_e}')

            cert = st.session_state.get('systems_disruption_quench_cert', None)
            if isinstance(cert, dict):
                try:
                    import pandas as _pd
                    from src.certification.disruption_quench_certification_v377 import certification_table_rows
                    rows, cols = certification_table_rows(cert)
                    st.dataframe(_pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
                    tier = (((cert.get('metrics') or {}).get('disruption_proximity_tier')) if isinstance(cert.get('metrics'), dict) else None)
                    if tier == 'HIGH':
                        st.warning('High disruption proximity index (proxy). Treat as governance risk; truth is unchanged.')
                except Exception:
                    st.json(cert)

                try:
                    st.download_button(
                        'Download certification JSON',
                        data=json.dumps(cert, indent=2, sort_keys=True, default=str),
                        file_name='systems_disruption_quench_certification_v377.json',
                        mime='application/json',
                        use_container_width=True,
                        key='systems_dl_disruption_quench_cert_json',
                    )
                except Exception:
                    pass

                with st.expander('Certification details (JSON)', expanded=False):
                    st.json(cert)

    # -----------------------------
    # Frontier visualization (SHOULD)
    # -----------------------------
    with st.expander('Frontier visualization (samples / trace)', expanded=False):
        src_opts = ['Precheck samples', 'Seeded Recovery trace (last)', 'Feasible Search trace (last)']
        src_sel = st.radio('Source', src_opts, index=0, horizontal=True, key='sys_frontier_src')
        x_key = st.selectbox('X-axis variable', ['R0_m','a_m','Bt_T','Ti_keV','Paux_MW','kappa','t_shield_m'], index=0, key='sys_frontier_x')
        y_opts = ['q_div_MW_m2','sigma_vm','sigma_hoop_MPa','TBR','H98','Q_DT_eqv','Pfus_DT_adj_MW']
        # Recovery trace doesn't store full outputs; use V as the y-axis.
        if src_sel == 'Seeded Recovery trace (last)':
            y_opts = ['V (hard violation)']
        y_key = st.selectbox('Y-axis metric', y_opts, index=0, key='sys_frontier_y')
        pts = []
        try:
            if src_sel == 'Precheck samples':
                _pre = st.session_state.get('last_precheck_report', None)
                if _pre is not None:
                    _samp = getattr(_pre, 'samples', None) or []
                    for sr in _samp:
                        try:
                            sp = getattr(sr, 'sample', None)
                            xv = float(getattr(sp, 'values', {}).get(x_key, float('nan')))
                            yv = float(getattr(sr, 'outputs', {}).get(y_key, float('nan')))
                            feas = (len(getattr(sr, 'hard_failed', []) or []) == 0)
                            if math.isfinite(xv) and math.isfinite(yv):
                                pts.append((xv, yv, feas))
                        except Exception:
                            continue
            elif src_sel == 'Seeded Recovery trace (last)':
                rep = st.session_state.get('v178_last_recovery', {}) or {}
                tr = rep.get('trace') or []
                for t in tr:
                    try:
                        x = t.get('x', {}) or {}
                        xv = float(x.get(x_key, float('nan')))
                        yv = float(t.get('V', float('nan')))
                        feas = bool(t.get('feasible'))
                        if math.isfinite(xv) and math.isfinite(yv):
                            pts.append((xv, yv, feas))
                    except Exception:
                        continue
            else:
                rep = st.session_state.get('v178_fs_last', {}) or {}
                tr = rep.get('trace') or []
                for t in tr:
                    try:
                        x = t.get('x', {}) or {}
                        xv = float(x.get(x_key, float('nan')))
                        if y_key == 'V (hard violation)':
                            yv = float(t.get('V', float('nan')))
                        else:
                            met = t.get('metrics', {}) or {}
                            yv = float(met.get(y_key, float('nan')))
                        feas = bool(t.get('feasible'))
                        if math.isfinite(xv) and math.isfinite(yv):
                            pts.append((xv, yv, feas))
                    except Exception:
                        continue
        except Exception:
            pts = []

        if not pts:
            st.info('No points available yet. Run a precheck, seeded recovery, or feasible search first.')
        else:
            try:
                import matplotlib.pyplot as _plt
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cs = [p[2] for p in pts]
                fig = _plt.figure()
                ax = fig.add_subplot(111)
                # Plot feasible vs infeasible without hardcoding colors (matplotlib chooses default cycle)
                xf = [x for x, c in zip(xs, cs) if c]
                yf = [y for y, c in zip(ys, cs) if c]
                xi = [x for x, c in zip(xs, cs) if not c]
                yi = [y for y, c in zip(ys, cs) if not c]
                if xf:
                    ax.scatter(xf, yf, label='feasible')
                if xi:
                    ax.scatter(xi, yi, label='infeasible')
                ax.set_xlabel(x_key)
                ax.set_ylabel(y_key)
                ax.legend()
                st.pyplot(fig, use_container_width=True)
            except Exception as _e:
                st.warning(f'Plot failed: {_e}')
            try:
                import json as _json
                st.download_button('Download plotted points JSON', data=_json.dumps([{'x':p[0],'y':p[1],'feasible':p[2]} for p in pts], indent=2, sort_keys=True), file_name='systems_frontier_points.json', mime='application/json', use_container_width=True)
            except Exception:
                pass

    with st.expander('Latest Systems summary (stateful)', expanded=False):
        if isinstance(last_sys_art, dict):
            outs = (last_sys_art.get('outputs') or {})
            st.write('Key outputs (from last Systems run):')
            st.json({
                'Q_DT_eqv': outs.get('Q_DT_eqv'),
                'H98': outs.get('H98'),
                'Pfus_DT_adj_MW': outs.get('Pfus_DT_adj_MW'),
                'P_net_e_MW': outs.get('P_net_e_MW'),
                'q_div_MW_m2': outs.get('q_div_MW_m2'),
                'sigma_hoop_MPa': outs.get('sigma_hoop_MPa'),
                'TBR': outs.get('TBR'),
            })
        else:
            st.info('No Systems artifact yet. Run a Systems solve to populate this summary.')



    # v176.1: always-visible solve controls (so users don't miss them)
    st.markdown('### Solve controls')
    csc1, csc2, csc3 = st.columns([2,2,3])
    with csc1:
        preset = st.selectbox(
            'Solve preset',
            ['Robust (recommended)', 'Fast'],
            index=0,
            key='v176_solve_preset',
            help='Robust uses smaller steps and more iterations; Fast uses more aggressive steps for quicker convergence when well-behaved.',
        )
    with csc2:
        warm_start = st.checkbox(
            'Warm-start (use last Systems solution)',
            value=True,
            key='v176_warm_start',
            help='Uses the last Systems solution values as the initial guess for solved variables (within bounds).',
        )
    with csc3:
        st.caption('Tip: targets/variables live in the expander below. Preset + warm-start affect solver behavior.')

    base0 = st.session_state.get("last_point_inp")
    if base0 is None:
        base0 = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)

    # v178.11: Robust Base-design apply
    #
    # Streamlit forbids mutating session_state entries that are bound to widgets
    # *after* those widgets have been instantiated in a run. Buttons in later
    # sections (Feasible Search / Seeded Recovery) previously attempted to
    # directly set widget keys like `sys_base_R0_m`, which can raise a
    # StreamlitAPIException and surface as "Failed to apply Base vars.".
    #
    # Fix: stage updates in `systems_pending_base_apply` and apply them here,
    # before the Base-design widgets are created.
    st.session_state.setdefault('systems_pending_base_apply', None)
    # Optional source tag for Undo/history attribution.
    st.session_state.setdefault('systems_pending_base_apply_source', None)
    st.session_state.setdefault('systems_base_history', [])
    _pending_base = st.session_state.get('systems_pending_base_apply')
    if isinstance(_pending_base, dict) and _pending_base:
        try:
            _keymap = {
                'R0_m': 'sys_base_R0_m',
                'a_m': 'sys_base_a_m',
                'kappa': 'sys_base_kappa',
                'delta': 'sys_base_delta',
                'Bt_T': 'sys_base_Bt_T',
                'Ti_keV': 'sys_base_Ti_keV',
                'Ti_over_Te': 'sys_base_Ti_over_Te',
                't_shield_m': 'sys_base_t_shield_m',
            }
            # Save current Base overrides for Undo.
            try:
                _bo_prev = dict(st.session_state.get('systems_base_overrides', {}) or {})
                st.session_state['systems_base_history'].append({
                    'ts_unix': float(time.time()),
                    'base_overrides': _bo_prev,
                    'source': str(st.session_state.get('systems_pending_base_apply_source') or 'pending_apply'),
                })
                # keep history bounded
                st.session_state['systems_base_history'] = st.session_state['systems_base_history'][-50:]
            except Exception:
                pass
            _bo_apply = st.session_state.get('systems_base_overrides', {}) or {}
            for _k, _v in list(_pending_base.items()):
                try:
                    _fv = float(_v)
                    _bo_apply[_k] = _fv
                    _wk = _keymap.get(_k)
                    if _wk:
                        st.session_state[_wk] = _fv
                except Exception:
                    pass
            st.session_state['systems_base_overrides'] = _bo_apply
        except Exception:
            pass
        # Always clear so a bad value doesn't loop forever.
        st.session_state['systems_pending_base_apply'] = None
        st.session_state['systems_pending_base_apply_source'] = None

    with st.expander("Base design (starting point)", expanded=False):
        # v178.1: allow Systems Mode tools (like Seeded Feasibility Recovery) to
        # apply recovered base-design values deterministically.
        # We do this by using explicit widget keys and a small session_state
        # override dict. This does NOT change the physics/solver; it is UI state.
        st.session_state.setdefault('systems_base_overrides', {})
        _bo = st.session_state.get('systems_base_overrides', {}) or {}

        # Safety controls: undo/restore Base design overrides
        _hist = st.session_state.get('systems_base_history', []) or []
        u1, u2, u3 = st.columns([1.2, 1.2, 2.6])
        with u1:
            if st.button('Undo last Base apply', use_container_width=True, disabled=(len(_hist) == 0), key='sys_base_undo_btn'):
                try:
                    last = (st.session_state.get('systems_base_history') or [])[-1]
                    prev = dict(last.get('base_overrides') or {})
                    st.session_state['systems_base_overrides'] = prev
                    # Stage widget-key updates.
                    st.session_state['systems_pending_base_apply'] = dict(prev)
                    st.session_state['systems_run_precheck_now'] = True
                    try:
                        _alog('Systems', 'UndoBaseApply', {'source': str(last.get('source','')), 'n_keys': int(len(prev))})
                    except Exception:
                        pass
                    # Pop after staging
                    st.session_state['systems_base_history'] = (st.session_state.get('systems_base_history') or [])[:-1]
                    st.rerun()
                except Exception:
                    st.warning('Undo failed (unexpected).')
        with u2:
            if st.button('Clear Base history', use_container_width=True, disabled=(len(_hist) == 0), key='sys_base_clear_hist_btn'):
                st.session_state['systems_base_history'] = []
                st.rerun()
        with u3:
            if _hist:
                st.caption(f"Base history: {len(_hist)} step(s). Undo is local to this session.")
        colA, colB, colC = st.columns(3)
        with colA:
            R0_m = _num("R0 [m]", float(_bo.get('R0_m', _safe_get(base0, 'R0_m'))), 0.01, help="Major radius.", key='sys_base_R0_m')
            a_m = _num("a [m]", float(_bo.get('a_m', _safe_get(base0, 'a_m'))), 0.01, help="Minor radius.", key='sys_base_a_m')
            kappa = _num("κ [-]", float(_bo.get('kappa', _safe_get(base0, 'kappa'))), 0.01, help="Elongation.", key='sys_base_kappa')
            delta = _num("δ [-]", float(_bo.get('delta', getattr(base0, "delta", 0.0) or 0.0)), 0.02, min_value=0.0, max_value=0.8, help="Triangularity δ used only in the inboard radial-build clearance proxy.", key='sys_base_delta')
        with colB:
            Bt_T = _num("Bt [T]", float(_bo.get('Bt_T', _safe_get(base0, 'Bt_T'))), 0.1, help="On-axis toroidal field.", key='sys_base_Bt_T')
            Ti_keV = _num("Ti [keV]", float(_bo.get('Ti_keV', _safe_get(base0, 'Ti_keV'))), 0.5, help="Ion temperature (volume-average input in 0-D mode).", key='sys_base_Ti_keV')
            Ti_over_Te = _num("Ti/Te [-]", float(_bo.get('Ti_over_Te', getattr(base0, "Ti_over_Te", 2.0))), 0.05, help="Temperature ratio; sets Te.", key='sys_base_Ti_over_Te')
        with colC:
            t_shield_m = _num("Shield thickness [m]", float(_bo.get('t_shield_m', getattr(base0, "t_shield_m", 0.70))), 0.01, help="Inboard shielding thickness proxy (affects neutronics/HTS lifetime).", key='sys_base_t_shield_m')
            steady_state = st.checkbox("Steady-state (no CS pulse constraint)", value=bool(getattr(base0, "steady_state", True)))
            P_net_min_MW = _num("Minimum net electric [MW(e)]", float(getattr(base0, "P_net_min_MW", 0.0)), 5.0, help="Optional requirement; 0 disables hard requirement.")
        # model options
        st.markdown("**Model options**")
        m1, m2, m3 = st.columns(3)
        with m1:
            _c_label = st.selectbox("H-factor reference scaling (for H_scaling)", [
                'IPB98(y,2) (H98 basis)',
                'ITER89-P (L-mode)',
                'Kaye–Goldston (L-mode)',
                'Neo-Alcator (ohmic/L)',
                'Mirnov (ohmic)',
                'Shimomura (L-mode)',
            ], index=0)
            _c_map = {
                'IPB98(y,2) (H98 basis)': 'IPB98y2',
                'ITER89-P (L-mode)': 'ITER89P',
                'Kaye–Goldston (L-mode)': 'KG',
                'Neo-Alcator (ohmic/L)': 'NEOALC',
                'Mirnov (ohmic)': 'MIRNOV',
                'Shimomura (L-mode)': 'SHIMOMURA',
            }
            confinement_scaling = _c_map.get(_c_label, 'IPB98y2')
            confinement_model = str(confinement_scaling).lower()  # back-compat
        with m2:
            profile_model = st.selectbox("Profiles (½-D)", ["none","parabolic","pedestal"], index=0)
        with m3:
            zeff_mode = st.selectbox("Zeff mode", ["fixed","from_impurity"], index=0)
        profile_peaking_ne = _num("n peaking (alpha)", float(getattr(base0, "profile_peaking_ne", 1.0)), 0.1, help="Profile peaking control (if profiles enabled).")
        profile_peaking_T  = _num("T peaking (alpha)", float(getattr(base0, "profile_peaking_T", 1.5)), 0.1, help="Profile peaking control (if profiles enabled).")
        bootstrap_model = st.selectbox("Bootstrap proxy model", ["proxy", "improved"], index=0, help="Select bootstrap fraction proxy used for f_bs_proxy.")

        # Optional: compute TF Jop from winding-pack geometry (screening proxy)
        with st.expander("TF winding-pack Jop (optional)", expanded=False):
            tf_Jop_from_wp_geometry = st.checkbox(
                "Compute TF Jop from required ampere-turns and winding-pack area",
                value=bool(getattr(base0, "tf_Jop_from_wp_geometry", False)),
                help="If enabled, SHAMS derives an engineering current density from Bt,R0 and an explicit winding-pack area proxy (no detailed magnet model).",
            )
            tf_wp_width_m = _num("TF winding-pack width [m]", float(getattr(base0, "tf_wp_width_m", 0.25)), 0.01, min_value=0.05, help="Radial width of the winding pack used for Jop-from-geometry proxy.")
            tf_wp_height_factor = _num("TF winding-pack height factor [-]", float(getattr(base0, "tf_wp_height_factor", 2.4)), 0.05, min_value=0.5, help="Height proxy: H_wp = factor * (a*κ).")
            tf_wp_fill_factor = _num("TF winding-pack fill factor [-]", float(getattr(base0, "tf_wp_fill_factor", 1.0)), 0.05, min_value=0.05, max_value=1.0, help="Fraction of winding-pack area treated as conducting cross-section in the Jop-from-geometry proxy.")

        base = PointInputs(
            R0_m=R0_m, a_m=a_m, kappa=kappa, delta=delta, Bt_T=Bt_T,
            tf_Jop_from_wp_geometry=tf_Jop_from_wp_geometry,
            tf_wp_width_m=tf_wp_width_m,
            tf_wp_height_factor=tf_wp_height_factor,
            tf_wp_fill_factor=tf_wp_fill_factor,
            Ip_MA=float(getattr(base0, "Ip_MA", 8.0)),
            Ti_keV=Ti_keV,
            fG=float(getattr(base0, "fG", 0.8)),
            Paux_MW=float(getattr(base0, "Paux_MW", 20.0)),
            t_shield_m=t_shield_m,
            Ti_over_Te=Ti_over_Te,
            confinement_model=str(confinement_scaling).lower(),  # back-compat
            bootstrap_model=bootstrap_model,
            include_bootstrap_pressure_selfconsistency=False,
            f_bootstrap_consistency_abs_max=float("nan"),
            profile_model=profile_model,
            profile_peaking_ne=profile_peaking_ne,
            profile_peaking_T=profile_peaking_T,
            zeff_mode=zeff_mode,
            steady_state=steady_state,
            P_net_min_MW=P_net_min_MW,
            calib_confinement=float(st.session_state.get('calib_confinement', 1.0)),
            calib_divertor=float(st.session_state.get('calib_divertor', 1.0)),
            calib_bootstrap=float(st.session_state.get('calib_bootstrap', 1.0)),
        )

        # Persist the current Base-design fields so other Systems-mode tools can
        # reference them (e.g., Seeded Feasibility Recovery). This is UI state.
        st.session_state['systems_base_overrides'] = {
            'R0_m': float(R0_m),
            'a_m': float(a_m),
            'kappa': float(kappa),
            'delta': float(delta),
            'Bt_T': float(Bt_T),
            'Ti_keV': float(Ti_keV),
            'Ti_over_Te': float(Ti_over_Te),
            't_shield_m': float(t_shield_m),
        }

    if _sys_show('Setup','Advanced'):
        with st.expander("Targets and iteration variables", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                use_Q = st.checkbox("Target Q", value=True)
                Q_t = _num("Q target [-]", 10.0, 0.5, help="Target fusion gain Q.", key=PD_KEYS["Q_tgt"])
                # Default is intentionally conservative to help first-run success:
                # a single target (Q) with a single solved variable (Paux).
                use_H = st.checkbox("Target H98", value=False)
                H_t = _num("H98 target [-]", 1.15, 0.05, help="Target confinement H-factor.", key=PD_KEYS["H98_tgt"])
            with col2:
                use_Pnet = st.checkbox("Target net electric", value=False)
                Pnet_t = _num("P_net target [MW(e)]", 50.0, 5.0, help="Target net electric power.")
                # iteration vars
                st.markdown("**Iteration variables (solved)**")
                solve_Ip = st.checkbox("Solve Ip [MA]", value=False)
                solve_fG = st.checkbox("Solve fG [-]", value=False)
                solve_Paux = st.checkbox("Solve Paux [MW]", value=True)

            targets = {}
            if use_Q:
                targets["Q_DT_eqv"] = float(Q_t)
            if use_H:
                targets["H98"] = float(H_t)
            if use_Pnet:
                targets["P_e_net_MW"] = float(Pnet_t)

            variables = {}
            if solve_Ip:
                variables["Ip_MA"] = (float(base.Ip_MA), 0.5*float(base.Ip_MA), 1.8*float(base.Ip_MA))
            if solve_fG:
                variables["fG"] = (float(base.fG), 0.2, 1.2)
            if solve_Paux:
                variables["Paux_MW"] = (float(base.Paux_MW), 0.0, max(200.0, 3.0*float(base.Paux_MW)))

            # v177.2+: Persist assistant-applied bounds/target changes across reruns (Streamlit reruns on button clicks).
            st.session_state.setdefault('systems_bounds_overrides', {})
            st.session_state.setdefault('systems_targets_overrides', {})

            # Apply persisted overrides (if any) to the currently selected targets/variables.
            _bo = st.session_state.get('systems_bounds_overrides', {})
            if isinstance(_bo, dict) and _bo:
                for _vk, _bc in _bo.items():
                    if _vk in variables and isinstance(_bc, dict):
                        _x0, _lo, _hi = variables[_vk]
                        _lo2 = float(_bc.get('lo', _lo))
                        _hi2 = float(_bc.get('hi', _hi))
                        _x02 = float(_bc.get('x0', _x0))
                        variables[_vk] = (_x02, _lo2, _hi2)

            _to = st.session_state.get('systems_targets_overrides', {})
            if isinstance(_to, dict) and _to:
                for _tk, _tv in _to.items():
                    if _tk in targets:
                        targets[_tk] = float(_tv)

            # v323.1: Always persist the currently active Systems targets/variables.
            # Rationale: These dictionaries were previously defined only inside an
            # optional "Advanced"expander. If a user never opens that expander,
            # Streamlit reruns would leave `systems_targets`/`systems_variables`
            # empty, disabling Precheck/Solve buttons and making the UI appear
            # non-functional.
            st.session_state['systems_targets'] = dict(targets)
            st.session_state['systems_variables'] = dict(variables)

            # v176.1: preset + warm-start are defined above in always-visible Solve controls
            if preset.startswith('Fast'):
                _default_tol = 2e-3
                _default_damping = 0.85
                _default_max_iter = 25.0
                _default_trust = 10.0
            else:
                _default_tol = 1e-3
                _default_damping = 0.6
                _default_max_iter = 35.0
                _default_trust = 5.0


            tol = _num("Solver tolerance", _default_tol, 1e-3, help="Absolute tolerance on each target residual.", min_value=1e-5, max_value=1e-1)
            damping = _num("Damping", _default_damping, 0.05, help="Newton step damping for robustness.", min_value=0.1, max_value=1.0)

    
            # Persisted so downstream solve blocks never see an unbound name on reruns.
            max_iter = int(
                _num(
                    "Max iterations",
                    _default_max_iter,
                    1.0,
                    help="Maximum Newton iterations for Systems solve.",
                    min_value=1.0,
                    max_value=500.0,
                    key="systems_max_iter",
                )
            )
            override_trust = st.checkbox(
                "Override trust-region Δ (scaled)",
                value=False,
                help="Optional step-size cap in scaled variable space. Lower Δ for harder/brittle solves; raise Δ for faster convergence when stable.",
            )
            trust_delta = None
            if override_trust:
                trust_delta = _num(
                    "Trust-region Δ (scaled)",
                    _default_trust,
                    0.5,
                    help="Caps max(|dx_scaled|) per iteration. Smaller = safer steps; larger = more aggressive.",
                    min_value=0.1,
                    max_value=50.0,
                )
            st.caption("Solver trace will show `trust_region` events when steps are clipped or Δ adapts.")
            # Persist across reruns: this value is referenced later in the Systems solve block,
            # which may execute even if earlier UI branches were skipped.
            block_solve = st.checkbox(
                "Block-ordered solve (density → power → confinement → exhaust)",
                value=bool(st.session_state.get("systems_block_solve", False)),
                key="systems_block_solve",
                help="Runs a staged solve to reduce singular Jacobians. Stages are heuristic and fully traced.",
            )

            # Persist across reruns: this value is referenced later in the Systems solve block,
            # which may execute even if earlier UI branches were skipped.
            do_precheck = st.checkbox(
                "Feasibility-first precheck (explicit)",
                value=bool(st.session_state.get("systems_do_precheck", True)),
                key="systems_do_precheck",
                help="Before running Newton iterations, evaluate targets/constraints at variable bounds to detect obviously impossible target combinations. This does not change physics or solver behavior; it only exits early with an explicit reason when infeasibility is detected within the declared bounds.",
            )
            # Persist across reruns: referenced later in the Systems solve block.
            do_continuation = st.checkbox(
                "Continuation ramp to targets (path-following)",
                value=bool(st.session_state.get("systems_do_continuation", True)),
                key="systems_do_continuation",
                help="For coupled solves, ramp targets from the starting-point values toward the requested targets in small steps. Each step is solved explicitly and logged as `cont_step` / `cont_result`. This is a UI-side workflow for robustness; physics/models are unchanged.",
            )
            cont_steps = int(
                _num(
                    "Continuation steps",
                    float(st.session_state.get("systems_cont_steps", 10.0)),
                    1.0,
                    help="Number of continuation increments (only used when continuation is enabled and the solve is coupled).",
                    min_value=2.0,
                    max_value=50.0,
                    key="systems_cont_steps",
                )
            )
            st.caption("Continuation is applied only when there is more than one target or more than one solved variable.")

            # v177: feasibility-first solve (scout) and micro-atlas tools (integrated UI)
            cff1, cff2 = st.columns([2,3])
            with cff1:
                st.checkbox(
                    "Feasibility-first solve scout (find feasible start before Newton)",
                    value=False,
                    key='v177_feasibility_scout_enabled',
                    help="Runs a deterministic feasibility search within current variable bounds to find a starting point that satisfies hard constraints before targeting. This does not change physics; it only changes the initial guess.",
                )
            with cff2:
                cff2a, cff2b, cff2c = st.columns(3)
                with cff2a:
                    st.number_input('Scout samples', min_value=8, max_value=512, value=int(st.session_state.get('v177_scout_n_samples', 64)), step=8, key='v177_scout_n_samples')
                with cff2b:
                    st.number_input('Scout refine steps', min_value=0, max_value=200, value=int(st.session_state.get('v177_scout_n_refine', 20)), step=5, key='v177_scout_n_refine')
                with cff2c:
                    st.caption('Used only when scout is enabled.')

            with st.expander('Micro feasibility atlas (2D slice)', expanded=False):
                st.caption('Sweeps two solved variables over a small grid and shows feasibility / dominant hard constraint. Other solved variables are held at midpoint.')
                if len(variables) < 2:
                    st.info('Define at least two solved variables to use the atlas.')
                else:
                    try:
                        from systems.atlas import compute_micro_atlas
                    except Exception:
                        from src.systems.atlas import compute_micro_atlas  # type: ignore
                    keys = list(variables.keys())
                    ax1, ax2, ax3 = st.columns([2,2,2])
                    with ax1:
                        var_x = st.selectbox('X variable', keys, index=0, key='v177_atlas_var_x')
                    with ax2:
                        var_y = st.selectbox('Y variable', keys, index=1 if len(keys)>1 else 0, key='v177_atlas_var_y')
                    with ax3:
                        grid_n = int(st.number_input('Grid size', min_value=5, max_value=31, value=int(st.session_state.get('v177_atlas_grid_n', 15)), step=2, key='v177_atlas_grid_n'))

                    if st.button('Compute micro-atlas', key='v177_run_micro_atlas', use_container_width=True):
                        try:
                            from evaluator.core import Evaluator
                        except Exception:
                            from src.evaluator.core import Evaluator  # type: ignore
                        _ev_at = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)
                        atlas = compute_micro_atlas(base, variables, var_x, var_y, nx=grid_n, ny=grid_n, evaluator=_ev_at)
                        st.session_state['v177_last_micro_atlas'] = atlas

                    atlas = st.session_state.get('v177_last_micro_atlas', None)
                    if isinstance(atlas, dict) and atlas.get('ok'):
                        # --- Cartography 2.0 (derived-only) ---
                        with st.expander('Cartography 2.0 (robust / fragile / empty)', expanded=False):
                            try:
                                try:
                                    from systems.cartography2 import classify_cells, mechanism_histogram, label_fractions, mechanism_group_histogram
                                except Exception:
                                    from src.systems.cartography2 import classify_cells, mechanism_histogram, label_fractions, mechanism_group_histogram  # type: ignore

                                thr = float(st.number_input('Robust margin threshold (fraction)', min_value=0.0, max_value=0.50, value=float(st.session_state.get('v177_cart2_thr', 0.10)), step=0.01, key='v177_cart2_thr'))
                                c2 = classify_cells(atlas, robust_margin_min=thr)
                                if isinstance(c2, dict) and c2.get('ok'):
                                    labels = c2.get('labels') or []
                                    fr = label_fractions(labels)
                                    cA, cB, cC = st.columns(3)
                                    cA.metric('Robust', f"{100.0*fr.get('robust',0.0):.1f}%")
                                    cB.metric('Fragile', f"{100.0*fr.get('fragile',0.0):.1f}%")
                                    cC.metric('Empty', f"{100.0*fr.get('empty',0.0):.1f}%")

                                    hist = mechanism_histogram(atlas)
                                    gh = mechanism_group_histogram(atlas)
                                    if gh:
                                        rows_g = []
                                        total_fail = max(1, sum(gh.values()))
                                        for k, v in sorted(gh.items(), key=lambda kv: kv[1], reverse=True):
                                            rows_g.append({"group": k, "cells": int(v), "share": float(v)/float(total_fail)})
                                            if len(rows_g) >= 10:
                                                break
                                        try:
                                            import pandas as pd
                                            st.markdown('**Failing mechanism groups (overlay)**')
                                            st.dataframe(pd.DataFrame(rows_g), use_container_width=True, height=220, hide_index=True)
                                        except Exception:
                                            st.json(rows_g, expanded=False)

                                    # Present top mechanisms (excluding 'ok')
                                    rows = []
                                    for k, v in sorted(hist.items(), key=lambda kv: kv[1], reverse=True):
                                        if k == 'ok':
                                            continue
                                        rows.append({'mechanism': k, 'cells': int(v), 'share': float(v)/max(1,sum(hist.values()))})
                                        if len(rows) >= 12:
                                            break
                                    if rows:
                                        import pandas as pd
                                        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=260, hide_index=True)
                                    else:
                                        st.caption('No failing mechanisms in the current atlas slice.')
                                else:
                                    st.caption('Cartography2 classification unavailable for this atlas.')
                            except Exception as _e:
                                st.caption(f'Cartography2 unavailable: {_e}')
                        try:
                            import numpy as _np  # type: ignore
                            import matplotlib.pyplot as _plt  # type: ignore
                            dom = atlas.get('dominant') or []
                            cats = sorted({str(c) for row in dom for c in row})
                            cmap = {c:i for i,c in enumerate(cats)}
                            arr = _np.array([[cmap[str(c)] for c in row] for row in dom], dtype=float)
                            fig = _plt.figure()
                            _plt.imshow(arr, origin='lower', aspect='auto')
                            _plt.title('Dominant hard constraint (categorical)')
                            _plt.xlabel('y index')
                            _plt.ylabel('x index')
                            st.pyplot(fig, use_container_width=True)
                            st.caption('Legend (index -> category):')
                            st.json(cats)
                        except Exception as _e:
                            st.caption(f'Atlas plot unavailable: {_e}')
                        with st.expander('Atlas raw data (xs/ys)', expanded=False):
                            st.json({'var_x': atlas.get('var_x'), 'var_y': atlas.get('var_y'), 'xs': atlas.get('xs'), 'ys': atlas.get('ys'), 'dominant': atlas.get('dominant')})
                    elif isinstance(atlas, dict) and (not atlas.get('ok')):
                        st.warning(f"Atlas unavailable: {atlas.get('reason')}")

    # Show what the assistant last applied (so the user is never unsure).
    _lac = st.session_state.get('systems_last_applied_change')
    if isinstance(_lac, dict) and _lac.get('changes'):
        with st.expander('Last applied assistant change', expanded=False):
            st.write(_lac.get('changes'))
            if _lac.get('score') is not None:
                st.caption(f"proposal score: {float(_lac.get('score')):.3g}")
            st.caption('These changes are applied to the current Systems variables/targets/overrides.')

    if bool(st.session_state.pop('systems_just_applied', False)):
        st.success('Assistant change applied. Precheck will re-run automatically (or has just re-run).')


    # Guard against missing variables/targets due to earlier conditional branches.
    # Streamlit executes scripts top-level on each interaction; failures must degrade gracefully.
    try:
        targets  # type: ignore[name-defined]
    except NameError:
        targets = st.session_state.get('systems_targets', {}) or {}
    try:
        variables  # type: ignore[name-defined]
    except NameError:
        variables = st.session_state.get('systems_variables', {}) or {}
    try:
        do_precheck  # type: ignore[name-defined]
    except NameError:
        # Some UI branches define this checkbox earlier; ensure it's always defined
        # before it is used in the Systems solve/precheck block.
        do_precheck = bool(st.session_state.get('systems_do_precheck', True))
    try:
        do_continuation  # type: ignore[name-defined]
    except NameError:
        do_continuation = bool(st.session_state.get('systems_do_continuation', True))
    try:
        cont_steps  # type: ignore[name-defined]
    except NameError:
        try:
            cont_steps = int(st.session_state.get('systems_cont_steps', 10))
        except Exception:
            cont_steps = 10
    if not isinstance(targets, dict):
        targets = {}
    if not isinstance(variables, dict):
        variables = {}

    # v323.1: Ensure Systems has a functional default target/variable set even
    # when the user never opens the "Targets and iteration variables"expander.
    # This prevents disabled Run Precheck / Run Systems Solve buttons.
    if len(targets) == 0 and len(variables) == 0:
        # Conservative ...
        try:
            _Paux0 = float(getattr(base, 'Paux_MW', 20.0))
        except Exception:
            _Paux0 = 20.0
        targets = {'Q_DT_eqv': 10.0}
        variables = {'Paux_MW': (_Paux0, 0.0, max(200.0, 3.0*_Paux0))}
        st.session_state['systems_targets'] = dict(targets)
        st.session_state['systems_variables'] = dict(variables)

    # Persistent precheck controls (do not disappear on rerun)
    c_pre, c_solve = st.columns([1, 1])
    with c_pre:
        action = st.session_state.get("_sys_action")
        run_precheck_btn = st.button("Run precheck", use_container_width=True, disabled=(len(targets)==0 or len(variables)==0), key="v177_run_precheck_btn") or (action == "precheck")
        if run_precheck_btn and action == "precheck":
            st.session_state.pop("_sys_action", None)
    with c_solve:
        run = st.button("Run systems solve", type="primary", use_container_width=True, disabled=(len(targets)==0 or len(variables)==0), key="v177_run_systems_solve_btn")

    # If the user applied an assistant proposal, we auto-run precheck once so they immediately see the effect.
    if bool(st.session_state.pop('systems_run_precheck_now', False)):
        run_precheck_btn = True

    # Run (and persist) precheck even if the user did not click "Run systems solve".
    if run_precheck_btn and do_precheck and len(variables) > 0:
        try:
            import time as _time
            t_pre0 = _time.perf_counter()
            try:
                from evaluator.core import Evaluator
            except Exception:
                from src.evaluator.core import Evaluator  # type: ignore
            try:
                from systems.feasibility_completion import run_precheck
            except Exception:
                from src.systems.feasibility_completion import run_precheck  # type: ignore

            # Apply any Systems-mode constraint knob overrides (from assistant) before precheck
            base_for_pre = base
            st.session_state.setdefault('systems_inputs_overrides', {})
            ov = st.session_state.get('systems_inputs_overrides', {}) or {}
            if isinstance(ov, dict) and ov:
                try:
                    from dataclasses import replace as _dc_replace, fields as _dc_fields
                    _valid = {f.name for f in _dc_fields(base_for_pre)}
                    _kwargs = {k: float(v) for k, v in ov.items() if k in _valid}
                    if _kwargs:
                        base_for_pre = _dc_replace(base_for_pre, **_kwargs)
                except Exception:
                    pass

            _sys_ev_pre = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)
            _pre = run_precheck(
                base_for_pre,
                targets,
                variables,
                include_random=True,
                n_random=int(st.session_state.get('v177_precheck_n_random', 8)),
                seed=int(st.session_state.get('v177_precheck_seed', 1337)),
                evaluator=_sys_ev_pre,
                hard_constraint_names=_hard_constraint_names_for_intent(),
            )
            st.session_state['last_precheck_report'] = _pre
            st.session_state['systems_precheck_seconds'] = float(_time.perf_counter() - t_pre0)

            # If precheck is infeasible and auto-recovery is enabled, trigger
            # Seeded Feasibility Recovery once (handled in the recovery panel
            # later in this file).
            try:
                if (not bool(getattr(_pre, 'ok', False))) and bool(st.session_state.get('v178_recovery_enabled', True)) and bool(st.session_state.get('v178_recovery_auto', True)):
                    st.session_state['v178_recovery_autotrigger'] = True
            except Exception:
                pass
            try:
                _alog(
                    'Systems',
                    'RunPrecheck',
                    {
                        'ok': bool(getattr(_pre, 'ok', False)),
                        'reason': str(getattr(_pre, 'reason', '')),
                        'samples': int(getattr(_pre, 'n_samples', 0)),
                        'confidence': str(getattr(_pre, 'unreachable_targets_confidence', '')),
                        'failed_all': list(getattr(_pre, 'hard_constraints_failed_at_all_samples', []) or []),
                        'unreachable_targets': list(getattr(_pre, 'unreachable_targets', []) or []),
                        'precheck_seconds': float(getattr(_pre, 'precheck_seconds', float('nan'))),
                    },
                )
            except Exception:
                pass
        except Exception as _e:
            st.session_state['last_precheck_report'] = {'ok': False, 'reason': 'precheck_exception', 'error': str(_e)}
            _alog_exc('Systems', 'RunPrecheckException', _e)

    # Always show the latest precheck + assistant if we have a report (so Apply never "hides"it).
    _pre_last = st.session_state.get('last_precheck_report', None)
    if _pre_last is not None:
        try:
            _ok = bool(getattr(_pre_last, 'ok', _pre_last.get('ok', False) if isinstance(_pre_last, dict) else False))
        except Exception:
            _ok = False
        if _ok:
            st.success('Precheck: feasible within declared bounds (sampled).')
        else:
            if _design_intent_key() == 'reactor':
                st.error('Precheck: infeasible within declared bounds (sampled evaluation). Use the assistant below to apply minimal changes.')
            else:
                # v178.6: intent-aware messaging (avoid claiming we're using reactor hard set in research intent).
                _hs = sorted(list(_hard_constraint_names_for_intent()))
                st.warning('Precheck: infeasible under current hard-constraint set ' + (f"({', '.join(_hs)})"if _hs else '') + '. In **Experimental Device** intent, this does not block exploration; you can still run solves to study the machine.')
        if _sys_show('Diagnose','Recover','Advanced'):
            with st.expander('Precheck report (detailed)', expanded=False):
                view_mode = st.radio("View", options=["Summary", "Detailed"], index=0, horizontal=True, key="systems_precheck_view_mode")

                st.caption(f"Report type: {type(_pre_last).__name__}")
                st.caption('If this panel ever looks empty, the raw report is shown at the bottom for debugging.')
                # Summary view (default): compact, readable.
                try:
                    n_samp = int(getattr(_pre_last, 'n_samples', _pre_last.get('n_samples', 0)))
                    conf = str(getattr(_pre_last, 'unreachable_targets_confidence', _pre_last.get('unreachable_targets_confidence', '')))
                    failed = list(getattr(_pre_last, 'hard_constraints_failed_at_all_samples', _pre_last.get('hard_constraints_failed_at_all_samples', [])))
                    st.write(f"Samples: **{n_samp}**"+ (f"| Unreachable confidence: **{conf}**"if conf else ""))
                    if failed:
                        st.warning("Failed at all samples: "+ ", ".join(map(str, failed)))
                    else:
                        st.success("No hard constraint failed at all samples.")
                except Exception:
                    pass

                if view_mode == "Detailed":

                    try:
                        n_samp = int(getattr(_pre_last, 'n_samples', _pre_last.get('n_samples', 0)))
                        conf = str(getattr(_pre_last, 'unreachable_targets_confidence', _pre_last.get('unreachable_targets_confidence', '')))
                        st.write(f"Samples evaluated: **{n_samp}**")
                        if conf:
                            st.write(f"Unreachable targets confidence: **{conf}**")
                    except Exception:
                        pass
                    try:
                        failed = list(getattr(_pre_last, 'hard_constraints_failed_at_all_samples', _pre_last.get('hard_constraints_failed_at_all_samples', [])))
                        bestm = getattr(_pre_last, 'hard_constraints_best_margin', _pre_last.get('hard_constraints_best_margin', {})) or {}
                        bests = getattr(_pre_last, 'hard_constraints_best_sample', _pre_last.get('hard_constraints_best_sample', {})) or {}
                        if failed:
                            st.markdown('**Hard constraints failed at all samples**')

                            # Minimal-change recommender (qualitative) (COULD but very useful)
                            try:
                                _recs = []
                                for nm in list((_pre.hard_constraints_failed_at_all_samples or []) if hasattr(_pre,'hard_constraints_failed_at_all_samples') else (failed or [])):
                                    nml = str(nm).lower()
                                    if 'q_div' in nml:
                                        _recs.append(('q_div', 'Increase R0 / major radius, increase λq / broaden SOL, reduce P_SOL, or relax q_div_max (Research only).'))
                                    elif 'sigma' in nml or 'stress' in nml:
                                        _recs.append(('sigma_vm', 'Increase structural allowance / coil build, reduce B_peak/currents, increase R0, or relax sigma_allow (Research only).'))
                                    elif 'hts' in nml or 'margin' in nml:
                                        _recs.append(('HTS margin', 'Reduce peak field/current density, increase coil build, increase operating margin, or relax hts_margin_min (Research only).'))
                                    elif 'tbr' in nml:
                                        _recs.append(('TBR', 'Increase blanket effectiveness (if modeled), increase R0, reduce penetrations, or relax TBR_min (Research only).'))
                                    else:
                                        _recs.append((str(nm), 'Adjust bounds on sensitive variables or relax this constraint in Research intent (diagnostic).'))
                                if _recs:
                                    st.markdown('**What usually helps (qualitative)**')
                                    for k, msg in _recs[:8]:
                                        st.write(f'- **{k}**: {msg}')
                            except Exception:
                                pass

                            ranked = sorted([(nm, float(bestm.get(nm, float('nan'))), str(bests.get(nm, ''))) for nm in failed], key=lambda t: (t[1] if t[1]==t[1] else -1e9), reverse=True)
                            for nm, bm, sn in ranked:
                                st.write(f"- **{nm}**: best margin {bm:.3g} at sample `{sn}`")
                        else:
                            # v178.9: avoid an empty detailed report when precheck is feasible.
                            st.caption('No hard constraints failed at all samples.')
                            # Still show best-margin dictionary if available (useful for "how feasible?"diagnostics).
                            if isinstance(bestm, dict) and bestm:
                                st.caption('Best hard-constraint margins across samples:')
                                # Keep it compact; Streamlit will allow expand/copy.
                                st.json(bestm)
                    except Exception:
                        pass

                    # Show unreachable targets (if any) even when feasible.
                    try:
                        unreachable = list(getattr(_pre_last, 'unreachable_targets', _pre_last.get('unreachable_targets', [])) or [])
                        if unreachable:
                            st.markdown('**Targets outside sampled reachable range**')
                            for u in unreachable:
                                tgt_name = str(u.get('target'))
                                st.write(f"- **{tgt_name}**: requested {u.get('target_value')} vs sampled range [{u.get('sample_min')}, {u.get('sample_max')}]")
                        else:
                            st.caption('No unreachable targets detected in sampled range.')
                    except Exception:
                        pass
                    # Always show the raw report (guarantees non-empty UI)
                    try:
                        if hasattr(_pre_last, '__dict__'):
                            st.markdown('**Raw precheck report (debug)**')
                            st.json(dict(_pre_last.__dict__))
                        elif isinstance(_pre_last, dict):
                            st.markdown('**Raw precheck report (debug)**')
                            st.json(_pre_last)
                    except Exception as _e:
                        st.caption(f'Raw report unavailable: {_e}')


            # Only show the assistant when infeasible
            if not _ok:
                if _sys_show('Diagnose','Recover','Advanced'):
                    with st.expander('Feasibility completion assistant (guided minimal changes)', expanded=False):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.number_input('Random samples (precheck)', min_value=0, max_value=64, value=int(st.session_state.get('v177_precheck_n_random', 8)), step=1, key='v177_precheck_n_random')
                        with c2:
                            st.number_input('Deterministic seed', min_value=0, max_value=999999, value=int(st.session_state.get('v177_precheck_seed', 1337)), step=1, key='v177_precheck_seed')
                        with c3:
                            st.caption('Proposals are deterministic for a fixed seed and bounds.')

                        try:
                            try:
                                from systems.feasibility_completion import propose_feasibility_completion
                            except Exception:
                                from src.systems.feasibility_completion import propose_feasibility_completion  # type: ignore
                            try:
                                from evaluator.core import Evaluator
                            except Exception:
                                from src.evaluator.core import Evaluator  # type: ignore

                            # Apply overrides before proposing
                            base_for_props = base
                            try:
                                ov = st.session_state.get('systems_inputs_overrides', {})
                                if isinstance(ov, dict) and ov:
                                    d0 = dict(base_for_props.__dict__)
                                    d0.update({k: float(v) for k, v in ov.items()})
                                    base_for_props = PointInputs(**d0)
                            except Exception:
                                pass

                            _ev_props = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)
                            props = propose_feasibility_completion(
                                base_for_props,
                                targets,
                                variables,
                                evaluator=_ev_props,
                                include_random=True,
                                n_random=int(st.session_state.get('v177_precheck_n_random', 8)),
                                seed=int(st.session_state.get('v177_precheck_seed', 1337)),
                                max_k_changes=2,
                                hard_constraint_names=_hard_constraint_names_for_intent(),
                            )
                        except Exception as _e:
                            props = []
                            st.caption(f"Proposal generation failed: {_e}")

                        st.session_state.setdefault('systems_undo_stack', [])
                        st.session_state.setdefault('systems_inputs_overrides', {})
                        st.session_state.setdefault('systems_bounds_overrides', {})
                        st.session_state.setdefault('systems_targets_overrides', {})

                        # NOTE: We also persist initial-guess overrides (x0) using the same
                        # systems_bounds_overrides structure: {var: {x0, lo, hi}}.

                        def _push_undo():
                            st.session_state['systems_undo_stack'].append({
                                'variables': dict(variables),
                                'targets': dict(targets),
                                'inputs_overrides': dict(st.session_state.get('systems_inputs_overrides', {})),
                                'bounds_overrides': dict(st.session_state.get('systems_bounds_overrides', {})),
                                'targets_overrides': dict(st.session_state.get('systems_targets_overrides', {})),
                            })

                        def _apply_prop(p):
                            ch = p.get('changes') or {}
                            if 'bounds' in ch:
                                bo = st.session_state.get('systems_bounds_overrides', {}) or {}
                                for vk, bc in (ch.get('bounds') or {}).items():
                                    if not isinstance(bc, dict):
                                        continue
                                    if vk in variables:
                                        x0, lo, hi = variables[vk]
                                        lo2 = float(bc.get('lo', lo))
                                        hi2 = float(bc.get('hi', hi))
                                        x02 = float(bc.get('x0', x0))
                                        variables[vk] = (x02, lo2, hi2)
                                    bo[vk] = {k: float(v) for k, v in bc.items() if v is not None}
                                st.session_state['systems_bounds_overrides'] = bo
                            if 'targets' in ch:
                                to = st.session_state.get('systems_targets_overrides', {}) or {}
                                for tk, tv in (ch.get('targets') or {}).items():
                                    if tk in targets:
                                        targets[tk] = float(tv)
                                    to[tk] = float(tv)
                                st.session_state['systems_targets_overrides'] = to
                            if 'constraints' in ch:
                                ov = st.session_state.get('systems_inputs_overrides', {}) or {}
                                for kk, vv in (ch.get('constraints') or {}).items():
                                    ov[kk] = float(vv)
                                st.session_state['systems_inputs_overrides'] = ov

                        if st.button('Undo last assistant change', use_container_width=True, disabled=(len(st.session_state['systems_undo_stack'])==0), key='v177_undo_assistant'):
                            last_u = st.session_state['systems_undo_stack'].pop()
                            try:
                                variables.clear(); variables.update(last_u.get('variables') or {})
                                targets.clear(); targets.update(last_u.get('targets') or {})
                                st.session_state['systems_inputs_overrides'] = dict(last_u.get('inputs_overrides') or {})
                                st.session_state['systems_bounds_overrides'] = dict(last_u.get('bounds_overrides') or {})
                                st.session_state['systems_targets_overrides'] = dict(last_u.get('targets_overrides') or {})
                                st.success('Undo applied. Precheck will re-run.')
                                st.session_state['systems_run_precheck_now'] = True
                                st.rerun()
                            except Exception:
                                st.warning('Undo failed (unexpected state).')

                        st.markdown('**Suggested minimal changes**')
                        if not props:
                            st.info('No proposals available. Consider expanding bounds for R0/Bt or relaxing constraints explicitly.')
                        else:
                            for i, pr in enumerate(props, start=1):
                                cols = st.columns([4,1])
                                with cols[0]:
                                    st.write(f"{i}. **{pr.description}** _(type: {pr.kind})_")
                                    st.caption(f"score: {float(pr.score):.3g}")
                                with cols[1]:
                                    if st.button('Apply', key=f'v177_apply_prop_persist_{i}', use_container_width=True):
                                        _push_undo()
                                        _apply_prop({'changes': pr.changes})
                                        st.session_state['systems_last_applied_change'] = {
                                            'changes': pr.changes,
                                            'score': float(pr.score) if hasattr(pr, 'score') else None,
                                        }
                                        st.session_state['systems_just_applied'] = True
                                        _alog('Systems', 'ApplyProposal', {'changes': pr.changes, 'score': float(pr.score) if hasattr(pr,'score') else None})
                                        st.session_state['systems_run_precheck_now'] = True
                                        st.success('Applied. Re-running precheck…')
                                        st.rerun()

                        with st.expander('Constraint knob overrides (Systems Mode)', expanded=False):
                            ov = st.session_state.get('systems_inputs_overrides', {})
                            if ov:
                                st.json(ov)
                                if st.button('Clear constraint overrides', key='v177_clear_overrides_persist', use_container_width=True):
                                    st.session_state['systems_inputs_overrides'] = {}
                                    st.session_state['systems_run_precheck_now'] = True
                                    st.success('Cleared. Re-running precheck…')
                                    st.rerun()
                            else:
                                st.caption('No overrides applied.')

                # -----------------------------------------------------------------
                # Seeded Feasibility Recovery
            #
            # Finds a hard-constraint-feasible point close to a user seed, and
            # can apply it as the initial guess (x0) for Systems solve.
            #
            # This is NOT an optimizer: feasibility is the primary objective,
            # closeness-to-seed is the secondary objective.
            # -----------------------------------------------------------------
        if _sys_show('Recover','Advanced'):
            with st.expander('Seeded Feasibility Recovery (find feasible machine near your seed)', expanded=False):
                st.caption('If your guessed starting point is far from reality, SHAMS can search for a **nearby feasible machine** within the declared bounds. The recovered point can be applied as the Systems initial guess (x0).')

                rec_enabled = st.toggle(
                    'Enable seeded recovery',
                    value=bool(st.session_state.get('v178_recovery_enabled', True)),
                    key='v178_recovery_enabled',
                )
                if not rec_enabled:
                    st.info('Seeded recovery is disabled.')
                else:
                    cA, cB, cC, cD = st.columns(4)
                    with cA:
                        st.number_input('Recovery eval budget', min_value=30, max_value=2000, value=int(st.session_state.get('v178_recovery_budget', 250)), step=10, key='v178_recovery_budget')
                    with cB:
                        st.number_input('Local steps', min_value=10, max_value=400, value=int(st.session_state.get('v178_recovery_local_steps', 80)), step=5, key='v178_recovery_local_steps')
                    with cC:
                        st.number_input('Multi-start samples', min_value=0, max_value=400, value=int(st.session_state.get('v178_recovery_multistart', 40)), step=5, key='v178_recovery_multistart')
                    with cD:
                        st.number_input('Deterministic seed', min_value=0, max_value=999999, value=int(st.session_state.get('v178_recovery_seed', 2026)), step=1, key='v178_recovery_seed')
                    st.number_input('Multi-seed runs (N)', min_value=1, max_value=20, value=int(st.session_state.get('v179_rec_multiseed_n', 1)), step=1, key='v179_rec_multiseed_n', help='Runs recovery multiple times with different deterministic seeds and keeps the best result.')

                    st.toggle(
                        'Auto-run recovery after infeasible precheck',
                        value=bool(st.session_state.get('v178_recovery_auto', True)),
                        key='v178_recovery_auto',
                        help='When enabled, after a precheck reports infeasible, recovery runs automatically so you immediately get a candidate starting point.',
                    )

                    seed_mode = st.radio(
                        'Seed source',
                        ['Midpoint of bounds', 'Last Point Designer result', 'Manual (edit variables)'],
                        index=int(st.session_state.get('v178_recovery_seed_mode_idx', 0)),
                        key='v178_recovery_seed_mode',
                        horizontal=True,
                    )
                    try:
                        st.session_state['v178_recovery_seed_mode_idx'] = ['Midpoint of bounds', 'Last Point Designer result', 'Manual (edit variables)'].index(seed_mode)
                    except Exception:
                        pass

                    # -----------------------------
                    # A) Recovery variables (separate from solver iteration variables)
                    # -----------------------------
                    st.session_state.setdefault('v178_recovery_basevars_enabled', False)
                    basevars_enabled = st.checkbox(
                        'Allow recovery to adjust Base design variables (explicit bounds)',
                        value=bool(st.session_state.get('v178_recovery_basevars_enabled', False)),
                        key='v178_recovery_basevars_enabled',
                        help='This does NOT change the solver iteration-variable list. It only enables the feasibility-recovery search to move Base-design fields within explicit bounds.',
                    )

                    # Candidate base vars (PointInputs field names)
                    _BASE_VAR_MAP = [
                        ('R0_m', 'R0 [m]'),
                        ('a_m', 'a [m]'),
                        ('kappa', 'κ [-]'),
                        ('delta', 'δ [-]'),
                        ('Bt_T', 'Bt [T]'),
                        ('Ti_keV', 'Ti [keV]'),
                        ('Ti_over_Te', 'Ti/Te [-]'),
                        ('t_shield_m', 'Shield thickness [m]'),
                    ]
                    _base_labels_by_key = {k: lab for k, lab in _BASE_VAR_MAP}

                    selected_base_vars: List[str] = []
                    if basevars_enabled:
                        selected_base_vars = st.multiselect(
                            'Base design variables to include in recovery',
                            options=[k for k, _ in _BASE_VAR_MAP],
                            default=list(st.session_state.get('v178_recovery_basevars', []) or []),
                            format_func=lambda k: _base_labels_by_key.get(k, k),
                            key='v178_recovery_basevars',
                        )
                        st.caption('For each selected Base variable, set explicit recovery bounds. This keeps SHAMS feasibility-authoritative and auditable.')

                    # Build recovery bounds dict (solved iteration variables + optional base vars)
                    bounds_rec: Dict[str, Dict[str, float]] = {k: {'lo': float(lo), 'hi': float(hi)} for k, (_x0, lo, hi) in list(variables.items())}

                    # Base-design bounds UI (defaults: ±20% around current base value, clamped)
                    st.session_state.setdefault('v178_recovery_base_bounds', {})
                    _bb = st.session_state.get('v178_recovery_base_bounds', {}) or {}
                    if basevars_enabled and selected_base_vars:
                        with st.expander('Base-variable recovery bounds', expanded=False):
                            for _k in selected_base_vars:
                                try:
                                    _v0 = float(getattr(base, _k))
                                except Exception:
                                    continue
                                # Near-zero variables (notably delta) need an absolute bound span.
                                # Percent-based spans collapse to ~0 and make the variable unusable.
                                if _k == 'delta' and abs(_v0) < 1e-6:
                                    _span = 0.5
                                    _dlo = 0.0
                                    _dhi = 0.5
                                else:
                                    _span = max(1e-9, abs(_v0))
                                    _dlo = max(0.0, _v0 - 0.20 * _span)
                                    _dhi = _v0 + 0.20 * _span
                                _stored = _bb.get(_k, {}) if isinstance(_bb, dict) else {}
                                _lo_key = f'v178_rec_bound_lo_{_k}'
                                _hi_key = f'v178_rec_bound_hi_{_k}'
                                c1, c2, c3 = st.columns([2, 2, 1])
                                with c1:
                                    _lo = st.number_input(
                                        f"{_base_labels_by_key.get(_k, _k)} lo",
                                        value=float(_stored.get('lo', _dlo)),
                                        step=float(max(1e-6, 0.01 * _span)),
                                        key=_lo_key,
                                    )
                                with c2:
                                    _hi = st.number_input(
                                        f"{_base_labels_by_key.get(_k, _k)} hi",
                                        value=float(_stored.get('hi', _dhi)),
                                        step=float(max(1e-6, 0.01 * _span)),
                                        key=_hi_key,
                                    )
                                with c3:
                                    _pin = st.checkbox('Pin', value=bool(_stored.get('pin', False)), key=f'v178_rec_pin_{_k}', help='If pinned, recovery keeps this variable closer to the seed (higher distance weight).')
                                _lo2 = float(min(_lo, _hi))
                                _hi2 = float(max(_lo, _hi))
                                bounds_rec[_k] = {'lo': _lo2, 'hi': _hi2}
                                _bb[_k] = {'lo': _lo2, 'hi': _hi2, 'pin': bool(_pin)}
                        st.session_state['v178_recovery_base_bounds'] = _bb

                    # -----------------------------
                    # Seed dict (for recovery variables)
                    # -----------------------------
                    seed_dict: Dict[str, float] = {}
                    if seed_mode == 'Last Point Designer result':
                        try:
                            _lp = getattr(s, 'last_point_result', None)
                            _outs = None
                            if isinstance(_lp, dict):
                                _outs = _lp.get('outputs')
                            if not isinstance(_outs, dict):
                                _outs = getattr(s, 'last_point_outputs', None)
                            if isinstance(_outs, dict):
                                for _vn in list(bounds_rec.keys()):
                                    if _vn in _outs and _outs[_vn] is not None:
                                        try:
                                            seed_dict[_vn] = float(_outs[_vn])
                                        except Exception:
                                            pass
                        except Exception:
                            pass
                        if not seed_dict:
                            st.caption('No prior Point Designer outputs found for recovery variables; defaulting to midpoint/base.')

                    # For base vars, the natural seed is the current Base design
                    for _k in selected_base_vars:
                        try:
                            seed_dict.setdefault(_k, float(getattr(base, _k)))
                        except Exception:
                            pass

                    if seed_mode == 'Manual (edit variables)':
                        st.caption('Edit the seed values for all recovery variables. Values are clamped to bounds.')
                        with st.expander('Manual seed editor', expanded=False):
                            for _vn, _b in list(bounds_rec.items()):
                                try:
                                    _lo = float(_b.get('lo'))
                                    _hi = float(_b.get('hi'))
                                    if not (math.isfinite(_lo) and math.isfinite(_hi)):
                                        continue
                                except Exception:
                                    continue
                                _key = f'v178_seed_{_vn}'
                                _default = float(st.session_state.get(_key, seed_dict.get(_vn, (_lo + _hi) / 2.0)))
                                st.number_input(
                                    f"Seed {_base_labels_by_key.get(_vn, _vn)}",
                                    min_value=float(_lo),
                                    max_value=float(_hi),
                                    value=float(_default),
                                    step=(float(_hi) - float(_lo)) / 100.0 if float(_hi) > float(_lo) else 0.1,
                                    key=_key,
                                )
                                try:
                                    seed_dict[_vn] = float(st.session_state.get(_key, _default))
                                except Exception:
                                    pass

                    # Distance weights (pins)
                    weights_rec: Dict[str, float] = {}
                    try:
                        for _k, _v in (_bb or {}).items():
                            if isinstance(_v, dict) and bool(_v.get('pin')):
                                weights_rec[_k] = 10.0
                    except Exception:
                        pass

                    # Helper to run recovery
                    def _run_seeded_recovery() -> None:
                        try:
                            from evaluator.core import Evaluator
                        except Exception:
                            from src.evaluator.core import Evaluator  # type: ignore
                        try:
                            from systems.recovery import recover_feasible_near_seed
                        except Exception:
                            from src.systems.recovery import recover_feasible_near_seed  # type: ignore

                        # Apply constraint knob overrides to base inputs
                        base_rec = base
                        try:
                            ov = st.session_state.get('systems_inputs_overrides', {}) or {}
                            if isinstance(ov, dict) and ov:
                                from dataclasses import replace as _dc_replace, fields as _dc_fields
                                _valid = {f.name for f in _dc_fields(base_rec)}
                                _kwargs = {k: float(v) for k, v in ov.items() if k in _valid}
                                if _kwargs:
                                    base_rec = _dc_replace(base_rec, **_kwargs)
                        except Exception:
                            pass

                        # Build bounds dict for recovery (solved vars + optional base vars)
                        _bounds_rec = {k: {'lo': float(v.get('lo')), 'hi': float(v.get('hi'))} for k, v in (bounds_rec or {}).items()}
                        _weights_rec = weights_rec if isinstance(weights_rec, dict) else None
                        ev = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)
                        # Safety rails (MUST): validate bounds before running.
                        _okb, _errs, _warns = _sys_validate_bounds(_bounds_rec)
                        for _w in _warns:
                            try:
                                _alog('Systems', 'BoundsWarning', {'msg': _w})
                            except Exception:
                                pass
                        if not _okb:
                            st.error('Invalid recovery bounds:\n- ' + '\n- '.join(_errs))
                            return

                        rep = None
                        _nms = int(st.session_state.get('v179_rec_multiseed_n', 1))
                        _base_seed = int(st.session_state.get('v178_recovery_seed', 2026))
                        _reps = []
                        _best = None
                        _best_key = None
                        for _j in range(max(1, _nms)):
                            _seedj = _base_seed + int(_j)
                            _r = recover_feasible_near_seed(
                                base=base_rec,
                                variables=_bounds_rec,
                                evaluator=ev,
                                seed=seed_dict if seed_dict else None,
                                weights=_weights_rec,
                                rng_seed=int(_seedj),
                                budget_evals=int(st.session_state.get('v178_recovery_budget', 250)),
                                local_steps=int(st.session_state.get('v178_recovery_local_steps', 80)),
                                multi_start=int(st.session_state.get('v178_recovery_multistart', 40)),
                                hard_constraint_names=_hard_constraint_names_for_intent(),
                                return_trace=True,
                                trace_keep=2500,
                            )
                            try:
                                _r['rng_seed_used'] = int(_seedj)
                            except Exception:
                                pass
                            _reps.append(_r)
                            try:
                                _ok = bool(_r.get('ok'))
                                _d = float(_r.get('best_distance', 1e9))
                                _v = float(_r.get('best_V', 1e9))
                            except Exception:
                                _ok, _d, _v = False, 1e9, 1e9
                            _key = (0 if _ok else 1, _d if _ok else 0.0, _v)
                            if _best is None or _key < _best_key:
                                _best, _best_key = _r, _key
                        rep = _best or (_reps[0] if _reps else {'ok': False, 'reason': 'no_result'})
                        try:
                            rep['multi_seed_runs'] = int(_nms)
                            rep['all_runs'] = _reps
                        except Exception:
                            pass
                        # Merge traces with a seed tag (for timeline/frontier). Keep bounded.
                        try:
                            _mtr = []
                            for _rr in _reps:
                                for _t in (_rr.get('trace') or []):
                                    _tt = dict(_t)
                                    _tt['seed'] = _rr.get('rng_seed_used')
                                    _mtr.append(_tt)
                            rep['trace'] = _mtr[-2500:]
                        except Exception:
                            pass
                        if isinstance(rep, dict):
                            rep.setdefault('schema_version', 1)
                        st.session_state['v178_last_recovery'] = rep
                        # Run card (MUST)
                        try:
                            bm = dict(rep.get('best_margins', {}) or {})
                            dom = None
                            if bm:
                                dom = sorted([(k, float(v)) for k, v in bm.items() if isinstance(v, (int, float)) and math.isfinite(float(v))], key=lambda t: t[1])[0][0]
                            outc = {
                                'status': 'ok' if bool(rep.get('ok')) else 'fail',
                                'reason': str(rep.get('reason')),
                                'dominant_limiter': dom,
                                'limiters': list((rep.get('best_nan') or []) and ['numerics'] or ([] if bool(rep.get('ok')) else list((rep.get('best_violations') or {}).keys())[:3])),
                                'next': _sys_failure_taxonomy(str(rep.get('reason'))).get('next', []) + _sys_levers_from_limiters([dom] if dom else []),
                            }
                            _sys_append_run_card(kind='SeededRecovery', settings={'intent': st.session_state.get('design_intent',''), 'vars': list(_bounds_rec.keys()), 'budget': int(st.session_state.get('v178_recovery_budget', 250))}, outcome=outc)
                        except Exception:
                            pass
                        try:
                            _alog('Systems', 'SeededRecovery', {
                                'ok': bool(rep.get('ok')),
                                'reason': str(rep.get('reason')),
                                'evals': int(rep.get('evals', 0)),
                                'best_V': float(rep.get('best_V', float('nan'))),
                                'best_distance': float(rep.get('best_distance', float('nan'))),
                                'best_margins': dict(rep.get('best_margins', {}) or {}),
                                'best_nan': list(rep.get('best_nan', []) or []),
                                'recovery_vars': list(_bounds_rec.keys()),
                                'recovery_bounds': _bounds_rec,
                                'weights': _weights_rec or {},
                            })
                        except Exception:
                            pass

                    # Auto-run recovery when the latest precheck is infeasible
                    try:
                        _pre_last = st.session_state.get('last_precheck_report', None)
                        _pre_ok = bool(getattr(_pre_last, 'ok', _pre_last.get('ok', False) if isinstance(_pre_last, dict) else False))
                    except Exception:
                        _pre_ok = False
                    if (not _pre_ok) and bool(st.session_state.get('v178_recovery_auto', True)) and bool(st.session_state.pop('v178_recovery_autotrigger', False)):
                        _run_seeded_recovery()

                    action = st.session_state.get('_sys_action')
                    if st.button('Run seeded recovery now', use_container_width=True, key='v178_run_recovery_btn') or (action == 'recovery'):
                        st.session_state.pop('_sys_action', None) if action == 'recovery' else None
                        _run_seeded_recovery()

                    rep = st.session_state.get('v178_last_recovery')
                    if isinstance(rep, dict) and rep:
                        if bool(rep.get('ok')):
                            st.success(f"Recovered feasible point found ({rep.get('reason')}).")
                        else:
                            st.warning(f"No feasible point found within bounds (best effort). Reason: {rep.get('reason')}")

                        with st.expander('Recovery report (details)', expanded=False):
                            st.write({'evals': rep.get('evals'), 'best_V': rep.get('best_V'), 'best_distance': rep.get('best_distance')})
                            bm = rep.get('best_margins', {}) or {}
                            if bm:
                                st.caption('Hard-constraint margins at recovered best point:')
                                st.json(bm)
                            bp = rep.get('best_point', {}) or {}
                            sp = rep.get('seed_point', {}) or {}
                            if bp:
                                deltas = {k: float(bp.get(k, float('nan'))) - float(sp.get(k, float('nan'))) for k in bp.keys()}
                                st.caption('Δ from seed (best - seed) for recovery variables:')
                                st.json(deltas)

                            _nan = rep.get('best_nan', []) or []
                            if isinstance(_nan, list) and _nan:
                                st.caption('NaN diagnostics (numerically invalid hard constraints at the best recovered point):')
                                st.json(_nan)

                        # SHOULD/COULD: comparison + economics + narrative (recovered best point)
                        try:
                            _bp = rep.get('best_point', {}) or {}
                            if isinstance(_bp, dict) and _bp:
                                with st.expander('Recovered point vs Base (delta) / Economics / Narrative', expanded=False):
                                    # Base reference
                                    try:
                                        from dataclasses import asdict as _dc_asdict
                                        _base_ref = _dc_asdict(base)
                                    except Exception:
                                        _base_ref = dict(getattr(base, '__dict__', {}) or {})

                                    rows = []
                                    for k, v in sorted(_bp.items()):
                                        try:
                                            fv = float(v)
                                        except Exception:
                                            continue
                                        row = {'var': str(k), 'value': fv}
                                        if k in _base_ref and _base_ref.get(k) is not None:
                                            try:
                                                row['base'] = float(_base_ref.get(k))
                                                row['Δ'] = fv - float(_base_ref.get(k))
                                            except Exception:
                                                pass
                                        rows.append(row)
                                    if rows:
                                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                                    # Economics proxy (diagnostic)
                                    try:
                                        R0v = float(_bp.get('R0_m', _base_ref.get('R0_m', float('nan'))))
                                        av = float(_bp.get('a_m', _base_ref.get('a_m', float('nan'))))
                                        Bv = float(_bp.get('Bt_T', _base_ref.get('Bt_T', float('nan'))))
                                        st.caption('Economics proxy (diagnostic only):')
                                        st.write({'cost_proxy': (R0v**2) * max(0.1, av) * (Bv**2)})
                                    except Exception:
                                        pass

                                    # Narrative summary (COULD)
                                    if st.checkbox('Generate narrative summary (auto)', value=False, key='sys_rec_narr_toggle'):
                                        try:
                                            diffs = []
                                            for k in ['R0_m','a_m','kappa','delta','Bt_T','Ti_keV','Ti_over_Te','t_shield_m','Paux_MW']:
                                                if k in _bp and k in _base_ref and _base_ref[k] is not None:
                                                    dv = float(_bp[k]) - float(_base_ref[k])
                                                    if abs(dv) > 1e-9:
                                                        diffs.append(f"{k}: {float(_base_ref[k]):.3g} → {float(_bp[k]):.3g} (Δ{dv:+.3g})")
                                            bm = rep.get('best_margins', {}) or {}
                                            dom = None
                                            try:
                                                mlist = [(kk, float(vv)) for kk, vv in bm.items() if isinstance(vv, (int, float)) and math.isfinite(float(vv))]
                                                if mlist:
                                                    dom = sorted(mlist, key=lambda t: t[1])[0]
                                            except Exception:
                                                dom = None
                                            st.markdown('**Auto summary**')
                                            st.write(
                                                f"Recovered point is {'feasible' if bool(rep.get('ok')) else 'best-effort'} under intent. "
                                                + (f"Dominant limiter (tightest margin): `{dom[0]}` (margin={dom[1]:.3g}). "if dom else "")
                                            )
                                            if diffs:
                                                st.write('Key changes vs Base:')
                                                st.write('\n'.join([f"- {d}"for d in diffs]))
                                        except Exception as _e:
                                            st.warning(f'Narrative failed: {_e}')
                        except Exception:
                            pass

                        if bool(rep.get('ok')) and isinstance(rep.get('best_point'), dict):
                            _bp = rep.get('best_point') or {}

                            # Apply recovered Base-design values (explicit user action)
                            if basevars_enabled and selected_base_vars:
                                if st.button('Apply recovered Base design values', use_container_width=True, key='v178_apply_recovered_base'):
                                    try:
                                        bo2 = st.session_state.get('systems_base_overrides', {}) or {}
                                        applied = {}
                                        for _k in selected_base_vars:
                                            if _k in _bp:
                                                try:
                                                    _v = float(_bp.get(_k))
                                                    bo2[_k] = _v
                                                    applied[_k] = _v
                                                except Exception:
                                                    pass
                                        st.session_state['systems_base_overrides'] = bo2
                                        # Stage the widget-key updates to the next rerun (before widgets are created).
                                        # This avoids StreamlitAPIException.
                                        st.session_state['systems_pending_base_apply'] = dict(applied)
                                        st.session_state['systems_pending_base_apply_source'] = 'SeededRecoveryApplyBase'
                                        st.session_state['systems_last_applied_change'] = {'changes': {'base': applied}, 'score': None}
                                        st.session_state['systems_just_applied'] = True
                                        try:
                                            _alog('Systems', 'ApplyRecoveredBase', {'base': applied})
                                        except Exception:
                                            pass
                                        st.session_state['systems_run_precheck_now'] = True
                                        st.success('Applied recovered Base design values. Re-running precheck…')
                                        st.rerun()
                                    except Exception:
                                        st.error('Failed to apply recovered Base design values (unexpected error).')

                            if st.button('Apply recovered point as Systems initial guess (x0)', use_container_width=True, key='v178_apply_recovered_x0'):
                                # Persist x0 into systems_bounds_overrides
                                bo = st.session_state.get('systems_bounds_overrides', {}) or {}
                                for _vn, (_x0, _lo, _hi) in list(variables.items()):
                                    try:
                                        _x = float(_bp.get(_vn, _x0))
                                        bo[_vn] = {
                                            'x0': max(float(_lo), min(float(_hi), _x)),
                                            'lo': float(_lo),
                                            'hi': float(_hi),
                                        }
                                    except Exception:
                                        pass
                                st.session_state['systems_bounds_overrides'] = bo
                                st.session_state['systems_last_applied_change'] = {
                                    'changes': {'x0': _bp},
                                    'score': None,
                                }
                                st.session_state['systems_just_applied'] = True
                                try:
                                    _alog('Systems', 'ApplyRecoveredX0', {'x0': _bp})
                                except Exception:
                                    pass
                                st.session_state['systems_run_precheck_now'] = True
                                st.success('Applied recovered x0. Re-running precheck…')
                                st.rerun()

    # -----------------------------------------------------------------
    # Feasible Design Search (Systems + Optimization)
    # -----------------------------------------------------------------
    if _sys_show('Explore','Advanced'):
        with st.expander('Feasible Design Search (Systems + Optimization)', expanded=False):
            st.caption('Feasible-only search: hard constraints must pass; then we optimize an engineering objective among feasible machines.')

            src_opts = ['Last feasible from Seeded Recovery', 'Last Systems solution (if any)', 'Manual (current Base + midpoints)']
            src = st.radio('Starting point source', src_opts, index=int(st.session_state.get('v178_fs_src_idx', 0)), horizontal=True, key='v178_fs_src')
            try:
                st.session_state['v178_fs_src_idx'] = src_opts.index(src)
            except Exception:
                pass

            obj_opts = [
                ('q_div_MW_m2', 'Minimize divertor q_div'),
                ('P_SOL_over_R_MW_m', 'Minimize P_SOL/R'),
                ('neutron_wall_load_MW_m2', 'Minimize NWL'),
                ('sigma_vm_MPa', 'Minimize stress sigma_vm'),
                ('B_peak_T', 'Minimize B_peak'),
                ('-TBR', 'Maximize TBR'),
                ('-hts_margin', 'Maximize HTS margin'),
            ]
            obj_key = st.selectbox('Objective', options=[k for k,_ in obj_opts], index=int(st.session_state.get('v178_fs_obj_idx', 0)), format_func=lambda k: dict(obj_opts).get(k,k), key='v178_fs_obj')
            try:
                st.session_state['v178_fs_obj_idx'] = [k for k,_ in obj_opts].index(obj_key)
            except Exception:
                pass

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.number_input('Search eval budget', min_value=50, max_value=5000, value=int(st.session_state.get('v178_fs_budget', 800)), step=50, key='v178_fs_budget')
            with c2:
                st.number_input('Top-K candidates', min_value=1, max_value=50, value=int(st.session_state.get('v178_fs_topk', 12)), step=1, key='v178_fs_topk')
            with c3:
                st.number_input('Deterministic seed', min_value=0, max_value=999999, value=int(st.session_state.get('v178_fs_seed', 2026)), step=1, key='v178_fs_seed')
            st.number_input('Multi-seed runs (N)', min_value=1, max_value=20, value=int(st.session_state.get('v179_fs_multiseed_n', 1)), step=1, key='v179_fs_multiseed_n', help='Runs feasible search multiple times with different deterministic seeds and merges the Top-K candidates.')
            with c4:
                st.number_input('Local radius (fraction of bound span)', min_value=0.01, max_value=1.0, value=float(st.session_state.get('v178_fs_radius', 0.25)), step=0.01, key='v178_fs_radius')

            # Default bounds from solver variable bounds + recovery base bounds (if any)
            bounds_default = {}
            try:
                for k, (_x0, lo, hi) in list(variables.items()):
                    bounds_default[k] = {'lo': float(lo), 'hi': float(hi)}
            except Exception:
                pass
            try:
                _bb = st.session_state.get('v178_recovery_base_bounds', {}) or {}
                for k, v in (_bb or {}).items():
                    if isinstance(v, dict) and 'lo' in v and 'hi' in v:
                        bounds_default[k] = {'lo': float(v.get('lo')), 'hi': float(v.get('hi'))}
            except Exception:
                pass

            default_vars = list(st.session_state.get('v178_fs_vars', []) or [])
            if not default_vars:
                rep0 = st.session_state.get('v178_last_recovery')
                if isinstance(rep0, dict):
                    rv = rep0.get('recovery_vars')
                    if isinstance(rv, list) and rv:
                        default_vars = [str(x) for x in rv]
            if not default_vars:
                default_vars = list(bounds_default.keys())

            search_vars = st.multiselect(
                'Variables to search (explicit bounds required)',
                options=list(bounds_default.keys()),
                default=[k for k in default_vars if k in bounds_default],
                key='v178_fs_vars',
            )

            st.session_state.setdefault('v178_fs_bounds', {})
            _fsb = st.session_state.get('v178_fs_bounds', {}) or {}
            with st.expander('Search bounds (explicit)', expanded=False):
                for k in search_vars:
                    b0 = bounds_default.get(k, {})
                    lo0 = float((_fsb.get(k, {}) or {}).get('lo', b0.get('lo', 0.0)))
                    hi0 = float((_fsb.get(k, {}) or {}).get('hi', b0.get('hi', 1.0)))
                    span = max(1e-9, abs(hi0 - lo0))
                    a,b = st.columns(2)
                    with a:
                        lo = st.number_input(f'{k} lo', value=float(lo0), step=float(span/50.0), key=f'v178_fs_blo_{k}')
                    with b:
                        hi = st.number_input(f'{k} hi', value=float(hi0), step=float(span/50.0), key=f'v178_fs_bhi_{k}')
                    lo2 = float(min(lo, hi))
                    hi2 = float(max(lo, hi))
                    _fsb[k] = {'lo': lo2, 'hi': hi2}
            st.session_state['v178_fs_bounds'] = _fsb

            def _fs_obj_value(out: dict) -> float:
                try:
                    if str(obj_key).startswith('-'):
                        k = str(obj_key)[1:]
                        v = float(out.get(k, float('nan')))
                        return -v if math.isfinite(v) else float('inf')
                    v = float(out.get(str(obj_key), float('nan')))
                    return v if math.isfinite(v) else float('inf')
                except Exception:
                    return float('inf')

            _intent_key_fs = _design_intent_key()
            _hard_set_fs = set(_hard_constraint_names_for_intent())
            _ignore_set_fs = set(_ignored_constraint_names_for_intent())
            _soft_set_fs = set(_INTENT_SOFT.get(_intent_key_fs, set()))

            def _fs_is_feasible(out: dict) -> bool:
                """Feasibility under the active Design Intent hard-constraint set."""
                try:
                    from constraints.constraints import evaluate_constraints
                except Exception:
                    from src.constraints.constraints import evaluate_constraints  # type: ignore
                try:
                    cs = evaluate_constraints(out or {})
                    for c in cs:
                        nm = str(getattr(c, 'name', ''))
                        if nm in _ignore_set_fs:
                            continue
                        if nm in _hard_set_fs and not bool(getattr(c, 'passed', False)):
                            return False
                    return True
                except Exception:
                    return False

            def _fs_violation_score(out: dict) -> float:
                """Intent-aware continuous violation score (0 is best).

                Reactor intent: primarily used only as diagnostics (we still filter feasible-only).
                Research intent: used as the main objective to find best-compromise designs.
                """
                try:
                    from constraints.constraints import evaluate_constraints
                except Exception:
                    from src.constraints.constraints import evaluate_constraints  # type: ignore
                try:
                    cs = evaluate_constraints(out or {})
                except Exception:
                    cs = []
                V = 0.0
                for c in cs:
                    nm = str(getattr(c, 'name', ''))
                    if nm in _ignore_set_fs:
                        continue
                    try:
                        m = float(getattr(c, 'margin', float('nan')))
                    except Exception:
                        m = float('nan')
                    if not math.isfinite(m):
                        v = 1e6
                    else:
                        v = max(0.0, -m)
                    if nm in _hard_set_fs:
                        V += 100.0 * v * v
                    elif nm in _soft_set_fs:
                        V += 1.0 * v * v
                return float(V)

            def _fs_margins(out: dict) -> dict:
                try:
                    from constraints.constraints import evaluate_constraints
                except Exception:
                    from src.constraints.constraints import evaluate_constraints  # type: ignore
                m = {}
                try:
                    cs = evaluate_constraints(out or {})
                    for c in cs:
                        if getattr(c, 'severity', 'hard') == 'hard':
                            try:
                                m[c.name] = float(getattr(c, 'margin'))
                            except Exception:
                                m[c.name] = float('nan')
                except Exception:
                    pass
                return m

            def _fs_build_inputs(base_inp, varvals: dict):
                try:
                    from dataclasses import replace as _dc_replace, fields as _dc_fields
                    _valid = {f.name for f in _dc_fields(base_inp)}
                    _kwargs = {k: float(v) for k, v in (varvals or {}).items() if k in _valid}
                    return _dc_replace(base_inp, **_kwargs)
                except Exception:
                    return base_inp

            # Starting values
            start_vals = {}
            if src == 'Last feasible from Seeded Recovery':
                rep0 = st.session_state.get('v178_last_recovery')
                if isinstance(rep0, dict) and bool(rep0.get('ok')) and isinstance(rep0.get('best_point'), dict):
                    start_vals = dict(rep0.get('best_point') or {})
            elif src == 'Last Systems solution (if any)':
                try:
                    s_state = _v92_state_get()
                    _ls = getattr(s_state, 'last_systems_result', None)
                    if isinstance(_ls, dict) and isinstance(_ls.get('outputs'), dict):
                        out0 = _ls.get('outputs') or {}
                        start_vals = {k: float(out0.get(k)) for k in search_vars if k in out0 and out0.get(k) is not None}
                except Exception:
                    start_vals = {}

            if not start_vals:
                for k in search_vars:
                    b = _fsb.get(k, bounds_default.get(k, {})) or {}
                    lo = float(b.get('lo', 0.0)); hi = float(b.get('hi', 1.0))
                    start_vals[k] = 0.5*(lo+hi)

            try:
                from evaluator.core import Evaluator
            except Exception:
                from src.evaluator.core import Evaluator  # type: ignore
            ev_fs = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=8192)

            base_fs = base
            try:
                ov = st.session_state.get('systems_inputs_overrides', {}) or {}
                if isinstance(ov, dict) and ov:
                    base_fs = _fs_build_inputs(base_fs, ov)
            except Exception:
                pass

            def _run_feasible_search(_seed_override=None):
                seed0 = int(_seed_override) if _seed_override is not None else int(st.session_state.get('v178_fs_seed', 2026))
                rng = random.Random(seed0)
                budget = int(st.session_state.get('v178_fs_budget', 800))
                topk = int(st.session_state.get('v178_fs_topk', 12))
                radius = float(st.session_state.get('v178_fs_radius', 0.25))

                # Explicit bounds (with safety rails).
                bounds = {k: dict(_fsb.get(k, bounds_default.get(k, {})) or {}) for k in search_vars}
                for k, b in list(bounds.items()):
                    try:
                        lo = float(b.get('lo'))
                        hi = float(b.get('hi'))
                        bounds[k] = {'lo': lo, 'hi': hi}
                    except Exception:
                        del bounds[k]
                if not bounds:
                    return {'ok': False, 'reason': 'no_bounds', 'candidates': []}

                # MUST: validate bounds before running.
                _okb, _errs, _warns = _sys_validate_bounds(bounds)
                for _w in _warns:
                    try:
                        _alog('Systems', 'BoundsWarning', {'msg': _w})
                    except Exception:
                        pass
                if not _okb:
                    return {'ok': False, 'reason': 'invalid_bounds', 'errors': _errs, 'candidates': []}

                x_start = {k: float(start_vals.get(k, 0.5*(bounds[k]['lo']+bounds[k]['hi']))) for k in bounds.keys()}
                res0 = ev_fs.evaluate(_fs_build_inputs(base_fs, x_start))
                out0 = res0.out if res0 and res0.ok else {}
                feas0 = _fs_is_feasible(out0)
                obj0 = _fs_obj_value(out0)
                V0 = _fs_violation_score(out0)

                best_x = dict(x_start)
                best_obj = float(obj0) if math.isfinite(obj0) else float('inf')
                best_V = float(V0) if math.isfinite(V0) else float('inf')

                cands = []
                # Trace (COULD): store a lightweight evaluation trace for frontier plots and reproducibility.
                trace_keep = int(st.session_state.get('v178_fs_trace_keep', 2500))
                trace = []
                _MET_KEYS = ['q_div_MW_m2','P_SOL_over_R_MW_m','neutron_wall_load_MW_m2','sigma_vm_MPa','B_peak_T','TBR','hts_margin','H98','Q_DT_eqv','Pfus_DT_adj_MW']
                # Always record the start point as candidate in research mode; in reactor mode
                # we keep backward behavior (feasible-only candidates).
                if (_intent_key_fs == 'research') or feas0:
                    cands.append({'x': dict(x_start), 'obj': float(obj0), 'V': float(V0), 'feasible': bool(feas0), 'margins': _fs_margins(out0), 'headline': {'Q': out0.get('Q_DT_eqv'), 'H98': out0.get('H98'), 'P_net': out0.get('P_e_net_MW')}, 'metrics': {k: out0.get(k) for k in _MET_KEYS}})
                try:
                    if len(trace) < trace_keep:
                        trace.append({'i': 0, 'x': dict(x_start), 'obj': float(obj0) if math.isfinite(obj0) else None, 'V': float(V0) if math.isfinite(V0) else None, 'feasible': bool(feas0), 'metrics': {k: out0.get(k) for k in _MET_KEYS}})
                except Exception:
                    pass
                for i in range(max(0, budget-1)):
                    frac = max(0.05, radius * (1.0 - i/max(1, budget-1)))
                    x = {}
                    for k, b in bounds.items():
                        lo = b['lo']; hi = b['hi']
                        span = hi - lo
                        x0 = float(best_x.get(k, x_start.get(k))) if best_x else float(x_start.get(k))
                        step = frac * span
                        xv = x0 + (rng.random()*2.0 - 1.0) * step
                        xv = max(lo, min(hi, xv))
                        x[k] = float(xv)
                    res = ev_fs.evaluate(_fs_build_inputs(base_fs, x))
                    if not (res and res.ok and isinstance(res.out, dict)):
                        continue
                    out = res.out
                    feas = _fs_is_feasible(out)
                    V = _fs_violation_score(out)
                    obj = _fs_obj_value(out)

                    try:
                        if len(trace) < trace_keep:
                            trace.append({'x': dict(x), 'obj': float(obj) if math.isfinite(obj) else None, 'V': float(V) if math.isfinite(V) else None, 'feasible': bool(feas), 'metrics': {k: out.get(k) for k in _MET_KEYS}})
                    except Exception:
                        pass

                    if _intent_key_fs == 'reactor' and not feas:
                        continue

                    cands.append({'x': dict(x), 'obj': float(obj), 'V': float(V), 'feasible': bool(feas), 'margins': _fs_margins(out), 'headline': {'Q': out.get('Q_DT_eqv'), 'H98': out.get('H98'), 'P_net': out.get('P_e_net_MW')}, 'metrics': {k: out.get(k) for k in _MET_KEYS}})

                    # Update best according to intent.
                    if _intent_key_fs == 'reactor':
                        if feas and obj < best_obj:
                            best_obj = float(obj)
                            best_x = dict(x)
                    else:
                        # Research: prioritize violation score, then objective.
                        if (V < best_V - 1e-12) or (abs(V - best_V) <= 1e-12 and obj < best_obj):
                            best_V = float(V)
                            best_obj = float(obj)
                            best_x = dict(x)

                if _intent_key_fs == 'reactor':
                    cands.sort(key=lambda c: float(c.get('obj', float('inf'))))
                else:
                    cands.sort(key=lambda c: (float(c.get('V', float('inf'))), float(c.get('obj', float('inf')))))
                top = cands[:max(1, topk)] if cands else []
                return {
                    'ok': bool(len(top) > 0),
                    'reason': (
                        'feasible_candidates' if (_intent_key_fs == 'reactor' and len(top) > 0) else
                        ('best_compromise' if (_intent_key_fs == 'research' and len(top) > 0) else
                         ('start_not_feasible' if not feas0 else 'no_feasible_found'))
                    ),
                    'objective': str(obj_key),
                    'budget': budget,
                    'topk': topk,
                    'radius': radius,
                    'seed': int(seed0),
                    'vars': list(bounds.keys()),
                    'bounds': bounds,
                    'start_feasible': bool(feas0),
                    'start_obj': float(obj0) if math.isfinite(obj0) else None,
                    'start_V': float(V0) if math.isfinite(V0) else None,
                    'best_V': float(best_V) if math.isfinite(best_V) else None,
                    'best_obj': float(best_obj) if math.isfinite(best_obj) else None,
                    'best_x': dict(best_x) if best_x else None,
                    'candidates': top,
                    'trace': trace,
                    'trace_keep': trace_keep,
                    'ts_unix': float(time.time()),
                }
            action = st.session_state.get('_sys_action')

            _fs_running = bool(st.session_state.get('systems_fs_running', False))
            # Phase-1 UI stabilization: Feasible Search running watchdog + crash-safe execution.
            _fs_started_ts = float(st.session_state.get('systems_fs_started_ts', 0.0) or 0.0)
            if _fs_running and _fs_started_ts > 0.0:
                _fs_age_s = float(time.time()) - _fs_started_ts
                if _fs_age_s > 30.0:
                    with st.expander(' Feasible search appears stuck (watchdog)', expanded=False):
                        st.warning('A feasible-search run is marked as running, but no completion was recorded. You can safely clear the running flag to re-enable the button.')
                        st.caption(f'running_since = {_fs_age_s:.1f} s')
                        if st.button('Clear feasible-search running flag', use_container_width=True, key='v178_fs_clear_running'):
                            st.session_state['systems_fs_running'] = False
                            st.session_state['systems_fs_started_ts'] = 0.0
                            st.session_state['systems_fs_last_error'] = None
                            st.success('Cleared. You can run feasible search again.')
                            st.rerun()

            _run_search_clicked = st.button(
                'Run feasible design search',
                use_container_width=True,
                key='v178_fs_run_btn',
                disabled=_fs_running,
                help=('Running… please wait.' if _fs_running else None),
            ) or (action == 'search')
            if _fs_running and (action == 'search'):
                _run_search_clicked = False

            if _run_search_clicked:
                st.session_state['systems_fs_running'] = True
                st.session_state['systems_fs_started_ts'] = float(time.time())
                st.session_state['systems_fs_last_error'] = None
                if action == 'search':
                    st.session_state.pop('_sys_action', None)
                try:
                    try:
                        _alog('Systems', 'FeasibleSearchClicked', {
                            'objective': str(obj_key),
                            'budget': int(st.session_state.get('v178_fs_budget', 0)),
                            'topk': int(st.session_state.get('v178_fs_topk', 0)),
                            'multi_seed_runs': int(st.session_state.get('v179_fs_multiseed_n', 1)),
                            'vars': list(search_vars or []),
                            'intent': str(st.session_state.get('design_intent', '')),
                        })
                    except Exception:
                        pass

                    _nms = int(st.session_state.get('v179_fs_multiseed_n', 1))
                    _base_seed = int(st.session_state.get('v178_fs_seed', 2026))
                    _all = []
                    with st.spinner(f"Running feasible search… (budget={int(st.session_state.get('v178_fs_budget', 800))}, runs={_nms}). This may take a while."):
                        for _j in range(max(1, _nms)):
                            _all.append(_run_feasible_search(_seed_override=int(_base_seed + _j)))
                    rep = _all[0] if _all else {'ok': False, 'reason': 'no_result', 'candidates': []}
                    try:
                        _intent = str(st.session_state.get('design_intent','')).lower()
                        _intent_key = 'research' if 'research' in _intent else 'reactor'
                        _topk = int(rep.get('topk', int(st.session_state.get('v178_fs_topk', 12))))
                        _cands = []
                        _trace = []
                        for _r in _all:
                            for _c in list(_r.get('candidates', []) or []):
                                _cc = dict(_c); _cc['seed'] = _r.get('seed'); _cands.append(_cc)
                            for _t in list(_r.get('trace', []) or []):
                                _tt = dict(_t); _tt['seed'] = _r.get('seed'); _trace.append(_tt)
                        if _intent_key == 'reactor':
                            _cands.sort(key=lambda c: float(c.get('obj', float('inf'))))
                        else:
                            _cands.sort(key=lambda c: (float(c.get('V', float('inf'))), float(c.get('obj', float('inf')))))
                        rep['candidates'] = _cands[:max(1, _topk)] if _cands else []
                        rep['trace'] = _trace[-int(rep.get('trace_keep', 2500)):] if _trace else []
                        rep['multi_seed_runs'] = int(_nms)
                        rep['all_runs'] = _all
                        rep['seed'] = int(_base_seed)
                        rep['ok'] = bool(len(rep.get('candidates', []) or []) > 0)
                        rep['reason'] = 'multi_seed_' + str(rep.get('reason'))
                    except Exception:
                        pass

                    st.session_state['v178_fs_last'] = rep
                    try:
                        _alog('Systems', 'FeasibleSearchDone', {'ok': bool(rep.get('ok', False)), 'reason': str(rep.get('reason',''))})
                    except Exception:
                        pass
                except Exception as _e:
                    st.session_state['systems_fs_last_error'] = str(_e)
                    _alog_exc('Systems', 'FeasibleSearchError', _e)
                    st.error(f'Feasible search failed: {_e}')
                finally:
                    st.session_state['systems_fs_running'] = False
                    st.session_state['systems_fs_started_ts'] = 0.0
                    st.rerun()

    _precheck_only = False  # legacy flag (kept for backward compatibility)
    # Persisted solver knobs must be defined regardless of which UI subsections were rendered on this rerun.
    # (Phase-1 rule: no conditional variable definitions.)
    block_solve = bool(st.session_state.get("systems_block_solve", False))
    if run:
        # Local flow-control exception: block the full solve without calling
        # st.stop(), which can destabilize Streamlit rerun/tab selection.
        class _SysPrecheckBlocksSolve(Exception):
            """Raised to skip the full Systems solve when precheck blocks it."""
            pass

        _warn_unrealistic_point_inputs(base, context="Systems")
        st.info("Running coupled solve…")
        try:
            _alog(
                "Systems",
                "RunSystemsSolve",
                {
                    "n_targets": int(len(targets)),
                    "n_variables": int(len(variables)),
                    "targets": {k: float(v) for k, v in (targets or {}).items()},
                    "mode": "robust"if robust_mode else "fast",
                    "warm_start": bool(warm_start),
                    "continuation": bool(do_continuation),
                    "block_solve": bool(block_solve),
                },
            )
        except Exception:
            pass
        log = st.empty()
        last = None

        coupled = (len(targets) > 1) or (len(variables) > 1)
        base_for_solve = base
        # v177.5: apply persisted constraint-threshold overrides (Inputs knobs) to Systems base inputs.
        st.session_state.setdefault('systems_inputs_overrides', {})
        _io = st.session_state.get('systems_inputs_overrides', {}) or {}
        if isinstance(_io, dict) and _io:
            try:
                from dataclasses import replace as _dc_replace
                _kwargs = {k: float(v) for k, v in _io.items() if hasattr(base_for_solve, k)}
                if _kwargs:
                    base_for_solve = _dc_replace(base_for_solve, **_kwargs)
            except Exception:
                pass


        # v176.0: warm-start initial guesses from last Systems artifact
        if warm_start:
            try:
                _ls = getattr(s, 'last_systems_result', None)
                if isinstance(_ls, dict):
                    _outs = _ls.get('outputs') or {}
                    for _vn, (_x0, _lo, _hi) in list(variables.items()):
                        if _vn in _outs and _outs[_vn] is not None:
                            try:
                                _x = float(_outs[_vn])
                                # clamp to bounds
                                _x = max(float(_lo), min(float(_hi), _x))
                                variables[_vn] = (_x, float(_lo), float(_hi))
                            except Exception:
                                pass
            except Exception:
                pass


        # -----------------------------
        # Feasibility-first precheck (explicit; UI-side only)
        # -----------------------------


        # v177: richer precheck + completion assistant (core helpers in src/systems)
        if do_precheck and len(variables) > 0:
            import time as _time
            t_pre0 = _time.perf_counter()
            try:
                from evaluator.core import Evaluator
            except Exception:
                from src.evaluator.core import Evaluator  # type: ignore
            try:
                from systems.feasibility_completion import run_precheck, propose_feasibility_completion
            except Exception:
                from src.systems.feasibility_completion import run_precheck, propose_feasibility_completion  # type: ignore

            # Share a single evaluator cache for precheck + atlas + scout within this run
            _sys_ev = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)

            try:
                _pre = run_precheck(
                    base_for_solve,
                    targets,
                    variables,
                    include_random=True,
                    n_random=int(st.session_state.get('v177_precheck_n_random', 8)),
                    seed=int(st.session_state.get('v177_precheck_seed', 1337)),
                    evaluator=_sys_ev,
                    hard_constraint_names=_hard_constraint_names_for_intent(),
                )
            except Exception as _e:
                _pre = None

            try:
                precheck_s = float(_time.perf_counter() - t_pre0)
            except Exception:
                precheck_s = None
            if precheck_s is not None:
                st.session_state['systems_precheck_seconds'] = float(precheck_s)

            if _pre is not None:
                st.session_state['last_precheck_report'] = _pre

            # Run card (MUST): standardized precheck summary
            try:
                if _pre is not None:
                    bm = dict(getattr(_pre, 'hard_constraints_best_margin', {}) or {})
                    dom = None
                    try:
                        if bm:
                            dom = sorted([(k, float(v)) for k, v in bm.items() if isinstance(v, (int, float)) and math.isfinite(float(v))], key=lambda t: t[1])[0][0]
                    except Exception:
                        dom = None
                    outc = {
                        'status': 'ok' if bool(getattr(_pre, 'ok', False)) else 'fail',
                        'reason': str(getattr(_pre, 'reason', '')),
                        'dominant_limiter': dom,
                        'limiters': list(getattr(_pre, 'hard_constraints_failed_at_all_samples', []) or []),
                        'next': _sys_failure_taxonomy(str(getattr(_pre, 'reason', ''))).get('next', []) + _sys_levers_from_limiters([dom] if dom else list(getattr(_pre, 'hard_constraints_failed_at_all_samples', []) or [])),
                    }
                    _sys_append_run_card(kind='Precheck', settings={'intent': st.session_state.get('design_intent',''), 'n_samples': int(getattr(_pre, 'n_samples', 0)), 'n_vars': int(len(variables or {}))}, outcome=outc)
            except Exception:
                pass

            # If we were triggered by an assistant 'Apply' action, only run precheck (do not run the full solve).
            if _precheck_only and (_pre is not None) and bool(getattr(_pre, 'ok', False)):
                st.success('Precheck: feasible within declared bounds (sampled).')
                with st.expander('Precheck report (detailed)', expanded=False):
                    st.write(f"Samples evaluated: **{int(_pre.n_samples)}**")
                    st.write(f"Unreachable targets confidence: **{_pre.unreachable_targets_confidence}**")
                    st.caption('Full solve was not run. Click **Run systems solve** to proceed.')
                st.stop()

            if (_pre is not None) and (not bool(_pre.ok)):
                try:
                    _alog(
                        "Systems",
                        "PrecheckInfeasible",
                        {
                            "samples": int(getattr(_pre, 'n_samples', 0)),
                            "confidence": str(getattr(_pre, 'unreachable_targets_confidence', '')),
                            "failed_all": list(getattr(_pre, 'hard_constraints_failed_at_all_samples', []) or []),
                            "best_margins": dict(getattr(_pre, 'hard_constraints_best_margin', {}) or {}),
                            "unreachable_targets": list(getattr(_pre, 'unreachable_targets', []) or []),
                        },
                    )
                except Exception:
                    pass
                fail = {
                    'event': 'fail',
                    'reason': 'precheck_infeasible',
                    'unreachable_targets': _pre.unreachable_targets,
                    # keep backward-compatible key name
                    'hard_constraints_failed_at_all_corners': _pre.hard_constraints_failed_at_all_samples,
                    'precheck_seconds': precheck_s,
                }
                log.code(json.dumps(fail, indent=2, sort_keys=True))
                if _design_intent_key() == 'reactor':
                    st.error('Precheck: infeasible within declared bounds (sampled evaluation). Use the assistant below to apply minimal changes.')
                else:
                    # v178.6: intent-aware messaging.
                    _hs = sorted(list(_hard_constraint_names_for_intent()))
                    st.warning('Precheck: infeasible under current hard-constraint set ' + (f"({', '.join(_hs)})"if _hs else '') + '. In **Experimental Device** intent, this does not block exploration; you can still run solves to study the machine.')

                with st.expander('Precheck report (detailed)', expanded=False):
                    st.write(f"Samples evaluated: **{int(_pre.n_samples)}**")
                    st.write(f"Unreachable targets confidence: **{_pre.unreachable_targets_confidence}**")
                    if _pre.hard_constraints_failed_at_all_samples:
                        st.markdown('**Hard constraints failed at all samples**')
                        ranked = sorted(
                            [(nm, float(_pre.hard_constraints_best_margin.get(nm, float('nan'))), _pre.hard_constraints_best_sample.get(nm, '')) for nm in _pre.hard_constraints_failed_at_all_samples],
                            key=lambda t: (t[1] if t[1]==t[1] else -1e9),
                            reverse=True,
                        )
                        for nm, bm, sn in ranked:
                            st.write(f"- **{nm}**: best margin {bm:.3g} at sample `{sn}`")
                    if _pre.unreachable_targets:
                        st.markdown('**Targets outside sampled reachable range**')
                        for u in _pre.unreachable_targets:
                            if 'sample_min' in u:
                                tgt_name = str(u.get('target'))
                                st.write(f"- **{tgt_name}**: requested {u.get('target_value')} vs sampled range [{u.get('sample_min')}, {u.get('sample_max')}]")

                                # Quick-fix button for the most common case: Q target is outside sampled range.
                                # Users may miss the target widget (collapsed expander / scrolled UI), so offer
                                # a one-click adjustment that is fully logged.
                                try:
                                    if tgt_name in ('Q_DT_eqv', 'Q', 'Q_target'):
                                        smin = float(u.get('sample_min'))
                                        # Nudge above the sampled minimum (so it is clearly reachable).
                                        suggested = float(math.ceil(smin * 10.0) / 10.0)
                                        if st.button(f"Set Q target to {suggested:g} (make reachable)", key=f"v178_set_Q_from_pre_{suggested:g}"):
                                            try:
                                                st.session_state[PD_KEYS["Q_tgt"]] = suggested
                                            except Exception:
                                                st.session_state["v178_Q_tgt_fallback"] = suggested
                                            try:
                                                _alog('Systems', 'SetTargetFromPrecheck', {
                                                    'target': tgt_name,
                                                    'suggested': suggested,
                                                    'sample_min': smin,
                                                })
                                            except Exception:
                                                pass
                                            st.experimental_rerun()
                                except Exception:
                                    pass
                            else:
                                st.write(f"- **{u.get('target')}**: {u.get('reason')}")

                    with st.expander('Sample table (debug)', expanded=False):
                        try:
                            import pandas as _pd  # type: ignore
                            rows = []
                            for sr in _pre.samples:
                                rows.append({
                                    'sample': sr.sample.name,
                                    'hard_failed': ', '.join(sr.hard_failed),
                                    **{k: float(sr.sample.values.get(k, float('nan'))) for k in variables.keys()},
                                })
                            st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                        except Exception as _e:
                            st.caption(f"Sample table unavailable: {_e}")

                # Reactor intent is feasibility-authoritative: an infeasible precheck
                # blocks the full solve. Do **not** call st.stop() here; instead raise
                # a local flow-control exception that is handled below so UI remains
                # stable and navigation is not affected.
                if _design_intent_key() == 'reactor':
                    raise _SysPrecheckBlocksSolve('precheck_infeasible_reactor')

# Assistant UI is rendered in the persistent Precheck panel above.
                st.info('Feasibility completion assistant is available in the Precheck panel. Run precheck there to generate and apply proposals.')
        # v177: optionally run a feasibility scout before target solve (deterministic)
        if st.session_state.get('v177_feasibility_scout_enabled', False):
            try:
                from systems.feasibility_completion import feasibility_scout
            except Exception:
                from src.systems.feasibility_completion import feasibility_scout  # type: ignore
            try:
                from evaluator.core import Evaluator
            except Exception:
                from src.evaluator.core import Evaluator  # type: ignore
            _ev2 = _dsg_evaluator(origin="UI", cache_enabled=True, cache_max=4096)
            scout = feasibility_scout(
                base_for_solve,
                variables,
                evaluator=_ev2,
                n_samples=int(st.session_state.get('v177_scout_n_samples', 64)),
                seed=int(st.session_state.get('v177_precheck_seed', 1337)),
                n_refine=int(st.session_state.get('v177_scout_n_refine', 20)),
                hard_constraint_names=_hard_constraint_names_for_intent(),
            )
            if scout.get('ok'):
                base_for_solve = scout.get('best_inp', base_for_solve)
                log.code(json.dumps({'event': 'feasibility_scout', 'ok': True, 'best_min_margin': scout.get('best_min_margin')}, indent=2, sort_keys=True))
                st.info('Feasibility scout found a feasible start point within bounds; using it as initial guess.')
            else:
                log.code(json.dumps({'event': 'feasibility_scout', 'ok': False, 'best_score': scout.get('best_score'), 'hard_failed': scout.get('hard_failed')}, indent=2, sort_keys=True))
                st.warning('Feasibility scout did not find a fully feasible point; proceeding with the chosen base guess.')

        # Apply Systems-mode constraint knob overrides (from assistant)
        try:
            ov = st.session_state.get('systems_inputs_overrides', {})
            if isinstance(ov, dict) and ov:
                d0 = dict(base_for_solve.__dict__)
                d0.update({k: float(v) for k, v in ov.items()})
                base_for_solve = PointInputs(**d0)
        except Exception:
            pass

        # Solver knob defaults must be available regardless of which UI branches executed on this rerun.
        # (Phase-1 rule: no conditional variable definitions.)
        block_solve = bool(st.session_state.get("systems_block_solve", False))


        # -----------------------------
        # Continuation ramp to targets (explicit; UI-side only)
        # -----------------------------
        if coupled and do_continuation and cont_steps >= 2:
            try:
                out0 = _ui_evaluate(base_for_solve, origin="Systems")
            except Exception:
                out0 = {}

            start_targets = {}
            for k in targets.keys():
                try:
                    v = float(out0.get(k, float("nan")))
                except Exception:
                    v = float("nan")
                if v == v and abs(v) != float("inf"):
                    start_targets[k] = v

            def _make_req(_base: PointInputs, _t: dict) -> SolverRequest:
                opts = {"multistart": True, "restarts": 8, "cache_enabled": True, "cache_max": 1024}
                if trust_delta is not None:
                    opts["trust_delta"] = float(trust_delta)
                if block_solve:
                    opts["block_solve"] = True
                return SolverRequest(base=_base, targets=_t, variables=variables, max_iter=max_iter, tol=float(tol), damping=float(damping), options=opts)

            base_stage = base_for_solve
            for s in range(1, int(cont_steps)):
                alpha = float(s) / float(cont_steps)
                step_targets = {}
                for k, final in targets.items():
                    if k in start_targets:
                        step_targets[k] = float(start_targets[k] + alpha * (float(final) - float(start_targets[k])))
                    else:
                        step_targets[k] = float(final)

                log.code(json.dumps({"event": "cont_step", "step": float(s), "n_steps": float(cont_steps), "alpha": alpha, "targets": step_targets}, indent=2, sort_keys=True))
                _res = solve_request(_make_req(base_stage, step_targets), backend=DefaultTargetSolverBackend())
                log.code(json.dumps({"event": "cont_result", "step": float(s), "ok": bool(_res.ok), "iters": float(_res.iters), "message": _res.message}, indent=2, sort_keys=True))
                if not _res.ok:
                    fail = {"event": "fail", "reason": "continuation_step_fail", "step": float(s), "alpha": alpha, "message": _res.message}
                    log.code(json.dumps(fail, indent=2, sort_keys=True))
                    st.error("Continuation step failed. Adjust targets/bounds or disable continuation.")
                    st.stop()
                base_stage = _res.inp

            base_for_solve = base_stage
        try:
            for step in solve_for_targets_stream(
                base_for_solve,
                targets=targets,
                variables=variables,
                max_iter=max_iter,
                tol=float(tol),
                damping=float(damping),
                trust_delta=(float(trust_delta) if trust_delta is not None else None),
            ):
                last = step
                log.code(json.dumps(step, indent=2, sort_keys=True))
            req = SolverRequest(base=base_for_solve, targets=targets, variables=variables, max_iter=max_iter, tol=float(tol), damping=float(damping), options={"multistart": True, "restarts": 8, "cache_enabled": True, "cache_max": 1024, **({"trust_delta": float(trust_delta)} if trust_delta is not None else {}), **({"block_solve": True} if block_solve else {})})
            import time as _time
            t_solve0 = _time.perf_counter()
            res = solve_request(req, backend=DefaultTargetSolverBackend())
            wall_s = float(_time.perf_counter() - t_solve0)
            inp_sol = res.inp
            out_sol = res.out
            st.success(f"Done. Converged={res.ok}, iterations={res.iters}")

            if not res.ok and ("Ip_MA"in variables and "fG"in variables) and ("H98"in targets and "Q_DT_eqv"in targets):
                with st.expander("Target feasibility at (Iₚ, f_G) bound corners", expanded=False):
                    try:
                        from solvers.constraint_solver import evaluate_targets_at_corners
                        lo0, hi0 = float(variables["Ip_MA"][1]), float(variables["Ip_MA"][2])
                        lo1, hi1 = float(variables["fG"][1]), float(variables["fG"][2])
                        rows = evaluate_targets_at_corners(base, {"H98": float(targets["H98"]), "Q_DT_eqv": float(targets["Q_DT_eqv"])}, ("Ip_MA", lo0, hi0), ("fG", lo1, hi1))
                        import pandas as _pd  # type: ignore
                        st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                    except Exception as _e:
                        st.caption(f"Corner table unavailable: {_e}")
            st.session_state["last_point_inp"] = inp_sol
            st.session_state["last_point_out"] = out_sol

            constraints_list = evaluate_constraints(out_sol)
            solver_meta = {"message": res.message, "trace": res.trace or []}
            artifact = build_run_artifact(
                inputs=dict(inp_sol.__dict__),
                outputs=dict(out_sol),
                constraints=constraints_list,
                meta={"mode": "systems"},
                solver=solver_meta,
                baseline_inputs=dict(base.__dict__),
                subsystems={
                    "fidelity": st.session_state.get("fidelity_config", {}),
                    "calibration": {
                        "confinement": float(st.session_state.get("calib_confinement", 1.0)),
                        "divertor": float(st.session_state.get("calib_divertor", 1.0)),
                        "bootstrap": float(st.session_state.get("calib_bootstrap", 1.0)),
                    },
                },
            )

            # ---- Systems Mode freeze contract (schema_version=1) ----
            # NOTE: This is purely metadata; it does not affect physics.
            try:
                from src.systems.schema import SCHEMA_VERSION as _SYS_SCHEMA_V, freeze_contract as _sys_freeze_contract
            except Exception:  # pragma: no cover
                from systems.schema import SCHEMA_VERSION as _SYS_SCHEMA_V, freeze_contract as _sys_freeze_contract
            artifact.setdefault("schema_version", int(_SYS_SCHEMA_V))
            artifact.setdefault("freeze_contract", _sys_freeze_contract())
            artifact.setdefault("artifact_kind", "systems")

            # ---- Human-readable freeze statement (mirrors Point Designer governance banner) ----
            try:
                artifact.setdefault("freeze_statement", {
                    "systems_mode": "FROZEN",
                    "version": "v187.1",
                    "basis": "Point Designer physics/constraints are immutable; Systems Mode explores and ranks candidates using intent-aware acceptance without altering evaluator logic.",
                })
            except Exception:
                pass

            # ---- Intent-aware feasibility summary (resolves hard-feasibility vs intent ambiguity) ----
            try:
                failed_names = []
                for _c in constraints_list:
                    try:
                        if not bool(getattr(_c, "passed", True)) and str(getattr(_c, "severity", "hard")).lower() == "hard":
                            failed_names.append(str(getattr(_c, "name", "")))
                    except Exception:
                        pass
                _cls = _classify_failed_constraints(failed_names)
                artifact["intent_feasibility_summary"] = {
                    **_constraint_policy_snapshot(),
                    "blocking_feasible": (len(_cls.get("blocking", [])) == 0),
                    "failed_blocking": _cls.get("blocking", []),
                    "failed_diagnostic": _cls.get("diagnostic", []),
                    "failed_ignored": _cls.get("ignored", []),
                    "note": "Feasibility under active Design Intent; hard constraint failures may be diagnostic/ignored in Research intent.",
                }
            except Exception:
                pass

            # Frozen top-level key: run_cards (keep ui_state copy for restore)
            try:
                _cards = st.session_state.get("systems_run_cards", [])
                artifact["run_cards"] = _shams_json_sanitize(_cards)
            except Exception:
                pass

            # Embed enough UI state into the artifact so it can fully restore Systems Mode later.
            # This does NOT change physics; it is purely UX/state persistence.
            try:
                artifact.setdefault("ui_state", {})
                _ui_state = {
                    "workflow_step": str(st.session_state.get("systems_workflow_step", "")),
                    "design_intent": str(st.session_state.get("design_intent", "")),
                    "systems_run_cards": st.session_state.get("systems_run_cards", []),
                    "systems_journal": st.session_state.get("systems_journal", []),
                    "v178_last_precheck": st.session_state.get("v178_last_precheck"),
                    "v178_last_recovery": st.session_state.get("v178_last_recovery"),
                    "v178_fs_last": st.session_state.get("v178_fs_last"),
                }
                # Important: sanitize to prevent circular refs / Streamlit state leaks.
                artifact["ui_state"].update(_shams_json_sanitize(_ui_state))
            except Exception:
                pass



            # v380.0: Impurity radiation partition + detachment requirement certification (governance-only)
            try:
                from src.certification.impurity_radiation_detachment_certification_v380 import (
                    evaluate_impurity_radiation_detachment_authority,
                )
                _cert = evaluate_impurity_radiation_detachment_authority(out_sol).to_dict()
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['impurity_radiation_detachment_v380'] = _cert
            except Exception:
                pass
            # v381.0: Advanced current-drive authority (governance-only)
            try:
                from src.certification.current_drive_certification_v381 import (
                    evaluate_current_drive_authority,
                )
                _cd_cert = evaluate_current_drive_authority(out_sol).to_dict()
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['current_drive_v381'] = _cd_cert
            except Exception:
                pass

            # v383.0: Plant economics & cost authority 2.0 (governance-only)
            try:
                from src.certification.plant_economics_certification_v383 import (
                    evaluate_plant_economics_authority_v383,
                )
                _pe_cert = evaluate_plant_economics_authority_v383(
                    out_sol,
                    inputs=(artifact.get('inputs') if isinstance(artifact.get('inputs'), dict) else None),
                ).to_dict()
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['plant_economics_v383'] = _pe_cert
            except Exception:
                pass

            # v388.0.0: Cost Authority 3.0 — Industrial Depth (governance-only)
            try:
                from src.certification.cost_authority_certification_v388 import (
                    evaluate_cost_authority_v388,
                )
                _c388 = evaluate_cost_authority_v388(
                    out_sol,
                    inputs=(artifact.get('inputs') if isinstance(artifact.get('inputs'), dict) else None),
                ).to_dict()
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['cost_authority_v388'] = _c388
            except Exception:
                pass

            # v389.0.0: Structural Stress Authority (governance-only)
            try:
                from src.certification.structural_stress_certification_v389 import (
                    certify_structural_stress_v389,
                )
                _s389 = certify_structural_stress_v389(out_sol)
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['structural_stress_v389'] = _s389
            except Exception:
                pass

            # v393.0.0: Damage→Strength Coupling (governance-only)
            try:
                from src.certification.damage_strength_coupling_certification_v393 import (
                    certify_damage_strength_coupling_v393,
                )
                _d393 = certify_damage_strength_coupling_v393(out_sol)
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['damage_strength_coupling_v393'] = _d393
            except Exception:
                pass

            # v390.0.0: Neutronics & Activation Authority 3.0 (governance-only)
            try:
                from src.certification.neutronics_activation_certification_v390 import (
                    certify_neutronics_activation_v390,
                )
                _n390 = certify_neutronics_activation_v390(out_sol)
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['neutronics_activation_v390'] = _n390
            except Exception:
                pass

            # v391.0.0: Availability 2.0 — Reliability Envelope Authority (governance-only)
            try:
                from src.certification.availability_reliability_certification_v391 import (
                    certify_availability_reliability_v391,
                )
                _a391 = certify_availability_reliability_v391(out_sol)
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['availability_reliability_v391'] = _a391
            except Exception:
                pass

            # v392.0.0: Neutronics Shield Attenuation Authority (governance-only)
            try:
                from src.certification.neutronics_shield_attenuation_certification_v392 import (
                    certify_neutronics_shield_attenuation_v392,
                )
                _n392 = certify_neutronics_shield_attenuation_v392(out_sol)
                artifact.setdefault('certifications', {})
                if isinstance(artifact.get('certifications'), dict):
                    artifact['certifications']['neutronics_shield_attenuation_v392'] = _n392
            except Exception:
                pass

            # v176.2: attach lightweight telemetry so users can verify performance changes
            try:
                precheck_s = st.session_state.get("systems_precheck_seconds", None)
                tel = {
                    "wall_s": float(wall_s),
                    "precheck_s": (float(precheck_s) if precheck_s is not None else None),
                    "backend": str(solver_backend),
                    "robust_mode": bool(robust_mode),
                    "warm_start": bool(warm_start),
                    "continuation": bool(cont_enabled),
                    "block_solve": bool(block_solve),
                    "n_targets": int(len(targets)),
                    "n_variables": int(len(variables)),
                    "max_iter": int(max_iter),
                    "tol": float(tol),
                }
                artifact.setdefault("meta", {})
                artifact["meta"]["telemetry"] = tel
                st.session_state["last_systems_telemetry"] = tel
            except Exception:
                pass

            # v98.1: cache + ledger record (systems)
            try:
                s = _v92_state_get()
                s.last_systems_result = artifact
                # v182.1: also cache into session_state for rerun-stable rendering
                st.session_state['systems_last_solve_artifact'] = artifact
                # Canonical interop cache keys (Phase-1 contract): other decks
                # (Scan/Pareto/Trade Study) consume these without triggering compute.
                st.session_state['systems_last_solution'] = artifact
                st.session_state['last_systems_solution'] = artifact
                _v98_record_run("systems", artifact, mode="systems_mode")
            except Exception:
                pass

            st.markdown("### Key results")
            kcols = st.columns(4)
            def _k(metric, key, fmt="{:.3g}"):
                v = float(out_sol.get(key, float("nan")))
                with metric:
                    st.metric(key, fmt.format(v) if v==v else "NaN")
            _k(kcols[0], "Q_DT_eqv", "{:.3g}")
            _k(kcols[1], "H98", "{:.3g}")
            _k(kcols[2], "P_e_net_MW", "{:.3g}")
            _k(kcols[3], "q_div_MW_m2", "{:.3g}")

            # constraints dashboard
            with st.expander("Constraints & margins (systems mode)", expanded=False):
                rows_c = []
                for c in constraints_list:
                    try:
                        margin = float(getattr(c, "margin"))
                    except Exception:
                        margin = float("nan")
                    rows_c.append({
                        "constraint": c.name,
                        "sense": c.sense,
                        "value": c.value,
                        "limit": c.limit,
                        "units": c.units,
                        "passed": bool(c.passed),
                        "margin_frac": margin,
                        "severity": getattr(c, "severity", "hard"),
                        "note": c.note,
                    })
                dfc = pd.DataFrame(rows_c)
                st.dataframe(dfc, use_container_width=True)

            # Sankey + radial build
            with st.expander("Plots (radial build + power balance)", expanded=False):
                try:
                    import tempfile, os
                    tmpdir = tempfile.mkdtemp(prefix="shams_systems_")
                    rb = os.path.join(tmpdir, "radial_build.png")
                    plot_radial_build_from_artifact(artifact, rb)
                    st.image(rb, caption="Radial build (proxy)", use_container_width=True)
                except Exception as e:
                    st.warning(f"Radial build plot unavailable: {e}")
                try:
                    import tempfile, os
                    from shams_io.sankey import build_power_balance_sankey
                    import plotly.graph_objects as go
                    sank = build_power_balance_sankey(artifact)
                    fig = go.Figure(data=[go.Sankey(**sank)])
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Sankey unavailable: {e}")

            # v374.2: Post-Key-results diagnostics bundle (Compact Cockpit + Systems Console)
            with st.expander("Detailed Systems Diagnostics (post-run)", expanded=False):
                # Compact Cockpit controls
                cc1, cc2, cc3 = st.columns([1, 1, 2])
                with cc1:
                    sys_cockpit_pin = st.toggle(
                        "Pin cockpit",
                        value=st.session_state.get("systems_cockpit_pin", False),
                        key="systems_cockpit_pin",
                    )
                with cc2:
                    sys_cockpit_show_md = st.toggle(
                        "Show markdown",
                        value=st.session_state.get("systems_cockpit_show_md", False),
                        key="systems_cockpit_show_md",
                    )
                with cc3:
                    st.caption("Diagnostics only (does not change physics, constraints, or truth).")

                _ = sys_cockpit_pin  # retained for future pin behavior

                # Compact cockpit
                try:
                    _sys_render_compact_cockpit()
                except Exception:
                    st.caption("Compact cockpit unavailable (non-fatal).")

                # Systems Console: verdict bar + why-chain + constraint cards
                try:
                    _sys_art2 = st.session_state.get("systems_last_solve_artifact") or _sys_fetch_latest_systems_artifact()
                    if isinstance(_sys_art2, dict):
                        _sys_cons2 = _sys_extract_constraints(_sys_art2)
                        _sys_render_verdict_bar(_sys_art2, constraints=_sys_cons2)
                        _sys_render_causal_chain(
                            _sys_art2,
                            constraints=_sys_cons2,
                            expert=st.session_state.get("systems_expert_view", False),
                        )
                        _sys_render_constraint_cards(_sys_art2, constraints=_sys_cons2)
                    else:
                        st.info("No cached Systems artifact yet. Run Precheck / Solve to populate diagnostics.")
                except Exception:
                    st.caption("Detailed diagnostics unavailable (non-fatal).")

            # v375.0: Exhaust authority (certified bundle) — kept under Key results
            with st.expander("Exhaust & Divertor Authority (certified)", expanded=False):
                try:
                    _ea = {
                        "lambda_q_mm_raw": float(out_sol.get("lambda_q_mm_raw", float("nan"))),
                        "lambda_q_mm_used": float(out_sol.get("lambda_q_mm", float("nan"))),
                        "flux_expansion_raw": float(out_sol.get("flux_expansion_raw", float("nan"))),
                        "flux_expansion_used": float(out_sol.get("flux_expansion", float("nan"))),
                        "n_strike_points_raw": int(out_sol.get("n_strike_points_raw", out_sol.get("n_strike_points", 2)) or 2),
                        "n_strike_points_used": int(out_sol.get("n_strike_points", 2) or 2),
                        "f_wet_raw": float(out_sol.get("f_wet_raw", float("nan"))),
                        "f_wet_used": float(out_sol.get("f_wet_divertor", float("nan"))),
                        "A_wet_m2": float(out_sol.get("A_wet_m2", float("nan"))),
                        "q_div_MW_m2": float(out_sol.get("q_div_MW_m2", float("nan"))),
                        "q_div_max_MW_m2": float(out_sol.get("q_div_max_MW_m2", float("nan"))),
                        "q_div_unit_suspect": float(out_sol.get("q_div_unit_suspect", 0.0)),
                        "contract_sha256": str(out_sol.get("exhaust_authority_contract_sha256", "")),
                    }
                    st.dataframe(pd.DataFrame([_ea]), use_container_width=True)
                    if float(_ea.get("q_div_unit_suspect", 0.0)) >= 0.5:
                        st.warning("q_div magnitude looks unit-suspect (>1e5 MW/m²). This is a flag only; truth is unchanged.")
                except Exception as _e:
                    st.caption(f"Exhaust authority bundle unavailable (non-fatal): {_e}")

            # v380.0: Impurity radiation partition + detachment requirement (certified)
            with st.expander("Impurity radiation & detachment authority (certified)", expanded=False):
                try:
                    from src.certification.impurity_radiation_detachment_certification_v380 import (
                        evaluate_impurity_radiation_detachment_authority,
                        certification_table_rows,
                    )

                    _cert = evaluate_impurity_radiation_detachment_authority(out_sol).to_dict()
                    st.dataframe(pd.DataFrame([certification_table_rows(_cert)]), use_container_width=True)
                    with st.expander("Details", expanded=False):
                        st.json(_cert)
                except Exception as _e:
                    st.caption(f"Impurity/detachment authority unavailable (non-fatal): {_e}")


                # v381.0: Current drive authority (certified)
                with st.expander("Current drive authority (certified)", expanded=False):
                    try:
                        _cert = None
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _cert = _certs.get('current_drive_v381')
                        if not isinstance(_cert, dict):
                            st.info("No cached current-drive certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.current_drive_certification_v381 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_cert)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_cert)
                    except Exception as _e:
                        st.caption(f"Current-drive authority unavailable (non-fatal): {_e}")


                # v383.0: Plant economics & cost authority 2.0 (certified)
                with st.expander("Plant economics & cost authority (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _pec = _certs.get('plant_economics_v383')
                        if not isinstance(_pec, dict):
                            st.info("No cached plant economics certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.plant_economics_certification_v383 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_pec)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_pec)
                    except Exception as _e:
                        st.caption(f"Plant economics authority unavailable (non-fatal): {_e}")


                # v388.0.0: Cost Authority 3.0 — Industrial Depth (certified)
                with st.expander("Cost authority — industrial depth (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _c388 = _certs.get('cost_authority_v388')
                        if not isinstance(_c388, dict):
                            st.info("No cached cost authority certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.cost_authority_certification_v388 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_c388)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_c388)
                    except Exception as _e:
                        st.caption(f"Cost authority unavailable (non-fatal): {_e}")

                # v389.0.0: Structural Stress Authority (certified)
                with st.expander("Structural stress authority (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _s389 = _certs.get('structural_stress_v389')
                        if isinstance(_s389, dict):
                            st.json(_s389)
                        else:
                            st.caption("Structural stress authority (v389) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Structural stress authority unavailable (non-fatal): {_e}")

                # v393.0.0: Damage→Strength Coupling (certified)
                with st.expander("Damage → strength coupling (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _d393 = _certs.get('damage_strength_coupling_v393')
                        if isinstance(_d393, dict):
                            st.json(_d393)
                        else:
                            st.caption("Damage → strength coupling (v393) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Damage → strength coupling unavailable (non-fatal): {_e}")





                # v390.0.0: Neutronics & Activation Authority 3.0 (certified)
                with st.expander("Neutronics & activation authority (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _n390 = _certs.get('neutronics_activation_v390')
                        if isinstance(_n390, dict):
                            st.json(_n390)
                        else:
                            st.caption("Neutronics & activation authority (v390) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Neutronics & activation authority unavailable (non-fatal): {_e}")

                # v392.0.0: Neutronics Shield Attenuation Authority (certified)
                with st.expander("Neutronics shield attenuation (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _n392 = _certs.get('neutronics_shield_attenuation_v392')
                        if isinstance(_n392, dict):
                            st.json(_n392)
                        else:
                            st.caption("Neutronics shield attenuation (v392) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Neutronics shield attenuation unavailable (non-fatal): {_e}")

                # v391.0.0: Availability 2.0 — Reliability Envelope Authority (certified)
                with st.expander("Availability & reliability envelope (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _a391 = _certs.get('availability_reliability_v391')
                        if isinstance(_a391, dict):
                            st.json(_a391)
                        else:
                            st.caption("Availability reliability envelope (v391) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Availability reliability envelope unavailable (non-fatal): {_e}")

        except _SysPrecheckBlocksSolve:
            st.warning(
                "Full Systems solve skipped: **precheck is infeasible under Reactor intent**. "
                "Use Seeded Recovery / assistant proposals to regain feasibility, or switch Design Intent "
                "to **Experimental Device** for exploratory solves.",
            )
            try:
                st.session_state['systems_last_solve_blocked_reason'] = 'precheck_infeasible_reactor'
            except Exception:
                pass
        except Exception as e:
            st.error(f"Systems solver error: {e}")
            try:
                _alog_exc('Systems', 'RunSystemsSolveException', e)
            except Exception:
                pass

    # ---------------------------------------------------------------------
    # v374.2+ render contract: if there is a cached Systems solution, ALWAYS
    # render Key results + post-run expanders from cache (no compute here).
    # This avoids the "results disappeared"symptom on rerun.
    # ---------------------------------------------------------------------
    if not run:
        try:
            _art_cached = st.session_state.get('systems_last_solution') or st.session_state.get('systems_last_solve_artifact')
            if isinstance(_art_cached, dict):
                _out_cached = _art_cached.get('outputs', {}) if isinstance(_art_cached.get('outputs', {}), dict) else {}
                _cons_cached = _sys_extract_constraints(_art_cached)

                st.markdown("### Key results")
                kcols = st.columns(4)
                def _k(metric, key, fmt="{:.3g}"):
                    v = float(_out_cached.get(key, float("nan")))
                    with metric:
                        st.metric(key, fmt.format(v) if v==v else "NaN")
                _k(kcols[0], "Q_DT_eqv", "{:.3g}")
                _k(kcols[1], "H98", "{:.3g}")
                _k(kcols[2], "P_e_net_MW", "{:.3g}")
                _k(kcols[3], "q_div_MW_m2", "{:.3g}")

                with st.expander("Constraints & margins (systems mode)", expanded=False):
                    rows_c = []
                    for c in _cons_cached:
                        try:
                            margin = float(getattr(c, "margin"))
                        except Exception:
                            margin = float("nan")
                        rows_c.append({
                            "constraint": c.name,
                            "sense": c.sense,
                            "value": c.value,
                            "limit": c.limit,
                            "units": c.units,
                            "passed": bool(c.passed),
                            "margin_frac": margin,
                            "severity": getattr(c, "severity", "hard"),
                            "note": c.note,
                        })
                    st.dataframe(pd.DataFrame(rows_c), use_container_width=True)

                with st.expander("Plots (radial build + power balance)", expanded=False):
                    try:
                        import tempfile, os
                        tmpdir = tempfile.mkdtemp(prefix="shams_systems_")
                        rb = os.path.join(tmpdir, "radial_build.png")
                        plot_radial_build_from_artifact(_art_cached, rb)
                        st.image(rb, caption="Radial build (proxy)", use_container_width=True)
                    except Exception as e:
                        st.warning(f"Radial build plot unavailable: {e}")
                    try:
                        from shams_io.sankey import build_power_balance_sankey
                        import plotly.graph_objects as go
                        sank = build_power_balance_sankey(_art_cached)
                        fig = go.Figure(data=[go.Sankey(**sank)])
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Sankey unavailable: {e}")

                with st.expander("Detailed Systems Diagnostics (post-run)", expanded=False):
                    try:
                        _sys_render_compact_cockpit()
                    except Exception:
                        st.caption("Compact cockpit unavailable (non-fatal).")
                    try:
                        _sys_render_verdict_bar(_art_cached, constraints=_cons_cached)
                        _sys_render_causal_chain(
                            _art_cached,
                            constraints=_cons_cached,
                            expert=st.session_state.get("systems_expert_view", False),
                        )
                        _sys_render_constraint_cards(_art_cached, constraints=_cons_cached)
                    except Exception:
                        st.caption("Detailed diagnostics unavailable (non-fatal).")

                with st.expander("Exhaust & Divertor Authority (certified)", expanded=False):
                    try:
                        _ea = {
                            "lambda_q_mm_raw": float(_out_cached.get("lambda_q_mm_raw", float("nan"))),
                            "lambda_q_mm_used": float(_out_cached.get("lambda_q_mm", float("nan"))),
                            "flux_expansion_raw": float(_out_cached.get("flux_expansion_raw", float("nan"))),
                            "flux_expansion_used": float(_out_cached.get("flux_expansion", float("nan"))),
                            "n_strike_points_raw": int(_out_cached.get("n_strike_points_raw", _out_cached.get("n_strike_points", 2)) or 2),
                            "n_strike_points_used": int(_out_cached.get("n_strike_points", 2) or 2),
                            "f_wet_raw": float(_out_cached.get("f_wet_raw", float("nan"))),
                            "f_wet_used": float(_out_cached.get("f_wet_divertor", float("nan"))),
                            "A_wet_m2": float(_out_cached.get("A_wet_m2", float("nan"))),
                            "q_div_MW_m2": float(_out_cached.get("q_div_MW_m2", float("nan"))),
                            "q_div_max_MW_m2": float(_out_cached.get("q_div_max_MW_m2", float("nan"))),
                            "q_div_unit_suspect": float(_out_cached.get("q_div_unit_suspect", 0.0)),
                            "contract_sha256": str(_out_cached.get("exhaust_authority_contract_sha256", "")),
                        }
                        st.dataframe(pd.DataFrame([_ea]), use_container_width=True)
                        if float(_ea.get("q_div_unit_suspect", 0.0)) >= 0.5:
                            st.warning("q_div magnitude looks unit-suspect (>1e5 MW/m²). This is a flag only; truth is unchanged.")
                    except Exception as _e:
                        st.caption(f"Exhaust authority bundle unavailable (non-fatal): {_e}")

                # v380.0: Impurity radiation partition + detachment requirement (certified)
                with st.expander("Impurity radiation & detachment authority (certified)", expanded=False):
                    try:
                        _cert = None
                        # Prefer cached certifications if present (strict render-from-cache).
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _cert = _certs.get('impurity_radiation_detachment_v380')
                        if not isinstance(_cert, dict):
                            st.info("No cached impurity/detachment certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.impurity_radiation_detachment_certification_v380 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_cert)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_cert)
                    except Exception as _e:
                        st.caption(f"Impurity/detachment authority unavailable (non-fatal): {_e}")

                # v383.0: Plant economics & cost authority 2.0 (certified)
                with st.expander("Plant economics & cost authority (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _pec = _certs.get('plant_economics_v383')
                        if not isinstance(_pec, dict):
                            st.info("No cached plant economics certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.plant_economics_certification_v383 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_pec)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_pec)
                    except Exception as _e:
                        st.caption(f"Plant economics authority unavailable (non-fatal): {_e}")


                # v388.0.0: Cost Authority 3.0 — Industrial Depth (certified)
                with st.expander("Cost authority — industrial depth (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _c388 = _certs.get('cost_authority_v388')
                        if not isinstance(_c388, dict):
                            st.info("No cached cost authority certification yet. Re-run Systems Solve to generate it.")
                        else:
                            from src.certification.cost_authority_certification_v388 import certification_table_rows
                            st.dataframe(pd.DataFrame([certification_table_rows(_c388)]), use_container_width=True)
                            with st.expander("Details", expanded=False):
                                st.json(_c388)
                    except Exception as _e:
                        st.caption(f"Cost authority unavailable (non-fatal): {_e}")

                # v389.0.0: Structural Stress Authority (certified)
                with st.expander("Structural stress authority (certified)", expanded=False):
                    try:
                        _certs = _art_cached.get('certifications', {}) if isinstance(_art_cached.get('certifications', {}), dict) else {}
                        _s389 = _certs.get('structural_stress_v389')
                        if isinstance(_s389, dict):
                            st.json(_s389)
                        else:
                            st.caption("Structural stress authority (v389) not enabled or unavailable in this artifact.")
                    except Exception as _e:
                        st.caption(f"Structural stress authority unavailable (non-fatal): {_e}")


        except Exception:
            pass
