"""Central UI iconography and mode scope cards.

Policy:
- For Streamlit, do NOT use icon=":shortcode:" or icon="".
- Prefer prefixing labels/headers with emojis (robust across Streamlit versions).
- Keep semantics professional and sparse.

© 2026 Afshin Arjhangmehr
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import streamlit as st

ICONS: Dict[str, str] = {
    # top-level modes
    "point": "🧭",
    "systems": "🧠",
    "scan": "🗺️",
    "pareto": "📈",
    "forge": "⚒️",
    "suite": "🧰",
    "compare": "🆚",
    "bench": "📚",
    "control": "🎛️",

    # common sub-panels
    "diag": "🩺",
    "registry": "📎",
    "atlas": "📚",
    "workbench": "📈",
    "bundle": "📦",
    "dossier": "🧾",
    "verify": "✅",
    "export": "📤",

    # physics domains
    "plasma": "🔥",
    "conf": "🌀",
    "hcd": "⚡",
    "bootstrap": "🧬",
    "exhaust": "💨",
    "rad": "🌈",
    "imp": "🧪",
    "neut": "☢️",
    "blanket": "🧱",
    "mag": "🧲",
    "struct": "🏗️",
    "bop": "🏭",
    "cost": "💰",
    "safety": "🛡️",
    "ctrl": "🎛️",
    "info": "ℹ️",
    "warn": "⚠️",
    "ok": "✅",
}

def label(key: str, text: str) -> str:
    ico = ICONS.get(key, "")
    return f"{ico} {text}".strip()

# Mode scope: what it does / does not do (constitutional summaries)
MODE_SCOPE: Dict[str, Dict[str, List[str]]] = {
    "point": {
        "does": [
            "Runs the frozen deterministic evaluator for a single design point.",
            "Reports PASS/FAIL, margins, dominant failure mechanism, and key outputs.",
            "Surfaces which physics blocks were executed (transparency registry).",
        ],
        "does_not": [
            "Does not optimize, iterate, or negotiate constraints.",
            "Does not hide infeasibility via solver convergence or penalty smoothing.",
            "Does not rank designs as ‘best’.",
        ],
    },
    "systems": {
        "does": [
            "Performs feasibility-first system-level negotiation as an EXPLANATION layer.",
            "Organizes constraint ledgers into mechanism-level narratives (why feasibility breaks).",
            "Provides deterministic ‘what would need to change’ guidance without modifying truth.",
        ],
        "does_not": [
            "Does not change the frozen evaluator or alter physics truth.",
            "Does not perform any internal root-finding or Newton iterations.",
            "Does not relax hard constraints implicitly.",
        ],
    },
    "scan": {
        "does": [
            "Runs deterministic batch scans across design families and parameter grids.",
            "Maps feasible/empty/fragile regions and dominant mechanisms over the space.",
            "Exports audit artifacts for each sampled point.",
        ],
        "does_not": [
            "Does not search adaptively inside truth (no hidden optimizer).",
            "Does not smooth constraints to fill empty regions.",
            "Does not claim ‘global optima’.",
        ],
    },
    "pareto": {
        "does": [
            "Acts as the interface to firewalled external optimization clients (ExtOpt).",
            "Defines problem specs, runspecs, and exports deterministic evidence bundles.",
            "Visualizes feasibility-first results and optimizer traces (when provided).",
        ],
        "does_not": [
            "Does not contain an internal optimizer inside SHAMS truth.",
            "Does not let optimizers modify the evaluator or constraints.",
            "Does not treat ‘objective improvement’ as a substitute for feasibility.",
        ],
    },
    "forge": {
        "does": [
            "Supports reactor-intent concept assembly workflows (design family narratives).",
            "Emits structured concept definitions for evaluation and external search.",
            "Focuses on completeness of a reactor concept (inputs, assumptions, intent).",
        ],
        "does_not": [
            "Does not guarantee feasibility or compensate missing physics with solvers.",
            "Does not auto-tune to meet constraints silently.",
            "Does not replace the truth evaluator; it feeds it.",
        ],
    },
    "suite": {
        "does": [
            "Provides cross-cutting diagnostics and derived reports (e.g., Plant Dossier).",
            "Exposes transparency registries, capability matrices, and verification utilities.",
            "Exports audit-ready dossiers and summaries derived from artifacts.",
        ],
        "does_not": [
            "Does not change truth or reclassify failed points as feasible.",
            "Does not introduce hidden state that affects evaluator outcomes.",
            "Does not add iterative balancing loops.",
        ],
    },
    "compare": {
        "does": [
            "Compares runs, artifacts, and ledgers to isolate why designs differ.",
            "Highlights constraint-margin deltas and mechanism changes.",
            "Supports reviewer-style side-by-side evaluation.",
        ],
        "does_not": [
            "Does not merge runs into a single ‘best’ result.",
            "Does not average away constraint violations.",
            "Does not infer causality without showing the traced mechanism/constraint changes.",
        ],
    },
    "bench": {
        "does": [
            "Hosts constitutional benchmarks and parity tracking (e.g., PROCESS parity atlas).",
            "Allows user-supplied reference comparisons with explicit deltas.",
            "Acts as regression safety for the evaluator and UI wiring.",
        ],
        "does_not": [
            "Does not assume external reference values are authoritative without provenance.",
            "Does not auto-fit SHAMS to match other codes by tuning hidden knobs.",
            "Does not import/run external tools implicitly.",
        ],
    },
    "control": {
        "does": [
            "Provides governance/operations utilities (run manifests, gatechecks, status).",
            "Surfaces toolchain health and deterministic reproducibility checks.",
            "Centralizes ‘review-room’ readiness indicators.",
        ],
        "does_not": [
            "Does not change model outputs or evaluator behavior.",
            "Does not run background tasks that mutate artifacts.",
            "Does not bypass hygiene/verification requirements.",
        ],
    },
}

def render_mode_scope(mode_key: str):
    """Render a compact scope card: what it does / does not do."""
    s = MODE_SCOPE.get(mode_key)
    if not s:
        return
    with st.expander(label("info", "What this mode does / does not do"), expanded=False):
        st.markdown("**What this mode does**")
        st.markdown("\n".join([f"- {x}" for x in s.get("does", [])]))
        st.markdown("**What this mode does not do**")
        st.markdown("\n".join([f"- {x}" for x in s.get("does_not", [])]))
