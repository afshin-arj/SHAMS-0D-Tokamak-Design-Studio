"""Independence Phase 4.2 — Cite-SHAMS handoff pack lock tests.

Ensures the handoff pack builds deterministically, carries required cite/reproduce
files, stamps NO-SOLUTION atlas when infeasible, and keeps PROCESS/CONDITIONAL honesty.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _feasible_artifact() -> dict:
    from models.inputs import PointInputs
    from models.reference_machines import REFERENCE_MACHINES
    from shams_io.run_artifact import build_run_artifact

    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    cons = [
        {
            "name": "q95",
            "value": 3.5,
            "limit": 2.0,
            "sense": ">=",
            "passed": True,
            "severity": "hard",
            "margin_frac": 0.5,
            "units": "",
            "group": "stability",
        }
    ]
    return build_run_artifact(
        inputs=inp.to_dict(),
        outputs={"Q_DT_eqv": 5.0, "P_fus_MW": 100.0, "q95": 3.5},
        constraints=cons,
        meta={"created_unix": 0.0, "label": "cite_pack_feasible", "mode": "test"},
    )


def _infeasible_artifact() -> dict:
    from models.inputs import PointInputs
    from models.reference_machines import REFERENCE_MACHINES
    from shams_io.run_artifact import build_run_artifact

    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    cons = [
        {
            "name": "Transport spread",
            "value": 5.0,
            "limit": 1.5,
            "sense": "<=",
            "passed": False,
            "severity": "hard",
            "margin_frac": -2.0,
            "units": "",
            "group": "transport",
        }
    ]
    return build_run_artifact(
        inputs=inp.to_dict(),
        outputs={
            "Q_DT_eqv": 1.0,
            "transport_spread_ratio_v396": 5.0,
            "transport_spread_max_v396": 1.5,
        },
        constraints=cons,
        meta={"created_unix": 0.0, "label": "cite_pack_infeasible", "mode": "test"},
    )


def test_generator_importable() -> None:
    from reports.cite_shams_handoff_pack import (  # noqa: F401
        PACK_SCHEMA,
        build_cite_shams_handoff_pack,
        validate_pack_honesty,
    )

    assert PACK_SCHEMA == "shams.cite_shams_handoff_pack.v1"


def test_pack_builds_deterministically() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    art = _feasible_artifact()
    a = build_cite_shams_handoff_pack(
        art, repo_root=ROOT, created_unix=0.0, include_git_describe=False
    )
    b = build_cite_shams_handoff_pack(
        art, repo_root=ROOT, created_unix=0.0, include_git_describe=False
    )
    assert a["pack_sha256"] == b["pack_sha256"]
    assert len(a["pack_sha256"]) == 64
    assert a["zip_bytes"] == b["zip_bytes"]
    assert a["shams_version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert a["release_status"] == "CONDITIONAL"
    assert a["process_retired_claimed"] is False


def test_pack_contains_required_files() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    required = {
        "VERSION",
        "provenance.json",
        "point_inputs.json",
        "run_artifact.json",
        "run_artifact.sha256",
        "evaluation_export.json",
        "CITATION.cff",
        "citation.txt",
        "citation.bib",
        "release_gate.json",
        "LIMITATIONS_POINTER.md",
        "HONESTY.md",
        "README.md",
        "manifest.json",
        "MANIFEST_SHA256.txt",
        "pack_meta.json",
    }
    assert required <= set(pack["files"])
    with zipfile.ZipFile(io.BytesIO(pack["zip_bytes"]), "r") as zf:
        names = set(zf.namelist())
    assert required <= names
    # Manifest lists content hashes
    manifest = json.loads(pack["files"]["manifest.json"].decode("utf-8"))
    assert manifest["run_artifact_sha256"] == pack["run_artifact_sha256"]
    assert pack["run_artifact_sha256"] == pack["files"]["run_artifact.sha256"].decode().strip()


def test_citation_snippet_matches_version_and_artifact_hash() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    version = pack["shams_version"]
    sha = pack["run_artifact_sha256"]
    cite = pack["files"]["citation.txt"].decode("utf-8")
    bib = pack["files"]["citation.bib"].decode("utf-8")
    assert version in cite
    assert sha in cite
    assert "CONDITIONAL" in cite
    assert "METHOD-ONLY" in cite
    assert version in bib
    assert sha in bib
    assert "@software{" in bib
    cff = pack["files"]["CITATION.cff"].decode("utf-8")
    assert version in cff or f'version: "{version}"' in cff or f"version: {version}" in cff


def test_infeasible_pack_carries_atlas() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    art = _infeasible_artifact()
    assert art.get("no_solution_atlas") or art.get("kpis", {}).get("feasible_hard") is False
    pack = build_cite_shams_handoff_pack(
        art, repo_root=ROOT, created_unix=0.0, include_git_describe=False
    )
    assert pack["has_no_solution_atlas"] is True
    assert pack["hard_feasible"] is False
    assert "no_solution_atlas.json" in pack["files"]
    atlas = json.loads(pack["files"]["no_solution_atlas.json"].decode("utf-8"))
    assert atlas.get("schema") == "no_solution_atlas.v1"
    assert atlas.get("verdict") in ("INFEASIBLE", "UNKNOWN")


def test_feasible_pack_omits_atlas_file() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    assert pack["hard_feasible"] is True
    assert "no_solution_atlas.json" not in pack["files"]


def test_honesty_language_present() -> None:
    from reports.cite_shams_handoff_pack import (
        build_cite_shams_handoff_pack,
        validate_pack_honesty,
    )

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    assert validate_pack_honesty(pack["pack_meta"], pack["files"]) == []
    honesty = pack["files"]["HONESTY.md"].decode("utf-8")
    assert "METHOD-ONLY" in honesty
    assert "optional" in honesty.lower()
    assert "CONDITIONAL" in honesty
    assert "do **not** claim" in honesty.lower() or "do not claim" in honesty.lower()
    release = json.loads(pack["files"]["release_gate.json"].decode("utf-8"))
    assert release["release_status"] == "CONDITIONAL"


def test_honesty_gate_rejects_process_retired_claim() -> None:
    from reports.cite_shams_handoff_pack import (
        build_cite_shams_handoff_pack,
        validate_pack_honesty,
    )

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    bad_meta = dict(pack["pack_meta"])
    bad_meta["process_retired_claimed"] = True
    issues = validate_pack_honesty(bad_meta, pack["files"])
    assert any("process_retired_claimed" in i for i in issues)

    bad_meta2 = dict(pack["pack_meta"])
    bad_meta2["release_status"] = "APPROVED"
    bad_meta2["approved_evidenced"] = False
    issues2 = validate_pack_honesty(bad_meta2, pack["files"])
    assert any("APPROVED" in i for i in issues2)


def test_write_pack_roundtrip(tmp_path: Path) -> None:
    from reports.cite_shams_handoff_pack import write_cite_shams_handoff_pack

    out = tmp_path / "cite_pack.zip"
    pack = write_cite_shams_handoff_pack(
        _feasible_artifact(),
        out,
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    assert out.is_file()
    assert out.read_bytes() == pack["zip_bytes"]
    with zipfile.ZipFile(out, "r") as zf:
        assert "pack_meta.json" in zf.namelist()
        meta = json.loads(zf.read("pack_meta.json").decode("utf-8"))
    assert meta["pack_sha256"] == pack["pack_sha256"]


def test_point_inputs_present_and_nonempty() -> None:
    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack

    pack = build_cite_shams_handoff_pack(
        _feasible_artifact(),
        repo_root=ROOT,
        created_unix=0.0,
        include_git_describe=False,
    )
    inputs = json.loads(pack["files"]["point_inputs.json"].decode("utf-8"))
    assert isinstance(inputs, dict)
    assert "R0_m" in inputs or "R0" in inputs or len(inputs) > 0


def test_roadmap_marks_phase_4_2() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "4.2" in roadmap
    assert "Cite-SHAMS handoff" in roadmap or "cite-SHAMS handoff" in roadmap
    # Done marker near 4.2
    assert "4.2" in roadmap and "DONE" in roadmap
    assert "4.3" in roadmap  # next ticket declared

    doc = ROOT / "docs" / "CITE_SHAMS_HANDOFF.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "VERSION" in text
    assert "SHA-256" in text or "sha256" in text.lower()
    assert "CONDITIONAL" in text
    assert "METHOD-ONLY" in text
    assert "do **not** claim" in text.lower() or "do not claim" in text.lower()
    assert "PROCESS import" in text or "optional" in text.lower()
