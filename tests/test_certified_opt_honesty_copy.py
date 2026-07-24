"""Certified Optimizer Phase 1.3 — UI honesty copy lock tests.

Scanned decks (Opt Lab, Systems Mode, Pareto Lab, Control Room Certified Search)
must carry Proposed — SHAMS-certified, VERIFIED/REJECTED + atlas language,
forbid positive true-minimum / global-optimum claims, and avoid vNNN labels
in user-facing honesty strings. L0 untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_VERSION_TAG = re.compile(r"\bv\d{3}\b", re.IGNORECASE)

_BAN_MARKERS = (
    "never",
    "not an",
    "not a",
    "forbidden",
    "do not",
    "does not",
    "don't",
    "must not",
    "without claiming",
    "anti-pattern",
    "warning",
)


def _assert_no_positive_forbidden(blob: str, *, where: str) -> None:
    from ui_nicegui.lib.certified_opt_honesty import FORBIDDEN_POSITIVE_CLAIMS

    plain = re.sub(r"[*_`\"“”]", "", blob).lower()
    for phrase in FORBIDDEN_POSITIVE_CLAIMS:
        for m in re.finditer(re.escape(phrase.lower()), plain):
            window = plain[max(0, m.start() - 100) : m.end() + 60]
            assert any(b in window for b in _BAN_MARKERS), (
                f"{where}: positive claim {phrase!r} without ban context: {window!r}"
            )


def test_honesty_module_required_phrases() -> None:
    from ui_nicegui.lib.certified_opt_honesty import (
        PROPOSED_CERTIFIED,
        REQUIRED_PHRASES,
        all_honesty_user_facing_texts,
        honesty_banner_for,
    )

    blob = " ".join(all_honesty_user_facing_texts())
    for phrase in REQUIRED_PHRASES:
        assert phrase in blob or phrase.lower() in blob.lower(), phrase

    assert PROPOSED_CERTIFIED in honesty_banner_for("systems_mode")
    assert PROPOSED_CERTIFIED in honesty_banner_for("pareto_lab")
    assert PROPOSED_CERTIFIED in honesty_banner_for("certified_search")
    assert "VERIFIED" in honesty_banner_for("systems_mode")
    assert "REJECTED" in honesty_banner_for("pareto_lab")
    assert "atlas" in honesty_banner_for("certified_search").lower()


def test_honesty_strings_unversioned() -> None:
    from ui_nicegui.lib.certified_opt_honesty import all_honesty_user_facing_texts

    for text in all_honesty_user_facing_texts():
        assert not _VERSION_TAG.search(text), f"version tag in honesty string: {text!r}"


def test_scanned_decks_contain_honesty() -> None:
    from ui_nicegui.lib.certified_opt_honesty import (
        PROPOSED_CERTIFIED,
        scan_file_texts,
    )

    files = dict(scan_file_texts(ROOT))
    required_surfaces = [
        "ui_nicegui/decks/systems_mode/__init__.py",
        "ui_nicegui/decks/pareto_lab/__init__.py",
        "ui_nicegui/decks/control_room/certified_search.py",
        "ui_nicegui/lib/systems_labels.py",
        "ui_nicegui/lib/pareto_labels.py",
        "ui/decks/systems_mode.py",
        "ui/decks/pareto_lab.py",
        "ui/decks/control_room.py",
        "ui/decks/opt_lab.py",
    ]
    for rel in required_surfaces:
        assert rel in files, f"missing scan target: {rel}"
        text = files[rel]
        assert (
            "certified_opt_honesty" in text
            or PROPOSED_CERTIFIED in text
            or "Proposed — SHAMS-certified" in text
        ), rel
        assert "Proposed — SHAMS-certified" in text or "PROPOSED_CERTIFIED" in text or (
            "render_certified_opt_honesty_banner" in text
            or "SYSTEMS_MODE_HONESTY" in text
            or "PARETO_LAB_HONESTY" in text
            or "CERTIFIED_SEARCH_HONESTY" in text
            or "OPT_LAB_HONESTY" in text
        ), rel


def test_scanned_decks_forbid_positive_true_minimum() -> None:
    from ui_nicegui.lib.certified_opt_honesty import scan_file_texts

    # Skip the inventory module itself (it *defines* the forbidden phrases).
    skip = {"ui_nicegui/lib/certified_opt_honesty.py"}
    for rel, text in scan_file_texts(ROOT):
        if rel in skip:
            continue
        _assert_no_positive_forbidden(text, where=rel)


def test_certified_search_results_honesty_labels() -> None:
    nice = (
        ROOT / "ui_nicegui" / "decks" / "control_room" / "certified_search.py"
    ).read_text(encoding="utf-8")
    assert "BEST_PROPOSED_LABEL" in nice
    assert "PASS_KPI_LABEL" in nice
    assert "FAIL_KPI_LABEL" in nice
    assert "format_pass_fail_counts" in nice
    assert "VERIFIED_KPI_LABEL" not in nice
    assert "format_verified_rejected_counts" not in nice
    assert "Best PASS candidate" not in nice
    assert "not CCFS VERIFIED" in nice

    streamlit = (ROOT / "ui" / "decks" / "control_room.py").read_text(encoding="utf-8")
    # Certified Search block must share honesty labels (Streamlit parity).
    assert "BEST_PROPOSED_LABEL" in streamlit
    assert "PASS_KPI_LABEL" in streamlit
    assert "FAIL_KPI_LABEL" in streamlit
    assert "format_pass_fail_counts" in streamlit
    assert "CERTIFIED_SEARCH_FAIL_ATLAS_NOTE" in streamlit
    assert "Best PASS candidate" not in streamlit
    assert "PASS found:" not in streamlit


def test_counts_helper() -> None:
    from ui_nicegui.lib.certified_opt_honesty import (
        counts_from_pass_fail_rows,
        format_pass_fail_counts,
        format_verified_rejected_counts,
    )

    n_pass, n_fail = counts_from_pass_fail_rows(
        [{"verdict": "PASS"}, {"verdict": "FAIL"}, {"verdict": "PASS"}]
    )
    assert (n_pass, n_fail) == (2, 1)
    screening = format_pass_fail_counts(n_pass=2, n_fail=1, n_candidates=3)
    assert "L0 PASS=2" in screening
    assert "FAIL=1" in screening
    assert "not CCFS VERIFIED" in screening
    assert "VERIFIED=" not in screening
    assert "Proposed — SHAMS-certified" in screening
    assert not _VERSION_TAG.search(screening)

    # CCFS formatter remains for true VERIFIED paths.
    ccfs = format_verified_rejected_counts(n_verified=2, n_rejected=1, n_candidates=3)
    assert "VERIFIED=2" in ccfs
    assert "REJECTED=1" in ccfs


def test_systems_mode_post_solve_labels_unversioned() -> None:
    src = (
        ROOT / "ui_nicegui" / "decks" / "systems_mode" / "post_solve_authority_ui.py"
    ).read_text(encoding="utf-8")
    # User-facing expansion titles must not carry vNNN.
    for line in src.splitlines():
        stripped = line.strip()
        if "ui.expansion(" in stripped or 'ui.label("' in stripped:
            assert not _VERSION_TAG.search(stripped), stripped


def test_roadmap_marks_1_3() -> None:
    roadmap = (ROOT / "docs" / "CERTIFIED_OPTIMIZER_ROADMAP.md").read_text(encoding="utf-8")
    assert "1.3" in roadmap
    assert "UI honesty" in roadmap
    # Written to pass once roadmap is updated at ship.
    assert re.search(r"1\.3\s*\|[^|]*\|\s*\*\*DONE\*\*", roadmap) or (
        "**DONE**" in roadmap and "UI honesty copy" in roadmap
    )
