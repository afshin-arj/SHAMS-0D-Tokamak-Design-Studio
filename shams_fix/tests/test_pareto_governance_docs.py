from pathlib import Path


def test_pareto_docs_present():
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"
    assert (docs / "PARETO_MODE_CONSTITUTION.md").exists()
    assert (docs / "PARETO_FREEZE.md").exists()
    assert (docs / "PARETO_POST_FREEZE_CONTRIBUTION_RULES.md").exists()
    assert (docs / "PARETO_TEACHING_FREEZE_POLICY.md").exists()
