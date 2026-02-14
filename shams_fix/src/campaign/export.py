from __future__ import annotations

"""Campaign bundle export (v363.0).

Produces a single ZIP suitable for external optimizers and reviewers.

Bundle contents
---------------
- campaign.json: canonical campaign spec
- candidates.csv / candidates.jsonl
- assumptions.json: fixed inputs + evaluator label + fingerprints
- contract_fingerprints.json: profile-contract fingerprint (v362)
- MANIFEST_SHA256.txt: per-file hashes within the bundle
- README_CAMPAIGN.md: consumption instructions

© 2026 Afshin Arjhangmehr
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import json
import tempfile
import zipfile

try:
    from ..analysis.profile_contracts_v362 import load_profile_contracts_v362  # type: ignore
except Exception:
    from analysis.profile_contracts_v362 import load_profile_contracts_v362  # type: ignore

from .spec import CampaignSpec
from .generate import generate_candidates


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _write_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _write_candidates_csv(path: Path, candidates: List[Dict[str, Any]], *, var_names: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cid"] + list(var_names))
        w.writeheader()
        for row in candidates:
            out = {"cid": row.get("cid", "")}
            for vn in var_names:
                out[vn] = row.get(vn, "")
            w.writerow(out)


def _write_candidates_jsonl(path: Path, candidates: List[Dict[str, Any]], *, var_names: List[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in candidates:
            out = {"cid": row.get("cid", "")}
            for vn in var_names:
                out[vn] = row.get(vn, None)
            f.write(json.dumps(out, sort_keys=True) + "\n")


def _bundle_manifest(files: List[Path]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in files:
        out[p.name] = _sha256_file(p)
    return out


def export_campaign_bundle(
    spec: CampaignSpec,
    *,
    out_zip: Optional[Path] = None,
) -> Path:
    """Create a campaign bundle ZIP.

    Returns the path to the ZIP.
    """
    spec.validate()
    candidates = generate_candidates(spec)
    var_names = [v.name for v in spec.variables]

    contract, contract_sha = load_profile_contracts_v362()
    fingerprints = {
        "profile_contracts_v362_sha256": contract_sha,
        "profile_contracts_tier": spec.profile_contracts.tier,
        "profile_contracts_preset": spec.profile_contracts.preset,
    }

    assumptions = {
        "schema": "shams_campaign_assumptions.v1",
        "campaign_name": spec.name,
        "intent": spec.intent,
        "evaluator_label": spec.evaluator_label,
        "fixed_inputs": dict(spec.fixed_inputs),
        "fingerprints": fingerprints,
        "notes": "External optimizers may propose inputs, but cannot modify physics truth.",
    }

    readme = (
        "SHAMS Campaign Pack (v363.0)\n"
        "==========================\n\n"
        "This bundle is intended for external optimizers and reviewer replication.\n\n"
        "Files\n"
        "-----\n"
        "- campaign.json: canonical campaign spec\n"
        "- candidates.csv / candidates.jsonl: candidate inputs (CID + variables)\n"
        "- assumptions.json: fixed inputs and fingerprints (must be preserved)\n"
        "- contract_fingerprints.json: profile contract fingerprints\n"
        "- MANIFEST_SHA256.txt: per-file hashes\n\n"
        "Evaluation\n"
        "----------\n"
        "Run deterministic evaluation using:\n"
        "  python -m src.campaign.cli eval --campaign campaign.json --candidates candidates.csv --out results.jsonl\n"
    )

    with tempfile.TemporaryDirectory(prefix="shams_campaign_") as td:
        tdir = Path(td)
        p_campaign = tdir / "campaign.json"
        p_csv = tdir / "candidates.csv"
        p_jsonl = tdir / "candidates.jsonl"
        p_assum = tdir / "assumptions.json"
        p_fp = tdir / "contract_fingerprints.json"
        p_readme = tdir / "README_CAMPAIGN.md"

        _write_json(p_campaign, spec.to_dict())
        _write_candidates_csv(p_csv, candidates, var_names=var_names)
        _write_candidates_jsonl(p_jsonl, candidates, var_names=var_names)
        _write_json(p_assum, assumptions)
        _write_json(p_fp, fingerprints)
        p_readme.write_text(readme, encoding="utf-8")

        files = [p_campaign, p_csv, p_jsonl, p_assum, p_fp, p_readme]
        manifest = _bundle_manifest(files)
        p_manifest = tdir / "MANIFEST_SHA256.txt"
        p_manifest.write_text(
            "\n".join([f"{manifest[k]}  {k}" for k in sorted(manifest.keys())]) + "\n",
            encoding="utf-8",
        )
        files.append(p_manifest)

        if out_zip is None:
            out_zip = Path.cwd() / f"{spec.name}_campaign_pack.zip"
        out_zip = Path(out_zip)
        out_zip.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, arcname=p.name)

    return out_zip
