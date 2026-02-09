from __future__ import annotations

from pathlib import Path
import io
import zipfile

from tools.ui_wiring_index import build_ui_wiring_index_markdown
from tools.sandbox.reviewer_packet_builder import build_reviewer_packet_zip, ReviewerPacketOptions


def test_ui_wiring_index_contains_expected_anchors() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    md = build_ui_wiring_index_markdown(repo_root=repo_root)
    for s in [
        "Tabs creation",
        "Systems Mode tab block",
        "Scan Lab tab block",
        "Pareto Lab tab block",
        "Trade Study Studio import",
        "PROCESS parity benchmarks view",
        "Reviewer Packet view",
    ]:
        assert s in md


def test_reviewer_packet_includes_ui_wiring_index_by_default() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    candidate = {"inputs": {"R0_m": 6.2}, "outputs": {"dummy": 1}}
    b, summary = build_reviewer_packet_zip(candidate=candidate, repo_root=repo_root, options=ReviewerPacketOptions())
    assert isinstance(b, (bytes, bytearray))
    assert summary.get("schema", "").startswith("shams.reviewer_packet.summary")

    with zipfile.ZipFile(io.BytesIO(b), "r") as zf:
        names = set(zf.namelist())
        assert "ui/UI_WIRING_INDEX.md" in names
