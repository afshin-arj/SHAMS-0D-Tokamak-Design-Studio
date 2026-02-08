from __future__ import annotations

from tools.optimizer_family import build_family_gallery

def test_family_gallery_groups_by_island_id():
    records = [
        {"candidate": False, "inputs": {"_seed_meta": {"island_id": 0}}, "objective": 1, "worst_hard_margin": -1},
        {"candidate": True, "inputs": {"_seed_meta": {"island_id": 0}}, "objective": 5.0, "worst_hard_margin": 0.1},
        {"candidate": True, "inputs": {"_seed_meta": {"island_id": 0}}, "objective": 4.0, "worst_hard_margin": 0.2},
        {"candidate": True, "inputs": {"_seed_meta": {"island_id": 2}}, "objective": 2.0, "worst_hard_margin": 0.05},
        {"candidate": True, "inputs": {}, "objective": 1.0, "worst_hard_margin": 0.01},
    ]
    gal = build_family_gallery(records, objective_key="P_net_MW", objective_direction="max")
    assert gal["schema"] == "optimizer_family_gallery.v1"
    fams = {f["family_id"]: f for f in gal["families"]}
    assert fams[0]["n_feasible"] == 2
    assert fams[2]["n_feasible"] == 1
    assert fams[-1]["n_feasible"] == 1
    # robust rep should be record with max worst margin within family 0 (0.2)
    assert fams[0]["representatives"]["robust_best"]["record_index"] == 2
