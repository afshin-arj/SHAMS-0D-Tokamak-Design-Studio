from __future__ import annotations

from pathlib import Path


def test_v364_benchmark_runner_smoke(tmp_path: Path):
    """Smoke-test: run v364 suite on the synthetic cases and emit artifacts."""
    from src.parity_harness.runner import run_benchmark_suite

    out = tmp_path / "bench_out"
    rep = run_benchmark_suite(
        suite="v364",
        cases_dir=Path("benchmarks/cases"),
        out_dir=out,
        process_dir=None,
        generate_delta_dossiers=False,
    )

    assert rep["suite"] == "v364"
    assert int(rep["n_cases"]) >= 3
    # Ensure a case artifact exists
    paths = list(out.glob("**/shams_artifact.json"))
    assert len(paths) >= 1
