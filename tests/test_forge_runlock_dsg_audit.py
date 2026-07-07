"""Forge run-lock, DSG edge kind, and audit pack follow-ups."""
from __future__ import annotations

from ui_nicegui.lib.deck_dsg_hooks import deck_edge_kind_for
from ui_nicegui.lib.forge_helpers import FORGE_RUNLOCK_OWNER
from ui_nicegui.lib.run_lock import acquire, global_status, release, status
from ui_nicegui.session import DesignSession


def test_forge_dsg_edge_kind() -> None:
    assert deck_edge_kind_for("Reactor Design Forge") == "forge"


def test_run_lock_blocks_cross_owner() -> None:
    assert acquire("Point Designer: test", "PointDesigner") is True
    locked, task, holder = global_status()
    assert locked is True
    assert holder == "PointDesigner"
    locked_pd, _, is_pd = status(FORGE_RUNLOCK_OWNER)
    assert locked_pd is True
    assert is_pd is False
    assert acquire("Forge: test", FORGE_RUNLOCK_OWNER) is False
    release("PointDesigner")
    assert acquire("Forge: test", FORGE_RUNLOCK_OWNER) is True
    release(FORGE_RUNLOCK_OWNER)


def test_forge_runlock_owner_constant() -> None:
    s = DesignSession()
    assert FORGE_RUNLOCK_OWNER == "ReactorDesignForge"
    assert s.forge_audit_pack_name.endswith(".zip")
