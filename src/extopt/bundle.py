from __future__ import annotations

import csv
import io
import json
import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)  # deterministic ZIP timestamps


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _json_bytes(obj: Any) -> bytes:
    # Deterministic JSON serialization
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


@dataclass(frozen=True)
class BundleCandidate:
    cid: str
    artifact: Dict[str, Any]
    cache_hit: Optional[bool] = None


@dataclass(frozen=True)
class BundleProvenance:
    schema: str = "extopt_bundle_provenance.v1"
    shams_version: str = "unknown"
    evaluator_label: str = "unknown"
    intent: str = "unknown"
    family_name: str = "unknown"
    family_source: str = ""  # e.g. yaml path or upload name (optional)


def _index_row(c: BundleCandidate) -> Dict[str, Any]:
    art = c.artifact if isinstance(c.artifact, dict) else {}
    kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
    return {
        "cid": c.cid,
        "verdict": str(art.get("verdict", "")),
        "feasible_hard": bool(kpis.get("feasible_hard", False)),
        "worst_hard_margin": _safe_float(art.get("worst_hard_margin", kpis.get("min_hard_margin"))),
        "dominant_constraint": str(art.get("dominant_constraint", "")),
        "dominant_mechanism": str(art.get("dominant_mechanism", "")),
        "cache_hit": (bool(c.cache_hit) if c.cache_hit is not None else ""),
    }


def build_index(candidates: List[BundleCandidate]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows = [_index_row(c) for c in candidates]
    rows = sorted(rows, key=lambda r: str(r.get("cid", "")))
    summary = {
        "schema": "extopt_bundle_index_summary.v1",
        "n_total": int(len(rows)),
        "n_pass": int(sum(1 for r in rows if str(r.get("verdict", "")).upper().startswith("PASS"))),
        "n_fail": int(sum(1 for r in rows if str(r.get("verdict", "")).upper().startswith("FAIL"))),
    }
    return rows, summary


def export_bundle_zip(
    *,
    out_zip: Path,
    candidates: List[BundleCandidate],
    provenance: BundleProvenance,
    include_artifact_json: bool = True,
    include_evidence_packs: bool = False,
    evidence_pack_paths: Optional[Dict[str, Path]] = None,
) -> Path:
    """Export a single deterministic ZIP bundle.

    Contents:
    - index.csv
    - index.json
    - manifest.json (hashes + provenance)
    - artifacts/<cid>.json (optional)
    - evidence_packs/<cid>.zip (optional)

    Determinism:
    - JSON is sort_keys + stable formatting
    - ZIP member timestamps are fixed
    - ZIP member order is sorted
    """
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    evidence_pack_paths = evidence_pack_paths or {}

    index_rows, index_summary = build_index(candidates)
    index_json_obj = {
        "schema": "extopt_bundle_index.v1",
        "summary": index_summary,
        "rows": index_rows,
    }

    members: List[Tuple[str, bytes]] = []

    # index.csv
    csv_buf = io.StringIO()
    fieldnames = list(index_rows[0].keys()) if index_rows else [
        "cid", "verdict", "feasible_hard", "worst_hard_margin", "dominant_constraint", "dominant_mechanism", "cache_hit"
    ]
    w = csv.DictWriter(csv_buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for r in index_rows:
        rr = {k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames}
        w.writerow(rr)
    members.append(("index.csv", csv_buf.getvalue().encode("utf-8")))

    # index.json
    members.append(("index.json", _json_bytes(index_json_obj)))

    # artifacts
    if include_artifact_json:
        for c in sorted(candidates, key=lambda x: str(x.cid)):
            members.append((f"artifacts/{c.cid}.json", _json_bytes(c.artifact)))

    # evidence packs
    if include_evidence_packs:
        for cid, p in sorted(evidence_pack_paths.items(), key=lambda kv: str(kv[0])):
            try:
                pb = Path(p).read_bytes()
                members.append((f"evidence_packs/{cid}.zip", pb))
            except Exception:
                pass

    # manifest
    manifest_entries = []
    for name, b in sorted(members, key=lambda t: t[0]):
        manifest_entries.append({"path": name, "sha256": _sha256_bytes(b), "bytes": int(len(b))})

    manifest = {
        "schema": "extopt_bundle_manifest.v1",
        "provenance": {
            "schema": provenance.schema,
            "shams_version": provenance.shams_version,
            "evaluator_label": provenance.evaluator_label,
            "intent": provenance.intent,
            "family_name": provenance.family_name,
            "family_source": provenance.family_source,
        },
        "entries": manifest_entries,
    }
    members.append(("manifest.json", _json_bytes(manifest)))

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, b in sorted(members, key=lambda t: t[0]):
            zi = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_DATETIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, b)

    return out_zip

# ---- v273 compatibility wrapper (non-breaking) ----
def export_bundle_zip_v273(*, out_zip, candidates, provenance, include_artifact_json=True,
                          include_evidence_packs=False, evidence_pack_paths=None,
                          problem_spec_json=None, runspec_json=None, optimizer_trace_json=None):
    """Backward-compatible exporter that also writes problem_spec/runspec/optimizer_trace."""
    if evidence_pack_paths is None:
        evidence_pack_paths = {}
    export_bundle_zip(
        out_zip=out_zip,
        candidates=candidates,
        provenance=provenance,
        include_artifact_json=include_artifact_json,
        include_evidence_packs=include_evidence_packs,
        evidence_pack_paths=evidence_pack_paths,
    )
    # Append extra JSON files deterministically
    import zipfile, json as _json
    with zipfile.ZipFile(out_zip, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        if problem_spec_json is not None:
            zf.writestr("problem_spec.json", _json.dumps(problem_spec_json, sort_keys=True, indent=2))
        if runspec_json is not None:
            zf.writestr("runspec.json", _json.dumps(runspec_json, sort_keys=True, indent=2))
        if optimizer_trace_json is not None:
            zf.writestr("optimizer_trace.json", _json.dumps(optimizer_trace_json, sort_keys=True, indent=2))
