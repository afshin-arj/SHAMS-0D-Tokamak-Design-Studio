"""Batch 10: Control Room wiring."""
from __future__ import annotations

from ui_nicegui.decks.control_room import render_control_room
from ui_nicegui.lib.control_room_helpers import (
    CR_SECTIONS,
    governance_summary,
    hygiene_scan,
    interop_check,
    list_docs,
    read_version,
    run_contract_validator,
)


def test_control_room_renderer_import() -> None:
    assert callable(render_control_room)


def test_cr_sections_defined() -> None:
    assert "Orientation" in CR_SECTIONS
    assert "Diagnostics" in CR_SECTIONS


def test_read_version() -> None:
    ver = read_version()
    assert ver and ver != "unknown"


def test_list_docs_nonempty() -> None:
    docs = list_docs()
    assert len(docs) >= 1


def test_hygiene_scan_shape() -> None:
    scan = hygiene_scan()
    assert "ok" in scan
    assert "packaging_ok" in scan
    assert isinstance(scan.get("hits"), list)
    assert isinstance(scan.get("dev_cache_hits"), list)


def test_interop_check() -> None:
    from ui_nicegui.session import DesignSession

    rep = interop_check(DesignSession())
    assert isinstance(rep, dict)
    assert "checks" in rep


def test_contract_validator_smoke() -> None:
    from ui_nicegui.session import DesignSession

    rep = run_contract_validator(DesignSession())
    assert isinstance(rep, dict)
    assert "ok" in rep
    assert "nicegui_ok" in rep
    assert rep.get("nicegui_ok") is True


def test_governance_summary() -> None:
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    summary = governance_summary(s)
    assert summary["version"] != "unknown"
    assert summary["active_deck"] == "Point Designer"
