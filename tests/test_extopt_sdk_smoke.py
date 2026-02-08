from __future__ import annotations

from pathlib import Path

from extopt.family import load_concept_family
from extopt.batch import BatchEvalConfig, evaluate_concept_family


def test_extopt_evaluates_example_family_smoke(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    fam_path = repo_root / "examples" / "concept_families" / "reactor_intent_baseline.yaml"
    assert fam_path.exists(), "Example concept family missing"

    fam = load_concept_family(fam_path)
    # Keep cache off in tests to avoid interacting with developer machines
    cfg = BatchEvalConfig(cache_enabled=False, cache_dir=None)
    res = evaluate_concept_family(fam, config=cfg, repo_root=repo_root)

    assert res.n_total == len(fam.candidates)
    assert res.n_total > 0
    assert 0 <= res.pass_rate <= 1
    # Every candidate must have an artifact with kpis
    for r in res.results:
        assert isinstance(r.artifact, dict)
        assert "kpis" in r.artifact
