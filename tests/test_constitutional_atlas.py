from __future__ import annotations

def test_constitutional_atlas_smoke():
    from src.models.reference_machines import reference_catalog
    from benchmarks.constitutional.atlas import evaluate_atlas_case, local_fragility_scan

    cat = reference_catalog()
    # Pick a deterministic first key
    k = sorted(cat.keys())[0]
    res = evaluate_atlas_case(k, "Research")
    assert res.schema.startswith("tokamak_constitutional_atlas_result")
    assert res.preset_key == k
    assert isinstance(res.run, dict)

    scan = local_fragility_scan(k, "Research", {})
    assert isinstance(scan, dict)
