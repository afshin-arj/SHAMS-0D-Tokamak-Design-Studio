"""Plain-language Compare deck labels — workflow tabs for fusion experts."""

from __future__ import annotations

COMPARE_TABS = [
    "1 · Load A & B",
    "2 · Performance",
    "3 · Constraints",
    "4 · Inputs & Structure",
    "5 · Export",
]

_LEGACY_TAB_MAP = {
    "Compare sources": "1 · Load A & B",
    "Key metrics": "2 · Performance",
    "Constraints (worst margins first)": "3 · Constraints",
}

TAB_HELP = {
    "1 · Load A & B": (
        "Load two run artifacts into slots A (baseline) and B (variant). "
        "Use Point Designer handoff, session slots, or JSON upload."
    ),
    "2 · Performance": (
        "Side-by-side KPIs and output deltas — Q, fusion power, net electric, "
        "βN, q95, engineering proxies. Largest changes highlighted first."
    ),
    "3 · Constraints": (
        "Worst constraint margins per run, margin regressions, and new failures in B. "
        "Use this to see *why* feasibility changed."
    ),
    "4 · Inputs & Structure": (
        "Which PointInputs changed, embedded scenario_delta (if present), "
        "and structural diffs (constraints added/removed, model cards)."
    ),
    "5 · Export": (
        "Download markdown or JSON comparison bundles for audit, review, or handoff."
    ),
}

DECK_SUBTITLE = (
    "Side-by-side artifact comparison on the frozen evaluator — isolate performance "
    "deltas, constraint-margin shifts, and input changes. Reviewer-style, not ranking."
)

DEFAULT_TAB = "1 · Load A & B"

DECISION_STATES = [
    "Load baseline vs variant",
    "See performance deltas (Q, Pfus, …)",
    "Understand constraint / feasibility change",
    "Audit inputs and schema changes",
    "Export for reviewer",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Load A & B",
    DECISION_STATES[1]: "2 · Performance",
    DECISION_STATES[2]: "3 · Constraints",
    DECISION_STATES[3]: "4 · Inputs & Structure",
    DECISION_STATES[4]: "5 · Export",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: (
        "**Slot A** is usually baseline; **Slot B** is the scenario or variant. "
        "Send runs from Point Designer Export Bay or System Suite Apply without downloading JSON."
    ),
    DECISION_STATES[1]: (
        "Key metrics use canonical output names with aliases (Q ↔ Q_DT_eqv, Pfus ↔ P_fus). "
        "Toggle **All numeric outputs** for a full delta table sorted by |Δ|."
    ),
    DECISION_STATES[2]: (
        "**Residual** is constraint margin (positive = headroom). "
        "New failures in B are constraints that passed in A but fail in B."
    ),
    DECISION_STATES[3]: (
        "Input diffs show explicit PointInputs changes. "
        "Structural diff reports constraint set and model-card changes without numeric tolerance."
    ),
    DECISION_STATES[4]: (
        "Markdown export is human-readable; JSON bundle preserves machine-readable diffs for CI or Control Room."
    ),
}

METRIC_DISPLAY = {
    "Q": "Gain Q",
    "Q_DT_eqv": "Gain Q (DT-equiv)",
    "Pfus_total_MW": "Fusion power (MW)",
    "P_fus_MW": "Fusion power (MW)",
    "P_e_net_MW": "Net electric (MW)",
    "betaN": "Normalized beta",
    "q95": "Safety factor q95",
    "Bpeak_TF_T": "Peak TF field (T)",
    "B_peak_T": "Peak field (T)",
    "q_div_MW_m2": "Divertor heat flux (MW/m²)",
    "neutron_wall_load_MW_m2": "Neutron wall load (MW/m²)",
    "COE_proxy_USD_per_MWh": "COE proxy (USD/MWh)",
}


def normalize_compare_tab(tab: str | None) -> str:
    if not tab:
        return DEFAULT_TAB
    t = str(tab).strip()
    if t in COMPARE_TABS:
        return t
    return _LEGACY_TAB_MAP.get(t, DEFAULT_TAB)


def teaching_banner(session) -> str:
    if not getattr(session, "cmp_teaching_mode", True):
        return ""
    state = getattr(session, "cmp_decision_state", "") or DECISION_STATES[0]
    if state not in TEACHING_HINTS:
        return ""
    return TEACHING_HINTS[state]
