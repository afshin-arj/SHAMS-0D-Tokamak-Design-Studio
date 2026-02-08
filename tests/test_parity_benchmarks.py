from tools.parity_bench import run_parity_benchmarks


def test_parity_benchmarks_regression():
    res = run_parity_benchmarks(update_golden=False)
    assert isinstance(res, dict)
    assert res.get("ok") is True, res
