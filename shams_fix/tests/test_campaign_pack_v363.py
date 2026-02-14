from __future__ import annotations

import json
from pathlib import Path

from src.campaign.spec import CampaignSpec
from src.campaign.generate import generate_candidates


def test_campaign_spec_roundtrip(tmp_path: Path) -> None:
    spec = CampaignSpec.from_dict(
        {
            "schema": "shams_campaign.v1",
            "name": "smoke",
            "intent": "DT",
            "evaluator_label": "hot_ion_point",
            "variables": [
                {"name": "R0_m", "kind": "float", "lo": 3.0, "hi": 6.0},
                {"name": "B0_T", "kind": "float", "lo": 4.0, "hi": 8.0},
            ],
            "fixed_inputs": {"include_profile_family_v358": True},
            "generator": {"mode": "lhs", "n": 16, "seed": 7},
            "profile_contracts": {"tier": "both", "preset": "C8"},
            "include_full_artifact": False,
        }
    )
    spec.validate()

    p = tmp_path / "campaign.json"
    p.write_text(json.dumps(spec.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    spec2 = CampaignSpec.from_dict(json.loads(p.read_text(encoding="utf-8")))
    spec2.validate()
    assert spec2.name == "smoke"
    assert spec2.generator.mode == "lhs"


def test_candidate_generation_is_deterministic() -> None:
    spec = CampaignSpec.from_dict(
        {
            "schema": "shams_campaign.v1",
            "name": "det",
            "intent": "DT",
            "evaluator_label": "hot_ion_point",
            "variables": [
                {"name": "x", "kind": "float", "lo": 0.0, "hi": 1.0},
                {"name": "y", "kind": "float", "lo": 10.0, "hi": 20.0},
            ],
            "fixed_inputs": {},
            "generator": {"mode": "sobol", "n": 32, "seed": 123},
            "profile_contracts": {"tier": "optimistic", "preset": "C8"},
        }
    )
    a = generate_candidates(spec)
    b = generate_candidates(spec)
    assert [r["cid"] for r in a] == [r["cid"] for r in b]
    assert a[0]["x"] == b[0]["x"]
    assert a[0]["y"] == b[0]["y"]
