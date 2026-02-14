from __future__ import annotations

from pathlib import Path
import json
import hashlib
import tempfile

from tools.regulatory_pack import export_regulatory_evidence_pack_zip


def _sha256_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()


def test_regulatory_pack_is_deterministic(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    artifact = {
        "shams_version": "test",
        "intent": "Reactor",
        "verdict": "INFEASIBLE",
        "magnet_regime": "HTS",
        "exhaust_regime": "attached",
        "authority_dominance": {
            "schema": "authority_dominance.v1",
            "dominant_authority": "MAGNET",
            "dominant_constraint_id": "MAG_TF_STRESS_LIMIT",
            "dominant_margin_min": -0.10,
        },
        "constraints": [{"id":"X", "margin":-1.0, "class":"HARD"}],
    }

    z1 = tmp_path/"a.zip"
    z2 = tmp_path/"b.zip"

    export_regulatory_evidence_pack_zip(repo_root, artifact, z1)
    export_regulatory_evidence_pack_zip(repo_root, artifact, z2)

    assert _sha256_bytes(z1.read_bytes()) == _sha256_bytes(z2.read_bytes())
