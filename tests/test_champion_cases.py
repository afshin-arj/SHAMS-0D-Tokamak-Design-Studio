"""Independence Phase 3.3 — champion cases lock tests.

Ensures reproducible SHAMS-only champion feasibility templates exist,
evaluate deterministically, and stamp NO-SOLUTION atlas on infeasible rows.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "CHAMPION_CASES.md"
CASES = ROOT / "benchmarks" / "champions" / "cases.json"
RUNNER = ROOT / "benchmarks" / "champions" / "run_champions.py"


def test_champion_doc_present() -> None:
    assert DOC.is_file(), "docs/CHAMPION_CASES.md must exist (Phase 3.3)"


def test_champion_doc_required_sections() -> None:
    text = DOC.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in [
        "champion",
        "reproduce",
        "VERSION",
        "SHA-256",
        "NO-SOLUTION",
        "Design Intent",
        "LIMITATIONS",
        "class/like",
    ]:
        assert phrase.lower() in lower, f"missing required phrase: {phrase}"
    assert "does not" in lower and "process" in lower and "retir" in lower


def test_champion_doc_anti_overclaim() -> None:
    plain = re.sub(r"[*_`]", "", DOC.read_text(encoding="utf-8")).lower()
    assert "invent" in plain and "mfile" in plain
    for m in re.finditer(r"process\s+(?:is|has been)\s+retired", plain):
        start = max(0, m.start() - 48)
        window = plain[start : m.start()]
        assert ("does not" in window) or ("do not" in window) or ("not claim" in window), (
            f"unqualified retirement claim near: {plain[m.start() - 20 : m.end() + 20]!r}"
        )


def test_cases_and_runner_present() -> None:
    assert CASES.is_file()
    assert RUNNER.is_file()


def test_champion_pack_evaluates_deterministically() -> None:
    from studies.champion_cases import run_all_champions

    a = run_all_champions()
    b = run_all_champions()
    assert a["n_cases"] >= 3
    assert a["n_hard_feasible"] >= 1
    assert a["n_infeasible"] >= 1
    assert a["pack_sha256"] == b["pack_sha256"]
    assert len(a["pack_sha256"]) == 64

    by_id = {s["case_id"]: s for s in a["cases"]}
    assert len(by_id) == a["n_cases"]

    for s in a["cases"]:
        assert s["citation_sha256"] and len(s["citation_sha256"]) == 64
        expect = s.get("expect_hard_feasible")
        if expect is True:
            assert s["hard_feasible"] is True, s["case_id"]
            assert s.get("no_solution_atlas") in (None, {})
        elif expect is False:
            assert s["hard_feasible"] is False, s["case_id"]
            atlas = s.get("no_solution_atlas") or {}
            assert atlas.get("schema") == "no_solution_atlas.v1"
            assert atlas.get("verdict") == "INFEASIBLE"
            assert atlas.get("dominant_mechanism")
            assert s.get("dominant_mechanism") == atlas.get("dominant_mechanism")


def test_infeasible_artifact_carries_atlas() -> None:
    from studies.champion_cases import load_champion_definitions, evaluate_champion_case

    cases = load_champion_definitions()
    infeas = [c for c in cases if c.get("expect_hard_feasible") is False]
    assert infeas, "need at least one deliberate infeasible champion"
    result = evaluate_champion_case(infeas[0])
    art = result["artifact"]
    assert art["kpis"]["feasible_hard"] is False
    assert "no_solution_atlas" in art
    assert art["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"


def test_docs_library_lists_champion_doc() -> None:
    from ui_nicegui.lib.control_room_helpers import CHAMPION_CASES_DOC, list_docs

    docs = list_docs()
    assert CHAMPION_CASES_DOC in docs
    assert "CHAMPION_CASES.md" in docs


def test_roadmap_marks_phase_3_3() -> None:
    roadmap = (ROOT / "docs" / "PROCESS_SURPASS_ROADMAP.md").read_text(encoding="utf-8")
    assert "3.3" in roadmap
    assert "Champion cases" in roadmap or "champion cases" in roadmap.lower()
    assert "DONE" in roadmap and "3.3" in roadmap
    # Next ticket after 3.3
    assert "3.4" in roadmap
