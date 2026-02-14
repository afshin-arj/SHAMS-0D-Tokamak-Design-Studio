from __future__ import annotations


def test_regime_conditioned_atlas_smoke() -> None:
    from analysis.regime_conditioned_atlas_v365 import AtlasConfig, MetricSpec, build_regime_conditioned_atlas

    recs = [
        {"candidate_id": "a", "optimistic_feasible": True, "robust_feasible": True, "plasma_regime": "H-mode", "exhaust_regime": "detached", "dominance_label": "PLASMA", "outputs": {"P_e_net_MW": 500.0, "f_recirc": 0.25, "CoE_USD_MWh": 80.0}},
        {"candidate_id": "b", "optimistic_feasible": True, "robust_feasible": True, "plasma_regime": "H-mode", "exhaust_regime": "detached", "dominance_label": "PLASMA", "outputs": {"P_e_net_MW": 450.0, "f_recirc": 0.20, "CoE_USD_MWh": 75.0}},
        {"candidate_id": "c", "optimistic_feasible": True, "robust_feasible": False, "plasma_regime": "H-mode", "exhaust_regime": "attached", "dominance_label": "EXHAUST", "outputs": {"P_e_net_MW": 600.0, "f_recirc": 0.40, "CoE_USD_MWh": 120.0}},
    ]

    cfg = AtlasConfig(
        conditioning_axes=("plasma_regime", "exhaust_regime", "dominance_label", "robustness_class"),
        min_bucket_size=1,
        feasibility_gate="robust_only",
        metrics=(MetricSpec("P_e_net_MW", "max"), MetricSpec("f_recirc", "min"), MetricSpec("CoE_USD_MWh", "min")),
    )

    atlas = build_regime_conditioned_atlas(recs, cfg)
    assert atlas["schema"] == "shams_regime_conditioned_atlas.v365"
    assert "fingerprint_sha256" in atlas
    # Only robust-only candidates appear in pareto sets
    ids = {row.get("candidate_id") for row in atlas.get("pareto_sets", [])}
    assert "c" not in ids