"""Independence Phase 4.1 — scoped PROCESS retirement evidence report lock.

Ensures process_retirement_report generates deterministically, cites VERSION +
hashes, lists NOT_COVERED domains, and refuses blanket PROCESS-retired claims.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "PROCESS_RETIREMENT_REPORT.md"
JSON_PATH = ROOT / "docs" / "validation" / "reports" / "process_retirement_report.json"


def test_generator_importable() -> None:
    from reports.process_retirement_report import (  # noqa: F401
        REPORT_SCHEMA,
        build_process_retirement_report,
        validate_report_honesty,
    )

    assert REPORT_SCHEMA == "shams.process_retirement_report.v1"


def test_report_builds_deterministically() -> None:
    from reports.process_retirement_report import build_process_retirement_report

    a = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    b = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    assert a["report_sha256"] == b["report_sha256"]
    assert len(a["report_sha256"]) == 64
    assert a["schema"] == "shams.process_retirement_report.v1"
    assert a["shams_version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_report_honesty_gate_flags() -> None:
    from reports.process_retirement_report import (
        build_process_retirement_report,
        validate_report_honesty,
    )

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    assert validate_report_honesty(report) == []
    assert report["verdict"]["blanket_process_retired"] is False
    assert report["honesty"]["process_retired_claimed"] is False
    assert report["honesty"]["numeric_parity_claimed"] is False
    assert report["honesty"]["invented_mfile"] is False
    assert report["verdict"]["release_status"] == "CONDITIONAL"
    assert report["verdict"]["parity_corpus_status"] == "METHOD-ONLY"


def test_report_refuses_overclaim_mutation() -> None:
    from reports.process_retirement_report import (
        build_process_retirement_report,
        validate_report_honesty,
    )

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    bad = json.loads(json.dumps(report))
    bad["verdict"]["blanket_process_retired"] = True
    bad.pop("report_sha256", None)
    issues = validate_report_honesty(bad)
    assert any("blanket_process_retired" in i for i in issues)

    bad2 = json.loads(json.dumps(report))
    bad2["honesty"]["numeric_parity_claimed"] = True
    bad2.pop("report_sha256", None)
    issues2 = validate_report_honesty(bad2)
    assert any("numeric_parity" in i for i in issues2)


def test_report_lists_not_covered_domains() -> None:
    from reports.process_retirement_report import build_process_retirement_report

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    by_id = {d["domain_id"]: d for d in report["domains"]}
    required_not = {
        "process_numeric_parity",
        "stellarator_ife",
        "bankable_cost_coe",
        "neutrals_edge_physics",
        "approved_zenodo_doi",
        "full_process_cli_breadth",
    }
    for did in required_not:
        assert did in by_id, did
        assert by_id[did]["coverage"] == "NOT_COVERED"
    assert report["coverage_summary"]["n_not_covered"] >= len(required_not)
    assert report["coverage_summary"]["n_scoped_covered_or_proxy"] >= 5


def test_report_cites_champion_and_parity_hashes() -> None:
    from reports.process_retirement_report import build_process_retirement_report

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    champs = report["evidence_index"]["champions"]
    assert champs["evaluated"] is True
    assert champs["pack_sha256"] and len(champs["pack_sha256"]) == 64
    assert champs["n_cases"] >= 3
    cited = [c for c in champs["cases"] if c.get("citation_sha256")]
    assert len(cited) == champs["n_cases"]
    for c in cited:
        assert len(c["citation_sha256"]) == 64

    parity = report["evidence_index"]["parity"]
    assert parity["corpus_status"] == "METHOD-ONLY"
    assert parity["dossiers"]
    for d in parity["dossiers"]:
        assert d["dossier_status"] == "METHOD-ONLY"
        assert d["file_sha256"] and len(d["file_sha256"]) == 64
        assert d["hash_match"] is True


def test_report_cites_overlays_and_release_gate() -> None:
    from reports.process_retirement_report import build_process_retirement_report

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    overlays = report["evidence_index"]["overlays"]
    assert len(overlays) == 5
    assert all(o.get("exists") for o in overlays), overlays
    gate = report["evidence_index"]["release_gate"]
    assert gate["verdict"] == "CONDITIONAL"
    assert gate["exists"] is True


def test_markdown_render_anti_overclaim() -> None:
    from reports.process_retirement_report import (
        build_process_retirement_report,
        render_process_retirement_markdown,
    )

    report = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    md = render_process_retirement_markdown(report)
    plain = re.sub(r"[*_`]", "", md).lower()
    assert "conditional" in plain
    assert "method-only" in plain
    assert "not_covered" in plain or "not covered" in plain
    assert "do not claim process is retired" in plain or "process is not retired" in plain
    for m in re.finditer(r"process\s+(?:is|has been)\s+retired", plain):
        start = max(0, m.start() - 48)
        window = plain[start : m.start()]
        assert (
            ("does not" in window)
            or ("do not" in window)
            or ("not claim" in window)
            or ("is not" in window)
            or ("never" in window)
        ), f"unqualified retirement claim near: {plain[m.start() - 20 : m.end() + 20]!r}"


def test_checked_in_artifacts_match_generator() -> None:
    """Checked-in JSON/MD must match a fresh build (stable hashing)."""
    from reports.process_retirement_report import (
        build_process_retirement_report,
        render_process_retirement_markdown,
        write_process_retirement_report,
    )

    # Ensure artifacts exist (generate if missing in fresh clones during develop)
    if not JSON_PATH.is_file() or not DOC.is_file():
        write_process_retirement_report(repo_root=ROOT, evaluate_champions=True)

    fresh = build_process_retirement_report(repo_root=ROOT, evaluate_champions=True)
    on_disk = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    # Drop helper key if present
    on_disk.pop("_written", None)
    assert on_disk["report_sha256"] == fresh["report_sha256"]
    assert on_disk["shams_version"] == fresh["shams_version"]
    assert on_disk["verdict"]["blanket_process_retired"] is False

    md_disk = DOC.read_text(encoding="utf-8")
    assert fresh["report_sha256"] in md_disk
    assert "Blanket PROCESS-retirement claim?" in md_disk
    assert "**NO**" in md_disk
    assert "CONDITIONAL" in md_disk
    assert render_process_retirement_markdown(fresh).splitlines()[0] in md_disk


def test_docs_library_and_studio_surface_report() -> None:
    from ui_nicegui.lib.control_room_helpers import list_docs
    from ui_nicegui.lib import studio_entry

    docs = list_docs()
    assert "PROCESS_RETIREMENT_REPORT.md" in docs
    labels = [lbl for lbl, _ in studio_entry.STUDIO_DOC_LINKS]
    assert any("retirement" in lbl.lower() or "scoped" in lbl.lower() for lbl in labels)
    # No version tags in user-facing studio doc labels
    for lbl, _ in studio_entry.STUDIO_DOC_LINKS:
        assert not re.search(r"\bv\d{3}", lbl), lbl


def test_roadmap_marks_phase_4_1() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "4.1" in roadmap
    assert "process_retirement_report" in roadmap.lower() or "PROCESS_RETIREMENT_REPORT" in roadmap
    # After ship: DONE marker for 4.1
    assert "4.1" in roadmap and "DONE" in roadmap
    assert "4.2" in roadmap  # next ticket declared
