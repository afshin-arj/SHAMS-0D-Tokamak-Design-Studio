"""ExtOpt batch: evaluator injection + honest intent_verdict tokens."""
from __future__ import annotations

from pathlib import Path

from extopt.batch import BatchEvalConfig, evaluate_concept_family
from extopt.family import load_concept_family


class _StubEv:
    """Minimal evaluator duck-type for injection tests (no L0 call)."""

    def evaluate(self, pi):
        class _R:
            ok = True
            out = {
                "Q_DT_eqv": 1.0,
                "Pfus_total_MW": 0.0,
                "P_e_net_MW": 0.0,
                "beta_N": 0.1,
                "q95_proxy": 3.0,
            }
            message = ""

        return _R()


def test_evaluate_concept_family_accepts_injected_evaluator(monkeypatch):
    """Injected evaluator must be used (NiceGUI ui_evaluator path)."""
    repo_root = Path(__file__).resolve().parents[1]
    fam_path = repo_root / "examples" / "concept_families" / "reactor_intent_baseline.yaml"
    fam = load_concept_family(fam_path)

    # Force constraint builder to empty list so we don't need full L0 outputs.
    import extopt.batch as batch_mod

    monkeypatch.setattr(batch_mod, "build_constraints_from_outputs", lambda *a, **k: [])
    monkeypatch.setattr(
        batch_mod,
        "build_run_artifact",
        lambda **kw: {
            "schema_version": "shams_run_artifact.v1",
            "inputs": kw.get("inputs") or {},
            "outputs": kw.get("outputs") or {},
            "constraints": kw.get("constraints") or [],
            "kpis": {"feasible_hard": False, "min_hard_margin": -1.0},
        },
    )

    stub = _StubEv()
    called = {"n": 0}
    _orig = stub.evaluate

    def _wrap(pi):
        called["n"] += 1
        return _orig(pi)

    stub.evaluate = _wrap  # type: ignore[method-assign]

    cfg = BatchEvalConfig(cache_enabled=False, cache_dir=None)
    res = evaluate_concept_family(fam, config=cfg, evaluator=stub)
    assert called["n"] == res.n_total == len(fam.candidates)
    assert hasattr(res, "artifacts")
    assert set(res.artifacts.keys()) == {c.cid for c in fam.candidates}
    for r in res.results:
        assert r.artifact.get("intent_verdict") == "INFEASIBLE"
        assert r.artifact.get("verdict") == "FAIL"


def test_evaluate_concept_family_legacy_kwargs_backcompat():
    """clients/reference_optimizer-style kwargs must not TypeError."""
    repo_root = Path(__file__).resolve().parents[1]
    fam_path = repo_root / "examples" / "concept_families" / "reactor_intent_baseline.yaml"
    fam = load_concept_family(fam_path)
    # Only first candidate to keep smoke light if something falls through
    from dataclasses import replace
    from extopt.family import ConceptCandidate

    fam = replace(fam, candidates=fam.candidates[:1])
    res = evaluate_concept_family(
        fam,
        evaluator_label="hot_ion_point",
        cache_enabled=False,
        cache_dir=None,
        export_evidence_packs=False,
        evidence_dir=None,
    )
    assert res.n_total == 1
    assert res.results[0].artifact.get("intent_verdict") in ("FEASIBLE", "INFEASIBLE")


def test_trade_study_dashboard_does_not_green_pass_on_sampling_confidence():
    """blocking-OK + Pareto sampling must not show green PASS as design certification."""
    import inspect

    from ui_nicegui.decks.trade_study_studio import verdict as vmod

    src = inspect.getsource(vmod.render_study_dashboard)
    assert "BLOCKING-OK SCREENING" in src
    assert 'title_prefix="Frontier screening posture"' in src
    assert "PASS+DIAG" not in src
    assert 'verdict_banner("PASS"' not in src
    assert "blocking-OK" in src


def test_extopt_helpers_inject_ui_evaluator():
    import inspect

    from ui_nicegui.lib import external_optimizer_helpers as h

    assert "ui_evaluator" in inspect.getsource(h.evaluate_concept_family_yaml)
    assert "ui_evaluator" in inspect.getsource(h.run_orchestrator_v385)
    assert "ui_evaluator" in inspect.getsource(h.run_extopt_workbench)
