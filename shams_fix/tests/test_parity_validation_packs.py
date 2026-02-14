from pathlib import Path

from src.parity.validation_packs import load_validation_packs, evaluate_pack_candidate, compare_to_reference


def test_validation_packs_run_end_to_end():
    packs = load_validation_packs(Path("benchmarks/ppl_validation_packs_v3.json"))
    assert len(packs) >= 2
    # use built-in refs (generated from current outputs) to ensure PASS
    import json
    refs = json.loads(Path("benchmarks/ppl_validation_refs_v3.json").read_text(encoding="utf-8"))["refs"]
    p = packs[0]
    _, _, metrics, _ = evaluate_pack_candidate(p)
    ref = refs.get(p.pack_id, {})
    res = compare_to_reference(pack=p, metrics=metrics, reference=ref)
    assert res["status"] in ("PASS", "WARN", "FAIL")
    # With self-generated refs, worst error should be ~0
    assert res["worst_rel_err"] < 1e-9
