from __future__ import annotations

from tools.regime_maps import build_regime_maps_report


def test_regime_maps_basic_determinism() -> None:
    # Synthetic records resembling trade study rows.
    recs = []
    for i in range(80):
        feas = (i % 5) != 0
        # Two separable clouds for deterministic bin clustering.
        if i < 40:
            R0_m = 1.80 + 0.002 * i
            B0_T = 10.0 + 0.01 * i
            dom = "q_div_MW_m2_screen"
        else:
            R0_m = 2.40 + 0.002 * (i - 40)
            B0_T = 12.0 + 0.01 * (i - 40)
            dom = "tf_stress_screen"

        recs.append(
            {
                "i": i,
                "is_feasible": feas,
                "min_margin_frac": 0.10 - 0.0005 * (i % 17),
                "dominant_constraint": dom,
                "R0_m": R0_m,
                "B0_T": B0_T,
            }
        )

    r1 = build_regime_maps_report(records=recs, features=["R0_m", "B0_T"], min_cluster_size=6, max_bins=12)
    r2 = build_regime_maps_report(records=recs, features=["R0_m", "B0_T"], min_cluster_size=6, max_bins=12)

    assert r1["kind"] == "shams_regime_maps_report"
    assert r1["n_feasible"] > 0
    assert r1["clustering"]["n_clusters"] >= 1

    # Determinism: exact structural match for same inputs.
    assert r1 == r2
