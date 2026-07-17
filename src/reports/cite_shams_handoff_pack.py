"""Independence Phase 4.2 — Cite-SHAMS handoff pack.

One-command / one-click export that bundles everything a study needs to **cite
and reproduce** a SHAMS feasibility result without depending on UKAEA PROCESS:

* SHAMS ``VERSION`` (+ best-effort ``git describe``)
* PointInputs + run artifact + SHA-256
* NO-SOLUTION atlas when hard-infeasible
* Release-gate status (**CONDITIONAL**)
* Citation snippet derived from ``CITATION.cff`` (text + BibTeX)
* Limitations pointer + honesty language (PROCESS import optional; METHOD-ONLY)

Reuses existing export / atlas machinery; does **not** duplicate reviewer-pack
physics. L0 risk: none (reads artifacts + repo metadata only).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PACK_SCHEMA = "shams.cite_shams_handoff_pack.v1"
# Frozen epoch so pack content (and zip member mtimes) stay deterministic in tests.
_PACK_EPOCH_UNIX = 0.0

_REPO_ROOT = Path(__file__).resolve().parents[2]

RELEASE_GATE_PATH = (
    _REPO_ROOT / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
)
LIMITATIONS_REL = "docs/LIMITATIONS.md"
CITATION_CFF_NAME = "CITATION.cff"
MIGRATION_GUIDE_REL = "docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"
RETIREMENT_REPORT_REL = "docs/PROCESS_RETIREMENT_REPORT.md"

# Forbidden overclaims inside pack prose / meta.
_FORBIDDEN_PHRASES = (
    "process retired",
    "process is retired",
    "process has been retired",
    "ukaea process is obsolete",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def pretty_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, default=str).encode("utf-8") + b"\n"


def read_shams_version(repo_root: Optional[Path] = None) -> str:
    root = repo_root or _REPO_ROOT
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def git_describe_best_effort(repo_root: Optional[Path] = None) -> Optional[str]:
    """Return ``git describe --dirty --always`` when git is available; else None."""
    root = repo_root or _REPO_ROOT
    try:
        proc = subprocess.run(
            ["git", "describe", "--dirty", "--always"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            desc = (proc.stdout or "").strip()
            return desc or None
    except Exception:
        pass
    # Fallback: GIT_COMMIT file / env (same posture as provenance.py).
    try:
        marker = (root / "GIT_COMMIT").read_text(encoding="utf-8").strip()
        if marker:
            return marker.splitlines()[0].strip()
    except Exception:
        pass
    return None


def _parse_release_verdict(text: str) -> str:
    m = re.search(r"Release verdict:\*\*\s*\*\*([A-Z]+)\*\*", text)
    if m:
        return m.group(1)
    if re.search(r"\bCONDITIONAL\b", text):
        return "CONDITIONAL"
    if re.search(r"\bAPPROVED\b", text) and "CONDITIONAL" not in text:
        return "APPROVED"
    return "UNKNOWN"


def load_release_gate(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = repo_root or _REPO_ROOT
    path = root / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
    if not path.is_file():
        path = RELEASE_GATE_PATH
    verdict = "CONDITIONAL"
    exists = path.is_file()
    if exists:
        try:
            verdict = _parse_release_verdict(path.read_text(encoding="utf-8"))
        except Exception:
            verdict = "CONDITIONAL"
    if verdict == "UNKNOWN":
        verdict = "CONDITIONAL"
    rel = str(path.resolve().relative_to(root.resolve())).replace("\\", "/") if exists else (
        "docs/validation/reports/scientific_release_readiness_20260716.md"
    )
    return {
        "release_status": verdict,
        "path": rel,
        "exists": exists,
        "note": (
            "Scientific release is CONDITIONAL until APPROVED evidence clears documented "
            "waivers — see docs/RELEASE_ARCHIVAL_CHECKLIST.md. Do not claim APPROVED."
        ),
    }


def _cff_field(text: str, key: str) -> Optional[str]:
    m = re.search(rf"(?m)^{re.escape(key)}:\s*[\"']?(.+?)[\"']?\s*$", text)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def parse_citation_cff(cff_text: str) -> Dict[str, Any]:
    title = _cff_field(cff_text, "title") or "SHAMS"
    version = _cff_field(cff_text, "version") or "unknown"
    date_released = _cff_field(cff_text, "date-released") or ""
    license_id = _cff_field(cff_text, "license") or ""
    url = _cff_field(cff_text, "repository-code") or ""
    year = date_released[:4] if len(date_released) >= 4 else ""

    # Authors: first family-names / given-names pair + contributors line.
    authors: List[str] = []
    fam = re.search(r"(?m)^\s+family-names:\s*[\"']?(.+?)[\"']?\s*$", cff_text)
    giv = re.search(r"(?m)^\s+given-names:\s*[\"']?(.+?)[\"']?\s*$", cff_text)
    if fam and giv:
        authors.append(f"{giv.group(1).strip()} {fam.group(1).strip()}")
    name_m = re.search(r"(?m)^\s+-\s+name:\s*[\"']?(.+?)[\"']?\s*$", cff_text)
    if name_m:
        authors.append(name_m.group(1).strip())
    if not authors:
        authors = ["SHAMS Contributors"]

    return {
        "title": title,
        "version": version,
        "date_released": date_released,
        "year": year,
        "license": license_id,
        "url": url,
        "authors": authors,
    }


def citation_text_snippet(meta: Dict[str, Any], *, artifact_sha256: str, shams_version: str) -> str:
    authors = ", ".join(meta.get("authors") or ["SHAMS Contributors"])
    title = meta.get("title") or "SHAMS"
    version = shams_version or meta.get("version") or "unknown"
    year = meta.get("year") or ""
    url = meta.get("url") or ""
    lines = [
        f"{authors} ({year}). {title}. Version {version}." if year else f"{authors}. {title}. Version {version}.",
    ]
    if url:
        lines.append(f"Available at: {url}")
    lines.append(f"Cite SHAMS VERSION `{version}` and run-artifact SHA-256 `{artifact_sha256}`.")
    lines.append(
        "Scientific release status: CONDITIONAL (see docs/LIMITATIONS.md). "
        "PROCESS import is optional; new studies default to citing SHAMS alone."
    )
    lines.append(
        "Parity with UKAEA PROCESS, when referenced, is METHOD-ONLY unless a lab-supplied "
        "NUMERIC dossier is attached — never invent MFILE numbers."
    )
    return "\n".join(lines) + "\n"


def citation_bibtex_snippet(meta: Dict[str, Any], *, artifact_sha256: str, shams_version: str) -> str:
    version = shams_version or meta.get("version") or "unknown"
    cite_key = "shams_" + re.sub(r"[^A-Za-z0-9]+", "_", version).strip("_")
    authors = " and ".join(meta.get("authors") or ["SHAMS Contributors"])
    title = meta.get("title") or "SHAMS"
    year = meta.get("year") or "2026"
    url = meta.get("url") or ""
    note = (
        f"Cite VERSION {version} + artifact SHA-256 {artifact_sha256}. "
        "Scientific release: CONDITIONAL. PROCESS import optional; METHOD-ONLY parity honesty."
    )
    parts = [
        f"@software{{{cite_key},",
        f"  title     = {{{title}}},",
        f"  author    = {{{authors}}},",
        f"  version   = {{{version}}},",
        f"  year      = {{{year}}},",
    ]
    if url:
        parts.append(f"  url       = {{{url}}},")
    parts.append(f"  note      = {{{note}}}")
    parts.append("}")
    return "\n".join(parts) + "\n"


def _honesty_markdown() -> str:
    return """# Cite-SHAMS handoff — honesty

This pack is **SHAMS-native**. New feasibility studies should cite SHAMS `VERSION`
plus the SHA-256 hashes in `manifest.json` / `run_artifact.sha256`.

## PROCESS positioning

* Importing PROCESS results (IN.DAT / MFILE) remains **optional**.
* For new work, PROCESS is at most an **optional proposer**; SHAMS re-evaluates
  and certifies (CCFS). This handoff pack is the default cite/reproduce unit.
* Do **not** claim “PROCESS retired.” Scoped coverage evidence lives in
  `docs/PROCESS_RETIREMENT_REPORT.md` — domains outside that scope remain NOT covered.

## Parity honesty

* PROCESS numeric parity in-repo is **METHOD-ONLY** until a lab lands a licensed MFILE.
* Never invent PROCESS reference numbers.
* If a parity dossier is attached separately, declare METHOD-ONLY vs NUMERIC explicitly.

## Release status

* Scientific release status for this repository is **CONDITIONAL**, not APPROVED.
* See `release_gate.json` and `docs/LIMITATIONS.md`.

## NO-SOLUTION

* Hard-infeasible evaluations include `no_solution_atlas.json` — infeasibility is
  valid science, not a packaging error.
"""


def _readme_markdown(
    *,
    shams_version: str,
    artifact_sha256: str,
    hard_feasible: Optional[bool],
    has_atlas: bool,
) -> str:
    feas = "unknown"
    if hard_feasible is True:
        feas = "hard-feasible"
    elif hard_feasible is False:
        feas = "hard-infeasible (NO-SOLUTION)"
    atlas_line = (
        "- `no_solution_atlas.json` — mechanism attribution for this infeasible point\n"
        if has_atlas
        else ""
    )
    return f"""# Cite-SHAMS handoff pack

SHAMS version: `{shams_version}`  
Run artifact SHA-256: `{artifact_sha256}`  
Feasibility: **{feas}**  
Scientific release: **CONDITIONAL**

## How to cite

1. Use `citation.txt` or `citation.bib` (derived from `CITATION.cff`).
2. Always include SHAMS `VERSION` **and** the run-artifact SHA-256 above.
3. Read `LIMITATIONS_POINTER.md` and `HONESTY.md` before claiming PROCESS agreement.

## Files

- `VERSION` — software version string
- `provenance.json` — version, optional git describe, pack schema
- `point_inputs.json` — PointInputs used for this evaluation
- `run_artifact.json` — full SHAMS run artifact
- `run_artifact.sha256` — SHA-256 of `run_artifact.json` bytes
- `evaluation_export.json` — deck export slice (reuses UI export-bundle builder)
{atlas_line}- `CITATION.cff` / `citation.txt` / `citation.bib` — software citation
- `release_gate.json` — CONDITIONAL release status
- `HONESTY.md` — PROCESS-optional + METHOD-ONLY language
- `manifest.json` / `MANIFEST_SHA256.txt` — per-file integrity hashes
- `pack_meta.json` — pack schema + `pack_sha256`

## Reproduce

1. Install SHAMS at the cited `VERSION` (see repository README).
2. Load `point_inputs.json` into Point Designer (or evaluate via `Evaluator.evaluate`).
3. Compare outputs / constraints to `run_artifact.json` under the same frozen L0.

PROCESS is not required to cite or reproduce this result.
"""


def _limitations_pointer() -> str:
    return f"""# Limitations pointer

Full public limitations: `{LIMITATIONS_REL}`

Also see:

* `{MIGRATION_GUIDE_REL}` — PROCESS → SHAMS migration (optional import)
* `{RETIREMENT_REPORT_REL}` — scoped retirement evidence (never a blanket claim)
* `docs/RELEASE_ARCHIVAL_CHECKLIST.md` — CONDITIONAL → APPROVED gates

Cite SHAMS VERSION + artifact SHA-256. Do not invent MFILE numbers.
"""


def _hard_feasible_from_artifact(artifact: Dict[str, Any]) -> Optional[bool]:
    kpis = artifact.get("kpis")
    if isinstance(kpis, dict) and "feasible_hard" in kpis:
        return bool(kpis.get("feasible_hard"))
    cs = artifact.get("constraints_summary")
    if isinstance(cs, dict) and "feasible" in cs:
        return bool(cs.get("feasible"))
    cons = artifact.get("constraints")
    if isinstance(cons, list) and cons:
        hard_fail = False
        saw_hard = False
        for c in cons:
            if not isinstance(c, dict):
                continue
            sev = str(c.get("severity") or "").lower()
            if sev != "hard":
                continue
            saw_hard = True
            if not c.get("passed", True):
                hard_fail = True
        if saw_hard:
            return not hard_fail
    return None


def _point_inputs_from_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    inputs = artifact.get("inputs")
    if isinstance(inputs, dict):
        return dict(inputs)
    return {}


def _atlas_from_artifact(artifact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    atlas = artifact.get("no_solution_atlas")
    if isinstance(atlas, dict) and atlas.get("schema") == "no_solution_atlas.v1":
        if str(atlas.get("verdict", "")) != "FEASIBLE":
            return atlas
    return None


def _build_evaluation_export(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Reuse UI export-bundle builder for a deterministic evaluation slice."""
    try:
        from ui.export_bundle import build_export_bundle
    except ImportError:  # pragma: no cover
        from export_bundle import build_export_bundle  # type: ignore

    outputs = artifact.get("outputs") if isinstance(artifact.get("outputs"), dict) else {}
    inputs = _point_inputs_from_artifact(artifact)
    constraints = artifact.get("constraints")
    atlas = artifact.get("no_solution_atlas") if isinstance(artifact.get("no_solution_atlas"), dict) else None
    design_intent = None
    if isinstance(inputs, dict):
        design_intent = inputs.get("design_intent") or inputs.get("intent")
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    if design_intent is None and isinstance(meta, dict):
        design_intent = meta.get("design_intent")

    bundle = build_export_bundle(
        deck="Cite-SHAMS handoff",
        outputs=outputs if isinstance(outputs, dict) else {},
        inputs=inputs,
        constraints=constraints,
        design_intent=str(design_intent) if design_intent else None,
        no_solution_atlas=atlas if isinstance(atlas, dict) else None,
    )
    # Drop wall-clock timestamp for pack determinism; keep schema fields + hash body.
    if isinstance(bundle, dict):
        bundle = dict(bundle)
        bundle.pop("timestamp_utc", None)
        # Recompute manifest over the timestamp-free payload.
        body = {k: v for k, v in bundle.items() if k != "manifest_sha256"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        bundle["manifest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return bundle


def _zip_datetime_from_unix(created_unix: float) -> Tuple[int, int, int, int, int, int]:
    """Convert unix epoch to zip date_time tuple (UTC)."""
    import time as _time

    t = _time.gmtime(float(created_unix) if created_unix is not None else 0.0)
    # zip supports 1980+; clamp earlier years.
    year = max(1980, int(t.tm_year))
    return (year, int(t.tm_mon), int(t.tm_mday), int(t.tm_hour), int(t.tm_min), int(t.tm_sec))


def validate_pack_honesty(meta: Dict[str, Any], files: Dict[str, bytes]) -> List[str]:
    """Return honesty issues (empty = PASS)."""
    issues: List[str] = []
    if meta.get("schema") != PACK_SCHEMA:
        issues.append(f"schema must be {PACK_SCHEMA}")
    if meta.get("process_retired_claimed") is True:
        issues.append("process_retired_claimed must be false")
    if meta.get("release_status") not in ("CONDITIONAL", "APPROVED"):
        issues.append("release_status missing or invalid")
    # Currently APPROVED is not evidenced — flag if claimed without note.
    if meta.get("release_status") == "APPROVED" and not meta.get("approved_evidenced"):
        issues.append("release_status APPROVED is not evidenced; keep CONDITIONAL")
    if meta.get("parity_honesty") not in (None, "METHOD-ONLY", "NUMERIC", "NOT_REFERENCED"):
        issues.append("parity_honesty must be METHOD-ONLY / NUMERIC / NOT_REFERENCED")
    if meta.get("parity_honesty") == "NUMERIC" and not meta.get("numeric_parity_dossier_attached"):
        issues.append("NUMERIC parity claimed without attached dossier")

    honesty = files.get("HONESTY.md", b"").decode("utf-8", errors="ignore")
    honesty_l = honesty.lower()
    if "method-only" not in honesty_l:
        issues.append("HONESTY.md must state METHOD-ONLY parity honesty")
    if "optional" not in honesty_l or "process" not in honesty_l:
        issues.append("HONESTY.md must state PROCESS import is optional")
    if "conditional" not in honesty_l:
        issues.append("HONESTY.md must state CONDITIONAL release")
    # Require explicit refusal of blanket retirement (phrase may appear only in refusal).
    if "do **not** claim" not in honesty_l and "do not claim" not in honesty_l:
        issues.append("HONESTY.md must refuse blanket PROCESS-retired claims")
    # Affirmative overclaim: "PROCESS is retired" without nearby refusal context.
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in honesty_l:
            # OK only when the surrounding sentence refuses the claim.
            if "do not claim" not in honesty_l and "do **not** claim" not in honesty_l:
                issues.append(f"forbidden overclaim phrasing: {phrase!r}")

    cite = files.get("citation.txt", b"").decode("utf-8", errors="ignore").lower()
    if "method-only" not in cite:
        issues.append("citation.txt must mention METHOD-ONLY honesty")
    if "conditional" not in cite:
        issues.append("citation.txt must mention CONDITIONAL release")
    return issues


def build_cite_shams_handoff_pack(
    artifact: Dict[str, Any],
    *,
    repo_root: Optional[Path] = None,
    created_unix: float = _PACK_EPOCH_UNIX,
    include_git_describe: bool = True,
    parity_honesty: str = "METHOD-ONLY",
) -> Dict[str, Any]:
    """Build a deterministic Cite-SHAMS handoff ZIP from a run artifact.

    Returns dict with ``zip_bytes``, ``manifest``, ``pack_meta``, ``files`` (name→bytes),
    ``pack_sha256``, and honesty fields.
    """
    if not isinstance(artifact, dict):
        raise ValueError("artifact must be a dict")

    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    version = read_shams_version(root)
    git_desc = git_describe_best_effort(root) if include_git_describe else None

    art_bytes = pretty_json_bytes(artifact)
    art_sha = sha256_bytes(art_bytes)
    inputs = _point_inputs_from_artifact(artifact)
    hard_feasible = _hard_feasible_from_artifact(artifact)
    atlas = _atlas_from_artifact(artifact)
    # Also stamp atlas when hard-infeasible but missing on artifact (reuse atlas builder).
    if atlas is None and hard_feasible is False:
        try:
            try:
                from diagnostics.no_solution_atlas import build_no_solution_atlas  # type: ignore
            except ImportError:
                from src.diagnostics.no_solution_atlas import build_no_solution_atlas
            outputs = artifact.get("outputs") if isinstance(artifact.get("outputs"), dict) else {}
            built = build_no_solution_atlas(outputs or {}, design_intent=None)
            if str(built.get("verdict", "")) == "INFEASIBLE":
                atlas = built
        except Exception:
            atlas = None

    release = load_release_gate(root)
    cff_path = root / CITATION_CFF_NAME
    cff_text = cff_path.read_text(encoding="utf-8") if cff_path.is_file() else ""
    cff_meta = parse_citation_cff(cff_text) if cff_text else {
        "title": "SHAMS",
        "version": version,
        "authors": ["SHAMS Contributors"],
        "year": "2026",
        "url": "",
    }

    eval_export = _build_evaluation_export(artifact)
    # Force deterministic timestamp_utc already stripped inside helper.

    provenance = {
        "schema": PACK_SCHEMA,
        "shams_version": version,
        "git_describe": git_desc,
        "created_unix": float(created_unix),
        "process_role": "optional_proposer_export_only",
        "parity_honesty": parity_honesty,
        "release_status": release.get("release_status"),
        "run_artifact_sha256": art_sha,
        "hard_feasible": hard_feasible,
        "has_no_solution_atlas": atlas is not None,
    }

    pack_meta_core = {
        "schema": PACK_SCHEMA,
        "shams_version": version,
        "git_describe": git_desc,
        "created_unix": float(created_unix),
        "run_artifact_sha256": art_sha,
        "hard_feasible": hard_feasible,
        "has_no_solution_atlas": atlas is not None,
        "release_status": release.get("release_status"),
        "parity_honesty": parity_honesty,
        "process_retired_claimed": False,
        "process_import_required": False,
        "approved_evidenced": False,
        "numeric_parity_dossier_attached": False,
    }

    files: Dict[str, bytes] = {
        "VERSION": (version + "\n").encode("utf-8"),
        "provenance.json": pretty_json_bytes(provenance),
        "point_inputs.json": pretty_json_bytes(inputs),
        "run_artifact.json": art_bytes,
        "run_artifact.sha256": (art_sha + "\n").encode("utf-8"),
        "evaluation_export.json": pretty_json_bytes(eval_export),
        "CITATION.cff": (cff_text.encode("utf-8") if cff_text else b""),
        "citation.txt": citation_text_snippet(
            cff_meta, artifact_sha256=art_sha, shams_version=version
        ).encode("utf-8"),
        "citation.bib": citation_bibtex_snippet(
            cff_meta, artifact_sha256=art_sha, shams_version=version
        ).encode("utf-8"),
        "release_gate.json": pretty_json_bytes(release),
        "LIMITATIONS_POINTER.md": _limitations_pointer().encode("utf-8"),
        "HONESTY.md": _honesty_markdown().encode("utf-8"),
        "README.md": _readme_markdown(
            shams_version=version,
            artifact_sha256=art_sha,
            hard_feasible=hard_feasible,
            has_atlas=atlas is not None,
        ).encode("utf-8"),
    }
    if atlas is not None:
        files["no_solution_atlas.json"] = pretty_json_bytes(atlas)

    # Manifest over content files (excluding manifest itself + pack_meta).
    manifest_files = {
        name: {"sha256": sha256_bytes(data), "bytes": len(data)}
        for name, data in sorted(files.items())
    }
    manifest = {
        "schema": "shams.cite_shams_handoff_manifest.v1",
        "pack_schema": PACK_SCHEMA,
        "shams_version": version,
        "run_artifact_sha256": art_sha,
        "files": manifest_files,
    }
    files["manifest.json"] = pretty_json_bytes(manifest)

    manifest_lines = [
        f"# Cite-SHAMS handoff MANIFEST_SHA256 — {version}",
        f"# run_artifact.sha256 = {art_sha}",
        "",
    ]
    for name, row in sorted(manifest_files.items()):
        manifest_lines.append(f"{row['sha256']}  {name}")
    # Include manifest.json hash after it is written.
    manifest_lines.append(f"{sha256_bytes(files['manifest.json'])}  manifest.json")
    files["MANIFEST_SHA256.txt"] = ("\n".join(manifest_lines) + "\n").encode("utf-8")

    # pack_sha256 over timestamp-stable content (all files except pack_meta).
    pack_hash_payload = {
        name: sha256_bytes(data) for name, data in sorted(files.items())
    }
    pack_sha = sha256_bytes(stable_json_bytes(pack_hash_payload))
    pack_meta = dict(pack_meta_core)
    pack_meta["pack_sha256"] = pack_sha
    pack_meta["n_files"] = len(files) + 1  # + pack_meta.json
    files["pack_meta.json"] = pretty_json_bytes(pack_meta)

    honesty_issues = validate_pack_honesty(pack_meta, files)
    if honesty_issues:
        raise ValueError("cite-SHAMS handoff honesty gate failed: " + "; ".join(honesty_issues))

    dt = _zip_datetime_from_unix(created_unix)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(filename=name, date_time=dt)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

    return {
        "schema": PACK_SCHEMA,
        "shams_version": version,
        "pack_sha256": pack_sha,
        "run_artifact_sha256": art_sha,
        "hard_feasible": hard_feasible,
        "has_no_solution_atlas": atlas is not None,
        "release_status": release.get("release_status"),
        "parity_honesty": parity_honesty,
        "process_retired_claimed": False,
        "manifest": manifest,
        "pack_meta": pack_meta,
        "files": files,
        "zip_bytes": zbuf.getvalue(),
        "suggested_filename": f"shams_cite_handoff_{version}_{art_sha[:12]}.zip",
    }


def write_cite_shams_handoff_pack(
    artifact: Dict[str, Any],
    out_zip: Path,
    *,
    repo_root: Optional[Path] = None,
    created_unix: float = _PACK_EPOCH_UNIX,
    include_git_describe: bool = True,
) -> Dict[str, Any]:
    """Build pack and write ZIP to ``out_zip``; return pack result dict."""
    pack = build_cite_shams_handoff_pack(
        artifact,
        repo_root=repo_root,
        created_unix=created_unix,
        include_git_describe=include_git_describe,
    )
    out_path = Path(out_zip)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pack["zip_bytes"])
    return pack


def main(argv: Optional[List[str]] = None) -> int:
    """CLI: ``python -m reports.cite_shams_handoff_pack ARTIFACT.json -o pack.zip``."""
    import argparse

    parser = argparse.ArgumentParser(description="Build a Cite-SHAMS handoff pack ZIP")
    parser.add_argument("artifact", type=Path, help="Path to shams run artifact JSON")
    parser.add_argument("-o", "--out", type=Path, required=True, help="Output ZIP path")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--no-git-describe", action="store_true")
    args = parser.parse_args(argv)

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    pack = write_cite_shams_handoff_pack(
        art,
        args.out,
        repo_root=args.repo_root,
        include_git_describe=not args.no_git_describe,
    )
    print(f"wrote {args.out}")
    print(f"pack_sha256={pack['pack_sha256']}")
    print(f"run_artifact_sha256={pack['run_artifact_sha256']}")
    print(f"release_status={pack['release_status']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
