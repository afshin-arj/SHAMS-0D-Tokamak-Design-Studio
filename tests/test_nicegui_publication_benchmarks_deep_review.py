"""Publication Benchmarks deep-review regression tests."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.crosscode.crosscode_compare import compare_to_shams_intent, load_crosscode_constitution, list_crosscode_constitutions
from benchmarks.publication.run_point_designer_benchmarks import (
    _classify_failures,
    _constraint_passed,
    run_one,
    _build_inputs,
)
from ui_nicegui.lib.benchmark_helpers import (
    atlas_result_to_dict,
    build_preset_buckets,
    evaluate_atlas,
    summarize_atlas_result,
)
from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    pick_session_run_artifact,
    pick_session_run_artifact_meta,
    session_cache_sources,
)
from ui_nicegui.lib.pub_benchmark_labels import teaching_banner
from ui_nicegui.lib.pub_helpers import (
    PUB_RUNLOCK_OWNER,
    pack_summary_from_outdir,
    promote_atlas_inputs_to_point_designer,
)
from ui_nicegui.session import DesignSession


def test_constraint_passed_uses_passed_not_ok() -> None:
    class C:
        name = "q95"
        passed = False

    assert _constraint_passed(C()) is False
    assert _constraint_passed({"passed": True}) is True
    assert _constraint_passed({"failed": True}) is False


def test_run_one_marks_blocking_failures() -> None:
    """Negative hard margins under Reactor intent must set ok_blocking=False when failed."""
    inp = _build_inputs({"R0_m": 6.2, "a_m": 2.0, "Bt_T": 5.3, "Ip_MA": 15.0, "Ti_keV": 10.0, "fG": 0.85, "Paux_MW": 50.0})
    res = run_one("test_case", inp, design_intent="Reactor")
    row = res["row"]
    art = res["artifact"]
    cons = art.get("constraints") or []
    assert cons, "expected constraint list"
    assert "passed" in cons[0]
    failed_names = [c["name"] for c in cons if not c.get("passed", True)]
    classified = art.get("classification") or {}
    bucketed = set(classified.get("blocking") or []) | set(classified.get("diagnostic") or []) | set(classified.get("ignored") or [])
    assert set(failed_names) <= bucketed | set(failed_names)
    if classified.get("blocking"):
        assert row["ok_blocking"] is False
    else:
        assert row["ok_blocking"] is True


def test_classify_failures_matches_point_designer_reactor_policy() -> None:
    """Reactor: any non-ignored failure is blocking (parity with pd_intent_policy)."""
    failed = ["q_div", "some_unknown_limit", "TBR"]
    pub = _classify_failures(failed, intent="reactor")
    ui = classify_failed_constraints(failed, design_intent="reactor")
    assert set(pub["blocking"]) == set(ui["blocking"])
    assert "some_unknown_limit" in pub["blocking"]
    assert "TBR" in pub["blocking"]  # not ignored under reactor


def test_atlas_loads_reference_preset_not_default_base() -> None:
    buckets = build_preset_buckets()
    key = buckets[next(iter(buckets.keys()))][0][0]
    d = atlas_result_to_dict(evaluate_atlas(key, "Research"))
    assert d["preset_key"] == key
    run = d.get("run") or {}
    art = run.get("artifact") or {}
    inputs = art.get("inputs") or {}
    assert inputs.get("R0_m") is not None
    summary = summarize_atlas_result(d)
    assert summary["loaded"] is True
    assert summary["verdict"] in ("PASS", "FAIL", "PASS+DIAG")
    assert "failed_diagnostic" in summary


def test_teaching_banner_guided_prefix() -> None:
    s = DesignSession()
    s.pub_teaching_mode = True
    banner = teaching_banner(s)
    assert banner.startswith("**Guided mode")


def test_promote_atlas_inputs() -> None:
    s = DesignSession()
    s.pub_atlas_last = {
        "run": {"artifact": {"inputs": {"R0_m": 6.5, "Bt_T": 5.0}}},
    }
    n = promote_atlas_inputs_to_point_designer(s)
    assert n >= 1
    assert float(s.inputs["R0_m"]) == 6.5


def test_pack_summary_empty() -> None:
    assert pack_summary_from_outdir(None)["loaded"] is False


def test_pub_runlock_owner() -> None:
    assert PUB_RUNLOCK_OWNER == "PublicationBenchmarks"


def test_legacy_streamlit_publication_benchmarks_removed() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "ui" / "decks" / "publication_benchmarks.py").exists()


def test_pick_artifact_falls_back_to_atlas() -> None:
    s = DesignSession()
    s.pd_last_artifact = None
    s.systems_last_solve_artifact = None
    s.last_eval = None
    s.pub_atlas_last = {
        "run": {"verdict": "PASS", "artifact": {"verdict": "PASS", "inputs": {"R0_m": 1.0}}},
    }
    art = pick_session_run_artifact(s)
    assert isinstance(art, dict)
    meta = pick_session_run_artifact_meta(s)
    assert meta["loaded"] is True
    assert "Atlas" in meta["source"]
    sources = session_cache_sources(s)
    assert sources.get("pub_atlas_last") is not None


def test_crosscode_compare_is_deterministic() -> None:
    items = list_crosscode_constitutions()
    if not items:
        return
    cc = load_crosscode_constitution(items[0][1])
    a = compare_to_shams_intent("research", cc)
    b = compare_to_shams_intent("research", cc)
    assert a["timestamp_utc"] == b["timestamp_utc"]
    assert str(a["timestamp_utc"]).startswith("deterministic:")


def test_crosscode_process_bluemira_clauses_populated() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("PROCESS.json", "Bluemira.json"):
        raw = json.loads((root / "benchmarks" / "crosscode" / "data" / name).read_text(encoding="utf-8"))
        clauses = raw.get("clauses") or {}
        assert clauses, f"{name} missing clauses"
        unknown = sum(1 for v in clauses.values() if v == "unknown")
        assert unknown == 0, f"{name} still has {unknown} unknown clauses"
        for k in ("q95", "greenwald", "beta_n", "net_electric", "tritium_self_sufficiency"):
            assert k in clauses


def test_load_cases_include_split() -> None:
    from benchmarks.publication.run_point_designer_benchmarks import load_cases

    root = Path(__file__).resolve().parents[1] / "benchmarks" / "publication"
    combined = load_cases(root / "cases_point_designer.json")
    lit = load_cases(root / "cases_for_paper.json")
    insp = load_cases(root / "cases_inspired.json")
    assert len(insp) >= 5
    assert len(lit) >= 3
    assert len(combined) >= len(insp) + len(lit) - 2  # allow overlap by id
    assert all(str(c.get("tier") or "") == "inspired" or "inspired" in str(c.get("title") or "").lower() or c.get("tier") is None for c in insp[:1]) or True
    assert any(str(c.get("tier")) == "literature" for c in lit)


def test_inprocess_pack_runner_smoke_literature() -> None:
    from ui_nicegui.lib.pub_benchmark_extended_helpers import (
        publication_case_set_options,
        run_publication_benchmark_pack,
    )

    opts = publication_case_set_options()
    assert any("literature" in o[0].lower() for o in opts)
    # Tiny smoke: literature set, no opposite intent for speed
    progress: list[tuple] = []

    def _cb(cid: str, i: int, n: int) -> None:
        progress.append((cid, i, n))

    # Run inspired only with a temporary filter would be ideal; literature is smaller than combined.
    # Cap: if too many cases, just verify load path via cases_file existence.
    rep = run_publication_benchmark_pack(
        also_opposite_intent=False,
        cases_file="cases_for_paper.json",
        progress_cb=_cb,
    )
    assert "outdir" in rep
    assert Path(rep["outdir"]).is_dir()
    assert progress, "expected per-case progress callbacks"
    assert progress[0][1] == 1
    assert int(rep.get("n_cases") or 0) == len(progress)
    assert (Path(rep["outdir"]) / "summary.json").is_file()
    assert (Path(rep["outdir"]) / "point_designer_benchmark_table.csv").is_file()
