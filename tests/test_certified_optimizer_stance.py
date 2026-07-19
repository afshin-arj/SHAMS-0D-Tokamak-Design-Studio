"""Certified Optimizer Phase 0.2 — stance doc lock tests.

Ensures docs/CERTIFIED_OPTIMIZER.md exists with propose→CCFS contract,
anti-patterns, UI honesty copy, and ObjectiveContract pointer.
Does not claim PROCESS retirement or implement SearchDriver / Opt Lab UI.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANCE = ROOT / "docs" / "CERTIFIED_OPTIMIZER.md"


def test_stance_doc_present() -> None:
    assert STANCE.is_file(), "docs/CERTIFIED_OPTIMIZER.md must exist (Phase 0.2)"


def test_stance_required_honesty_phrases() -> None:
    text = STANCE.read_text(encoding="utf-8")
    lower = text.lower()

    required = [
        "propose",
        "CCFS",
        "ObjectiveContract",
        "objective_contract.v1",
        "Proposed — SHAMS-certified",
        "optimizer-in-truth",
        "no_solution_atlas",
        "Evaluator",
        "hot_ion",
        "search-and-certify",
    ]
    for phrase in required:
        assert phrase in text or phrase.lower() in lower, f"missing required phrase: {phrase}"

    # Section / topic coverage
    for topic in [
        "Propose → CCFS",
        "Anti-patterns",
        "UI honesty",
        "ObjectiveContract",
        "Anti L0-opt",
        "Reviewer checklist",
        "Orthogonality",
    ]:
        assert topic.lower() in lower, f"missing section topic: {topic}"


def test_stance_forbids_overclaim_as_positive_claims() -> None:
    """Forbidden phrases may appear only as negated / warned-against language."""
    text = STANCE.read_text(encoding="utf-8")
    plain = re.sub(r"[*_`\"“”]", "", text).lower()

    # Stance must explicitly teach the honesty rule
    assert "proposed — shams-certified" in plain or "proposed - shams-certified" in plain
    assert "never" in plain and "true minimum" in plain
    assert "forbidden" in plain
    assert "does not claim process retirement" in plain or "do not claim process retirement" in plain

    # Every "true minimum" / "true global optimum" must sit near a ban word
    ban_markers = (
        "never",
        "forbidden",
        "anti-patterns",
        "anti-pattern",
        "do not",
        "does not",
        "not claim",
        "claiming",
        "overclaim",
    )
    for phrase in ("true minimum", "true global optimum", "true global minimum"):
        for m in re.finditer(re.escape(phrase), plain):
            window = plain[max(0, m.start() - 120) : m.end() + 80]
            assert any(b in window for b in ban_markers), (
                f"{phrase!r} without ban context: {window!r}"
            )

    # Unqualified "PROCESS is/has been retired" must not appear
    for m in re.finditer(r"process\s+(?:is|has been)\s+retired", plain):
        window = plain[max(0, m.start() - 64) : m.start()]
        assert any(
            w in window for w in ("never", "do not", "does not", "not claim", "claiming")
        ), f"unqualified retirement claim near: {plain[m.start() - 20 : m.end() + 20]!r}"


def test_readme_and_limitations_link_stance() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CERTIFIED_OPTIMIZER.md" in readme

    limitations = (ROOT / "docs" / "LIMITATIONS.md").read_text(encoding="utf-8")
    assert "CERTIFIED_OPTIMIZER.md" in limitations


def test_roadmap_marks_0_2() -> None:
    roadmap = (ROOT / "docs" / "CERTIFIED_OPTIMIZER_ROADMAP.md").read_text(encoding="utf-8")
    assert "CERTIFIED_OPTIMIZER.md" in roadmap
    # 0.2 marked DONE (table row)
    assert re.search(r"0\.2\s*\|[^|]*\|\s*\*\*DONE\*\*", roadmap) or (
        "**DONE**" in roadmap and "0.2" in roadmap and "stance" in roadmap.lower()
    )
    # 0.3 complete (Phase 0 exit); Top next is Opt Lab entry
    assert "0.3" in roadmap
    assert "l0_opt_guards" in roadmap.lower() or "Anti L0-opt" in roadmap
    assert "1.1" in roadmap


def test_docs_library_and_launchpad_surfaces() -> None:
    from ui_nicegui.lib.control_room_helpers import (
        CERTIFIED_OPTIMIZER_DOC,
        LAUNCHPAD_DECK,
        LAUNCHPAD_PATHS,
        list_docs,
    )
    from ui_nicegui.lib.studio_entry import STUDIO_DOC_LINKS

    assert CERTIFIED_OPTIMIZER_DOC == "CERTIFIED_OPTIMIZER.md"
    docs = list_docs()
    assert CERTIFIED_OPTIMIZER_DOC in docs

    helpers = (ROOT / "ui_nicegui" / "lib" / "control_room_helpers.py").read_text(
        encoding="utf-8"
    )
    assert 'CERTIFIED_OPTIMIZER_DOC = "CERTIFIED_OPTIMIZER.md"' in helpers
    assert "Read certified optimizer stance" in helpers

    titles = [p[0] for p in LAUNCHPAD_PATHS]
    assert "Read certified optimizer stance" in titles
    assert LAUNCHPAD_DECK.get("Read certified optimizer stance") == "Control Room"

    constitution = (
        ROOT / "ui_nicegui" / "decks" / "control_room" / "constitution.py"
    ).read_text(encoding="utf-8")
    assert "CERTIFIED_OPTIMIZER_DOC" in constitution
    assert "CERTIFIED_OPTIMIZER.md" in constitution

    assert any(
        path.endswith("CERTIFIED_OPTIMIZER.md") for _, path in STUDIO_DOC_LINKS
    )
    labels = [label for label, _ in STUDIO_DOC_LINKS]
    assert "Certified Optimizer stance" in labels
    # No version tags in user-facing labels
    for label, _ in STUDIO_DOC_LINKS:
        assert not re.search(r"\bv\d{3}\b", label), f"version tag in label: {label!r}"
