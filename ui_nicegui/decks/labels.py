"""Deck label registry — shared without importing deck renderers (avoids circular imports).

Order follows the fusion-expert implementation workflow (see ui_nicegui/lib/deck_workflow.py).
"""

DECK_LABELS: list[str] = [
    "Point Designer",
    "Scan Lab",
    "Systems Mode",
    "Compare",
    "Pareto Lab",
    "Trade Study Studio",
    "Reactor Design Forge",
    "Publication Benchmarks",
    "System Suite",
    "Control Room",
]
