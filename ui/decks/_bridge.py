"""Shared namespace-bridge helper for deck modules (UI redesign part 3).

Each deck module (ui/decks/*.py) is extracted from the monolithic ui/app.py via
a namespace bridge: at render time the deck copies app.py's module-level names
into its own module globals so that bare names in the moved body resolve exactly
as they did inline, and so Path(__file__).resolve().parent.parent / .parents[1]
still resolve to the SHAMS-0D root (app.py's location) rather than ui/decks/.

This is temporary tech debt. The long-term cleanup is to replace the bridge with
explicit per-deck imports of the app.py names each deck actually uses, plus a
shared ROOT constant for path computations. That rewrite requires per-deck AST
name analysis and textual path edits across many sites, and is deferred to avoid
regression risk; the bridge is load-bearing (bare-name resolution + __file__ path
coupling) and currently works and is tested. Centralising it here is a safe first
step: single-source, consistent behaviour, and one place to evolve the bridge.
"""
from __future__ import annotations


def bridge_deck(app_module, target_globals) -> None:
    """Copy app.py's module-level names into the deck's module globals.

    Called as `bridge_deck(_app_module, globals())` at the top of each
    render_X function. Dunder names are skipped. __file__ is set to app.py's
    path so Path(__file__) computations resolve to the SHAMS-0D root.
    """
    for _k, _v in vars(app_module).items():
        if not _k.startswith("__"):
            target_globals[_k] = _v
    target_globals["__file__"] = app_module.__file__
