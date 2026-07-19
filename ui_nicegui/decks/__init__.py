"""Deck registry for the NiceGUI UI.

Heavy deck modules are imported on first switch (module-level cache), matching
System Suite's overlay cache pattern — keeps Helm remounts snappy without a
keep-alive rewrite.
"""
from __future__ import annotations

import importlib
from typing import Callable

from ui_nicegui.session import DesignSession
from ui_nicegui.decks.labels import DECK_LABELS

_RENDERER_CACHE: dict[str, Callable[[DesignSession], None]] = {}

# (module_path, attribute) — resolved once per process.
_DECK_SPECS: dict[str, tuple[str, str]] = {
    "Point Designer": ("ui_nicegui.decks.point_designer", "render_point_designer"),
    "Systems Mode": ("ui_nicegui.decks.systems_mode", "render_systems_mode"),
    "Opt Lab": ("ui_nicegui.decks.opt_lab", "render_opt_lab"),
    "Scan Lab": ("ui_nicegui.decks.scan_lab", "render_scan_lab"),
    "Pareto Lab": ("ui_nicegui.decks.pareto_lab", "render_pareto_lab"),
    "Trade Study Studio": ("ui_nicegui.decks.trade_study_studio", "render_trade_study_studio"),
    "Reactor Design Forge": ("ui_nicegui.decks.reactor_design_forge", "render_reactor_design_forge"),
    "Compare": ("ui_nicegui.decks.compare", "render_compare"),
    "Publication Benchmarks": ("ui_nicegui.decks.publication_benchmarks", "render_publication_benchmarks"),
    "System Suite": ("ui_nicegui.decks.system_suite", "render_system_suite"),
    "Control Room": ("ui_nicegui.decks.control_room", "render_control_room"),
}


def _resolve_renderer(name: str) -> Callable[[DesignSession], None]:
    cached = _RENDERER_CACHE.get(name)
    if cached is not None:
        return cached
    spec = _DECK_SPECS.get(name)
    if spec is None:
        from ui_nicegui.decks._stubs import render_stub_deck

        def _stub(session: DesignSession, deck: str = name) -> None:
            render_stub_deck(session, deck)

        _RENDERER_CACHE[name] = _stub
        return _stub
    mod_path, attr = spec
    mod = importlib.import_module(mod_path)
    fn = getattr(mod, attr)
    _RENDERER_CACHE[name] = fn
    return fn


def _lazy_render(name: str) -> Callable[[DesignSession], None]:
    def _render(session: DesignSession) -> None:
        _resolve_renderer(name)(session)

    return _render


DECK_RENDERERS: dict[str, Callable[[DesignSession], None]] = {
    name: _lazy_render(name) for name in _DECK_SPECS
}

# Stub unported decks until Phase 4 batches complete.
for _deck in DECK_LABELS:
    if _deck not in DECK_RENDERERS:
        DECK_RENDERERS[_deck] = _lazy_render(_deck)
