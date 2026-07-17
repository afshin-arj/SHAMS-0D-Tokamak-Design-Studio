"""Independence Phase 3.2 — Zenodo / CITATION / software-paper packaging lock.

Ensures the archival metadata and APPROVED-release-path docs exist and stay
honest. Does not claim APPROVED status, PROCESS retirement, or a minted DOI.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "RELEASE_ARCHIVAL_CHECKLIST.md"
PITCH = ROOT / "docs" / "SOFTWARE_PAPER_PITCH.md"
ZENODO = ROOT / ".zenodo.json"


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_zenodo_metadata_present_and_aligned() -> None:
    assert ZENODO.is_file(), ".zenodo.json must exist (Phase 3.2)"
    meta = json.loads(ZENODO.read_text(encoding="utf-8"))
    assert meta["upload_type"] == "software"
    assert meta["license"] == "Apache-2.0"
    assert meta["version"] == _version(), ".zenodo.json version must match VERSION"
    assert meta["creators"], "creators required for Zenodo deposit"
    assert "SHAMS" in meta["title"]
    # Honesty: description must not overclaim
    desc = meta["description"].lower()
    assert "method-only" in desc
    assert "does not claim process retirement" in desc


def test_citation_cff_packaging_fields() -> None:
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "repository-code:" in cff
    assert "license: \"Apache-2.0\"" in cff or "license: Apache-2.0" in cff
    version_line = next((ln for ln in cff.splitlines() if ln.startswith("version:")), "")
    assert _version() in version_line, "CITATION.cff version must match VERSION"
    # ORCID must not be an invented value; allowed states: absent or commented placeholder
    for ln in cff.splitlines():
        stripped = ln.strip()
        if stripped.startswith("orcid:"):
            raise AssertionError(
                "uncommented orcid field present — only add a real ORCID iD, never a placeholder value"
            )


def test_release_archival_checklist_sections() -> None:
    assert CHECKLIST.is_file(), "docs/RELEASE_ARCHIVAL_CHECKLIST.md must exist (Phase 3.2)"
    text = CHECKLIST.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in [
        "zenodo",
        "doi",
        "conditional",
        "approved",
        "sha-256",
        "version",
        "citation.cff",
        ".zenodo.json",
        "tag",
        "parity dossier",
    ]:
        assert phrase in lower, f"missing required topic: {phrase}"
    # APPROVED path must be gated, with all Phase 1.4 waivers enumerated
    for gate in ["W-INSTALL", "W-PYTEST-SCOPE", "W-UI-SELFTEST", "W-REVIEWER-PACK", "W-PRODUCT-QA", "W-AUTH-SPOT", "W-NO-TAG"]:
        assert gate in text, f"APPROVED path must clear waiver {gate}"
    assert "CONDITIONAL → APPROVED" in text or "CONDITIONAL -> APPROVED" in text


def test_software_paper_pitch_sections() -> None:
    assert PITCH.is_file(), "docs/SOFTWARE_PAPER_PITCH.md must exist (Phase 3.2)"
    text = PITCH.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in [
        "statement of need",
        "functionality",
        "process",
        "method-only",
        "no-solution",
        "conditional",
        "doi",
        "feasibility",
    ]:
        assert phrase in lower, f"missing required section/topic: {phrase}"
    # Comparison stance must keep the propose/certify split explicit
    assert "propose" in lower and ("certif" in lower)


def test_packaging_docs_anti_overclaim() -> None:
    for path in (CHECKLIST, PITCH):
        plain = re.sub(r"[*_`]", "", path.read_text(encoding="utf-8")).lower()
        assert "does not claim" in plain or "do not claim" in plain, f"{path.name} must carry anti-overclaim language"
        for m in re.finditer(r"process\s+(?:is|has been)\s+retired", plain):
            start = max(0, m.start() - 64)
            window = plain[start : m.start()]
            assert ("does not" in window) or ("do not" in window) or ("never" in window) or ("not claim" in window), (
                f"unqualified retirement claim in {path.name} near: {plain[m.start()-20:m.end()+20]!r}"
            )
        # No concrete DOI value may appear until a real Zenodo deposit is made
        assert not re.search(r"10\.\d{4,9}/", plain), (
            f"{path.name} contains a concrete DOI-like identifier before any Zenodo deposit"
        )


def test_readme_links_citation_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CITATION.cff" in readme
    assert "RELEASE_ARCHIVAL_CHECKLIST.md" in readme


def test_roadmap_marks_phase_3_2() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "RELEASE_ARCHIVAL_CHECKLIST" in roadmap
    line_3_2 = next((ln for ln in roadmap.splitlines() if "Phase 3.2" in ln), "")
    assert "DONE" in line_3_2, "roadmap must mark Phase 3.2 DONE"
    assert "Phase 3.3" in roadmap, "roadmap must declare the next ticket (3.3)"
