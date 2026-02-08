from __future__ import annotations
"""Authority Pack (v119)

Goal: produce a single publishable bundle that captures:
- versioning + patch notes
- environment snapshot (best-effort)
- command log and pointers to generated artifacts
- audit pack + downstream bundle + handoff packs (if provided)
- integrity manifest (SHA256)

No physics/solver changes. Additive export only.
"""

from typing import Any, Dict, Optional, List
import time, json, hashlib, zipfile, os, subprocess, sys
from io import BytesIO
from pathlib import Path

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _best_effort_pip_freeze() -> Optional[str]:
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], stderr=subprocess.STDOUT, text=True)
        return out
    except Exception:
        return None

def _methods_appendix_text(version: str) -> str:
    # intentionally generic + stable; does not assert new physics
    return f"""# SHAMS Methods Appendix (auto-generated)

Version: {version}

## Philosophy
SHAMS is constraint-first and audit-ready. External optimizers are treated as proposal generators only; SHAMS remains the authority by re-evaluating physics and constraints and exporting transparent evidence.

## Determinism
- Feasibility and constraint evaluation is deterministic given inputs and version.
- Preference annotations and Pareto sets are post-processing (no optimization).
- Tolerance envelopes are bounded and deterministic (no probabilistic interpretation).

## Artifact Types
- shams_run_artifact: inputs, outputs, constraints, metadata, and summaries.
- audit packs: integrity and reproducibility evidence.
- decision packs: candidate tables + manifests + (optional) justification.
- optimizer downstream bundles: evaluated proposals + envelopes + decision pack.

## Reproduce
Use the included `requirements_freeze.txt` (best-effort) plus repository README to recreate the environment. Then rerun the same commands listed in `command_log.txt`.
"""

def build_authority_pack(
    *,
    repo_root: str,
    version: str = "v119",
    audit_pack_zip: Optional[bytes] = None,
    downstream_bundle_zip: Optional[bytes] = None,
    handoff_pack_zip: Optional[bytes] = None,
    extra_files: Optional[Dict[str, bytes]] = None,
    command_log: Optional[List[str]] = None,
) -> Dict[str, Any]:
    created = _created_utc()
    repo_path = Path(repo_root)

    # collect version files (best-effort)
    version_txt = (repo_path / "VERSION").read_text(encoding="utf-8", errors="replace") if (repo_path/"VERSION").exists() else version
    patch_notes = []
    for fn in sorted(repo_path.glob("PATCH_NOTES_v*.md")):
        try:
            patch_notes.append((fn.name, fn.read_bytes()))
        except Exception:
            pass

    freeze = _best_effort_pip_freeze()
    freeze_bytes = (freeze or "pip freeze unavailable").encode("utf-8")

    cmd_lines = command_log or [
        "python -m tools.ui_self_test --outdir out_ui_self_test",
        "python -m tools.verify_package",
        "python -m tools.verify_figures",
        "python -m tools.tests.test_plot_layout",
        "python -m tools.regression_suite",
    ]
    cmd_bytes = ("\n".join(cmd_lines) + "\n").encode("utf-8")

    methods_bytes = _methods_appendix_text(version_txt.strip()).encode("utf-8")

    files: Dict[str, bytes] = {}
    files["VERSION"] = version_txt.encode("utf-8") if isinstance(version_txt, str) else str(version_txt).encode("utf-8")
    files["requirements_freeze.txt"] = freeze_bytes
    files["command_log.txt"] = cmd_bytes
    files["methods_appendix.md"] = methods_bytes

    for name, b in patch_notes:
        files[f"patch_notes/{name}"] = b

    if isinstance(audit_pack_zip, (bytes, bytearray)):
        files["audit_pack.zip"] = bytes(audit_pack_zip)
    if isinstance(downstream_bundle_zip, (bytes, bytearray)):
        files["optimizer_downstream_bundle_v118.zip"] = bytes(downstream_bundle_zip)
    if isinstance(handoff_pack_zip, (bytes, bytearray)):
        files["handoff_pack.zip"] = bytes(handoff_pack_zip)

    if isinstance(extra_files, dict):
        for k,v in extra_files.items():
            if isinstance(k, str) and isinstance(v, (bytes, bytearray)):
                files[k] = bytes(v)

    manifest = {
        "kind": "shams_authority_pack_manifest",
        "version": version,
        "created_utc": created,
        "files": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k,v in files.items()},
        "notes": [
            "Authority pack: publishable evidence bundle. Additive export only.",
            "requirements_freeze.txt is best-effort and may vary across systems.",
        ],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    files["manifest.json"] = manifest_bytes

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k, v)

    return {
        "kind":"shams_authority_pack",
        "version": version,
        "created_utc": created,
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
    }
