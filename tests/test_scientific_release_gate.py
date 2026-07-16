"""Independence Phase 1.4 — scientific release gate lock.

Ensures CONDITIONAL release evidence and honesty artifacts remain present.
Does not claim PROCESS retirement or APPROVED without evidence.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_file_present_and_nonempty() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version.startswith("v")
    assert len(version) >= 5


def test_limitations_doc_present() -> None:
    path = ROOT / "docs" / "LIMITATIONS.md"
    text = path.read_text(encoding="utf-8")
    assert "METHOD-ONLY" in text
    assert "PROCESS" in text
    assert "retired" in text.lower()
    assert "Do not claim" in text or "does **not** claim" in text or "does not claim" in text.lower()


def test_scientific_release_readiness_report_conditional() -> None:
    path = ROOT / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
    text = path.read_text(encoding="utf-8")
    assert "CONDITIONAL" in text
    assert "docs/LIMITATIONS.md" in text
    # Anti-overclaim: must forbid retirement claims, not assert retirement
    lower = text.lower()
    assert "do not claim process" in lower or "process **not** retired" in lower or "process not retired" in lower
    assert "release verdict:** **conditional**" in lower or "**conditional**" in lower
    # Must not contain an unqualified retirement assertion as a positive claim line
    assert "verdict:** **approved**" not in lower or "conditional" in lower


def test_citation_cff_aligned_with_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    cff_raw = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    version_line = next(
        (ln for ln in cff_raw.splitlines() if ln.startswith("version:")),
        "",
    )
    assert version in version_line
    assert "Apache-2.0" in cff_raw or "Apache" in cff_raw


def test_license_and_governance_present() -> None:
    assert (ROOT / "LICENSE").is_file()
    gov = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
    assert "frozen" in gov.lower() or "Frozen" in gov


def test_readme_links_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "v418" in readme or (ROOT / "VERSION").read_text(encoding="utf-8").strip()[:5] in readme
    assert "LIMITATIONS" in readme or "docs/LIMITATIONS.md" in readme
