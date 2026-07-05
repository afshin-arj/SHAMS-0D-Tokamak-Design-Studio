"""Deck registry for the NiceGUI UI."""
from __future__ import annotations

from typing import Callable

from ui_nicegui.session import DesignSession
from ui_nicegui.decks.point_designer import render_point_designer
from ui_nicegui.decks.compare import render_compare
from ui_nicegui.decks.control_room import render_control_room
from ui_nicegui.decks.pareto_lab import render_pareto_lab
from ui_nicegui.decks.publication_benchmarks import render_publication_benchmarks
from ui_nicegui.decks.reactor_design_forge import render_reactor_design_forge
from ui_nicegui.decks.scan_lab import render_scan_lab
from ui_nicegui.decks.trade_study_studio import render_trade_study_studio
from ui_nicegui.decks.system_suite import render_system_suite
from ui_nicegui.decks.systems_mode import render_systems_mode
from ui_nicegui.decks.labels import DECK_LABELS
from ui_nicegui.decks._stubs import render_stub_deck

DECK_RENDERERS: dict[str, Callable[[DesignSession], None]] = {
    "Point Designer": render_point_designer,
    "Systems Mode": render_systems_mode,
    "Scan Lab": render_scan_lab,
    "Pareto Lab": render_pareto_lab,
    "Trade Study Studio": render_trade_study_studio,
    "Reactor Design Forge": render_reactor_design_forge,
    "Compare": render_compare,
    "Publication Benchmarks": render_publication_benchmarks,
    "System Suite": render_system_suite,
    "Control Room": render_control_room,
}

# Stub unported decks until Phase 4 batches complete.
for _deck in DECK_LABELS:
    if _deck not in DECK_RENDERERS:
        DECK_RENDERERS[_deck] = lambda session, name=_deck: render_stub_deck(session, name)
