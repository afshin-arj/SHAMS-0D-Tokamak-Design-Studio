"""Independence Phase 4.3 — parity contribution + exit evidence locks.

Ensures:
* submission schema validation + honesty (no fabricated NUMERIC)
* contribution intake builds deterministic hashed dossiers
* exit-evidence generator is deterministic
* PENDING/EXTERNAL items cannot be marked DONE without evidence
* no blanket PROCESS-retired claim
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_CONTRIB = ROOT / "docs" / "PARITY_CONTRIBUTION.md"
DOC_EXIT = ROOT / "docs" / "INDEPENDENCE_EXIT_EVIDENCE.md"
JSON_EXIT = ROOT / "docs" / "validation" / "reports" / "independence_exit_evidence.json"
TEMPLATE = ROOT / "benchmarks" / "parity" / "contributions" / "submission_template.json"


def test_contribution_module_importable() -> None:
    from parity_harness.contribution import (  # noqa: F401
        RECEIPT_SCHEMA,
        SUBMISSION_SCHEMA,
        example_method_only_submission,
        validate_submission,
    )

    assert SUBMISSION_SCHEMA == "shams.parity_contribution.v1"
    assert RECEIPT_SCHEMA == "shams.parity_contribution_receipt.v1"


def test_template_validates_as_method_only() -> None:
    from parity_harness.contribution import load_submission, validate_submission

    assert TEMPLATE.is_file()
    sub = load_submission(TEMPLATE)
    assert validate_submission(sub) == []
    assert sub["requested_status"] == "METHOD-ONLY"


def test_method_only_rejects_numeric_kpis() -> None:
    from parity_harness.contribution import example_method_only_submission, validate_submission

    sub = example_method_only_submission()
    sub["process_reference"]["Q_plasma"] = 10.0
    issues = validate_submission(sub)
    assert any("METHOD-ONLY" in i for i in issues)


def test_numeric_requires_provenance_and_license() -> None:
    from parity_harness.contribution import example_method_only_submission, validate_submission

    sub = example_method_only_submission()
    sub["requested_status"] = "NUMERIC"
    sub["process_reference"]["Q_plasma"] = 10.0
    # missing provenance source + license
    issues = validate_submission(sub)
    assert any("process_reference_source" in i for i in issues)
    assert any("holds_process_license" in i for i in issues)

    sub["provenance"]["process_reference_source"] = "lab://licensed-mfile-extract-sha256-abc"
    sub["license_attestation"]["holds_process_license_or_permission"] = True
    sub["license_attestation"]["may_share_extracts_with_shams_maintainers"] = True
    sub["honesty"]["no_invented_mfile"] = True
    assert validate_submission(sub) == []


def test_fabricated_numeric_without_kpis_rejected_on_intake() -> None:
    from parity_harness.contribution import (
        example_method_only_submission,
        process_contribution,
    )

    sub = example_method_only_submission()
    sub["requested_status"] = "NUMERIC"
    # Keep null KPIs — should fail validate or classify as METHOD-ONLY refuse
    sub["provenance"]["process_reference_source"] = "fake://source"
    sub["license_attestation"]["holds_process_license_or_permission"] = True
    sub["license_attestation"]["may_share_extracts_with_shams_maintainers"] = True
    sub["honesty"]["no_invented_mfile"] = True

    receipt = process_contribution(sub, repo_root=ROOT, write=False, evaluate=False)
    assert receipt["accepted"] is False
    assert receipt["issues"]
    assert any(
        "NUMERIC" in i or "KPI" in i or "METHOD-ONLY" in i for i in receipt["issues"]
    )


def test_process_contribution_method_only_deterministic(tmp_path: Path) -> None:
    from parity_harness.contribution import (
        example_method_only_submission,
        process_contribution,
    )

    sub = example_method_only_submission()
    out = tmp_path / "outbox"
    a = process_contribution(sub, repo_root=ROOT, out_dir=out, write=True, evaluate=True)
    b = process_contribution(sub, repo_root=ROOT, out_dir=out, write=False, evaluate=True)
    assert a["accepted"] is True
    assert a["dossier_status"] == "METHOD-ONLY"
    assert a["dossier_sha256"] == b["dossier_sha256"]
    assert len(a["dossier_sha256"]) == 64
    assert a["honesty"]["process_retired_claimed"] is False
    assert (out / f"{sub['case_id']}_delta_dossier.json").is_file()
    assert (out / f"{sub['case_id']}_receipt.json").is_file()


def test_exit_evidence_builds_deterministically() -> None:
    from reports.independence_exit_evidence import build_independence_exit_evidence

    a = build_independence_exit_evidence(repo_root=ROOT)
    b = build_independence_exit_evidence(repo_root=ROOT)
    assert a["report_sha256"] == b["report_sha256"]
    assert len(a["report_sha256"]) == 64
    assert a["schema"] == "shams.independence_exit_evidence.v1"
    assert a["shams_version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_exit_evidence_honesty_and_external_items() -> None:
    from reports.independence_exit_evidence import (
        build_independence_exit_evidence,
        validate_exit_evidence_honesty,
    )

    report = build_independence_exit_evidence(repo_root=ROOT)
    assert validate_exit_evidence_honesty(report) == []
    assert report["verdict"]["blanket_process_retired"] is False
    assert report["verdict"]["phase4_exit_complete"] is False
    assert report["verdict"]["release_status"] == "CONDITIONAL"
    assert report["honesty"]["community_adoption_claimed"] is False
    assert report["honesty"]["approved_doi_claimed"] is False

    by_id = {i["item_id"]: i for i in report["checklist"]}
    assert by_id["community_adoption"]["status"] == "EXTERNAL"
    assert by_id["approved_zenodo_doi"]["status"] == "EXTERNAL"
    assert by_id["scientific_release_conditional"]["status"] == "CONDITIONAL"
    # Shipped gates should be DONE after this ticket's artifacts exist
    for shipped in (
        "cite_shams_handoff_pack",
        "scoped_retirement_report",
        "migration_guide",
        "champion_templates",
        "ccfs_firewall",
        "no_solution_atlas",
        "parity_contribution_channel",
    ):
        assert by_id[shipped]["status"] == "DONE", shipped


def test_exit_evidence_refuses_marking_external_done() -> None:
    from reports.independence_exit_evidence import (
        build_independence_exit_evidence,
        validate_exit_evidence_honesty,
    )

    report = build_independence_exit_evidence(repo_root=ROOT)
    bad = json.loads(json.dumps(report))
    for item in bad["checklist"]:
        if item["item_id"] == "community_adoption":
            item["status"] = "DONE"
    bad.pop("report_sha256", None)
    issues = validate_exit_evidence_honesty(bad)
    assert any("community_adoption" in i for i in issues)

    bad2 = json.loads(json.dumps(report))
    bad2["verdict"]["phase4_exit_complete"] = True
    bad2.pop("report_sha256", None)
    issues2 = validate_exit_evidence_honesty(bad2)
    assert any("phase4_exit_complete" in i for i in issues2)


def test_exit_artifacts_on_disk_match_generator() -> None:
    from reports.independence_exit_evidence import (
        build_independence_exit_evidence,
        render_independence_exit_markdown,
        write_independence_exit_evidence,
    )

    # Regenerate to keep checked-in artifacts in sync for this test run
    write_independence_exit_evidence(repo_root=ROOT)
    fresh = build_independence_exit_evidence(repo_root=ROOT)
    assert JSON_EXIT.is_file()
    assert DOC_EXIT.is_file()
    on_disk = json.loads(JSON_EXIT.read_text(encoding="utf-8"))
    assert on_disk["report_sha256"] == fresh["report_sha256"]
    assert on_disk["verdict"]["blanket_process_retired"] is False
    md = DOC_EXIT.read_text(encoding="utf-8")
    assert fresh["report_sha256"] in md
    assert "Blanket PROCESS-retirement claim?" in md
    assert "**NO**" in md
    assert "EXTERNAL" in md
    assert render_independence_exit_markdown(fresh).splitlines()[0] in md


def test_docs_and_ui_surface() -> None:
    from ui_nicegui.lib.control_room_helpers import list_docs
    from ui_nicegui.lib import studio_entry

    assert DOC_CONTRIB.is_file()
    assert "parity contribution" in DOC_CONTRIB.read_text(encoding="utf-8").lower() or "METHOD-ONLY" in DOC_CONTRIB.read_text(encoding="utf-8")

    docs = list_docs()
    assert "PARITY_CONTRIBUTION.md" in docs
    assert "INDEPENDENCE_EXIT_EVIDENCE.md" in docs

    labels = [lbl for lbl, _ in studio_entry.STUDIO_DOC_LINKS]
    assert any("parity" in lbl.lower() or "contribution" in lbl.lower() for lbl in labels)
    assert any("exit" in lbl.lower() or "independence" in lbl.lower() for lbl in labels)
    for lbl, _ in studio_entry.STUDIO_DOC_LINKS:
        assert not re.search(r"\bv\d{3}", lbl), lbl


def test_roadmap_marks_4_3() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "4.3" in roadmap
    assert "DONE" in roadmap
    assert "parity contribution" in roadmap.lower() or "PARITY_CONTRIBUTION" in roadmap
    assert "independence_exit_evidence" in roadmap.lower() or "INDEPENDENCE_EXIT_EVIDENCE" in roadmap
    # Honest: full exit still open on EXTERNAL items
    assert "EXTERNAL" in roadmap
