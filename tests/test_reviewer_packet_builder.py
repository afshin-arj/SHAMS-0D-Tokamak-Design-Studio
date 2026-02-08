from __future__ import annotations

import json
import zipfile
from pathlib import Path

from tools.sandbox.reviewer_packet_builder import ReviewerPacketOptions, build_reviewer_packet_zip


def test_reviewer_packet_zip_contains_core_artifacts(tmp_path: Path) -> None:
    candidate = {
        "intent": "TestReactor",
        "feasible": True,
        "failure_mode": "",
        "inputs": {"R0_m": 6.2},
        "outputs": {"Q": 10.0},
        "constraints": [],
    }
    zip_bytes, summary = build_reviewer_packet_zip(
        candidate=candidate,
        repo_root=Path(__file__).resolve().parents[1],
        run_capsule={"schema": "shams.run_capsule.v2", "note": "unit-test"},
        scan_grounding={"note": "scan"},
        do_not_build_brief={"note": "dnb"},
        options=ReviewerPacketOptions(),
    )
    assert isinstance(zip_bytes, (bytes, bytearray)) and len(zip_bytes) > 200
    assert summary.get("schema") == "shams.reviewer_packet.summary.v1"

    with zipfile.ZipFile(io := tmp_path / "packet.zip", "w"):
        pass
    (tmp_path / "packet.zip").write_bytes(zip_bytes)
    with zipfile.ZipFile(tmp_path / "packet.zip", "r") as zf:
        names = set(zf.namelist())
        # Required
        assert "candidate.json" in names
        assert "MANIFEST_PACKET_SHA256.json" in names
        # Default inclusions
        assert "report_pack/report_pack.md" in names
        assert "review_trinity/review_trinity.md" in names
        assert "attack_simulation/attack_simulation.md" in names
        assert "run_capsule.json" in names
        assert "scan_grounding.json" in names
        assert "do_not_build_brief.json" in names
        # Manifest decodes
        man = json.loads(zf.read("MANIFEST_PACKET_SHA256.json").decode("utf-8"))
        assert man.get("schema") == "shams.reviewer_packet.manifest.v1"
        files = man.get("files") or []
        assert any(f.get("path") == "candidate.json" for f in files)
