from __future__ import annotations

"""Scan Lab — Canonical questions library (teaching + onboarding).

These are UI-only prompts that load curated scan presets or reveal a
recommended analysis view. They are not tied to any one machine — they
work from the user's current baseline point.
"""

from typing import Any, Dict, List


def build_canonical_questions() -> List[Dict[str, Any]]:
    """Return a small library of canonical Scan Lab questions.

    Each item can optionally reference a golden scan preset label or suggest a view.
    """
    return [
        {
            "question": "Why does increasing R0 help q_div so much?",
            "hint": "Run Ip × R0 cartography and look at dominance boundaries.",
            "suggested_golden_label": "Golden — ITER-like (Ip × R0) — Reactor",
        },
        {
            "question": "Why do compact high-field designs run into stress/HTS cliffs?",
            "hint": "Run Bt × R0 cartography; inspect first-failure order transitions.",
            "suggested_golden_label": "Golden — Compact high-field (Bt × R0) — Reactor",
        },
        {
            "question": "Is this a research machine or a power plant — and where does that difference show up?",
            "hint": "Run the same scan under both intents and inspect the Research-only feasible overlay.",
            "suggested_golden_label": "Golden — Research extreme (Ip × fG) — Intent split",
        },
        {
            "question": "Which knob helps most locally, without changing the design philosophy?",
            "hint": "Enable vector-field overlay and read arrows as local safety direction.",
            "suggested_golden_label": None,
        },
        {
            "question": "Is this feasible point robust or knife-edge?",
            "hint": "Use robustness labels and uncertainty stress-test around a picked cell.",
            "suggested_golden_label": None,
        },
    ]
