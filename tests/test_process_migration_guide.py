"""Independence Phase 3.1 — PROCESS→SHAMS migration guide lock.

Ensures the community migration doc exists with required sections.
Does not invent PROCESS MFILE numbers or claim PROCESS retirement.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"


def test_migration_guide_file_present() -> None:
    assert GUIDE.is_file(), "docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md must exist (Phase 3.1)"


def test_migration_guide_required_sections() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    lower = text.lower()

    # Title / entry
    assert "PROCESS → SHAMS Migration Guide" in text or "PROCESS -> SHAMS Migration Guide" in text

    # Required topic coverage (Done when)
    required_phrases = [
        "IN.DAT",
        "PointInputs",
        "MFILE",
        "artifact",
        "constraint",
        "VERSION",
        "SHA-256",
        "CCFS",
        "METHOD-ONLY",
        "propose",
    ]
    for phrase in required_phrases:
        assert phrase in text or phrase.lower() in lower, f"missing required phrase: {phrase}"

    # Section anchors (headings)
    for heading in [
        "IN.DAT concepts",
        "MFILE",
        "Constraint",
        "CCFS",
        "cite VERSION",
        "METHOD-ONLY",
    ]:
        assert heading.lower() in lower, f"missing section topic: {heading}"


def test_migration_guide_anti_overclaim() -> None:
    import re

    text = GUIDE.read_text(encoding="utf-8")
    # Strip markdown emphasis so "**does not** claim" matches cleanly
    plain = re.sub(r"[*_`]", "", text).lower()
    assert "invent" in plain and "mfile" in plain
    assert "does not claim process retirement" in plain or "do not claim process retirement" in plain
    for m in re.finditer(r"process\s+(?:is|has been)\s+retired", plain):
        start = max(0, m.start() - 48)
        window = plain[start : m.start()]
        assert ("does not" in window) or ("do not" in window) or ("not claim" in window), (
            f"unqualified retirement claim near: {plain[m.start()-20:m.end()+20]!r}"
        )


def test_crosswalk_and_readme_point_to_guide() -> None:
    crosswalk = (ROOT / "docs" / "PROCESS_CROSSWALK.md").read_text(encoding="utf-8")
    assert "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md" in crosswalk

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md" in readme


def test_roadmap_marks_phase_3_1() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    # After ship: DONE marker for 3.1
    assert "3.1" in roadmap
    assert "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md" in roadmap or "migration guide" in roadmap.lower()
    assert "DONE" in roadmap and "3.1" in roadmap


def test_control_room_surfaces_migration_guide_constant() -> None:
    helpers = (
        ROOT / "ui_nicegui" / "lib" / "control_room_helpers.py"
    ).read_text(encoding="utf-8")
    assert 'MIGRATION_GUIDE_DOC = "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"' in helpers
    assert "Migrate a PROCESS study to SHAMS" in helpers
    constitution = (
        ROOT / "ui_nicegui" / "decks" / "control_room" / "constitution.py"
    ).read_text(encoding="utf-8")
    assert "MIGRATION_GUIDE_DOC" in constitution
