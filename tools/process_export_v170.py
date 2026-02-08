from __future__ import annotations
"""Interoperability Dominance: PROCESS Downstream Export (v170)

Intent:
- Make SHAMS the upstream authority: generate SHAMS studies and export a PROCESS-like artifact pack
  so PROCESS (or other tools) can be used strictly as downstream post-processor.
- This is not a PROCESS reimplementation. It exports *compatible-looking* tables and a minimal
  structured mapping, without attempting to mirror PROCESS physics.

Inputs:
- run_artifact (required): shams_run_artifact
- optional completion_pack_v163 (recommended)
- optional citation_bundle_v168 (recommended)

Outputs:
- kind: shams_process_export_manifest, version v170
- plus a zip bytes pack containing:
  - process_like_inputs.csv
  - process_like_outputs.csv
  - mapping_v170.json
  - README.md
  - manifest.json (sha256 per file)

Safety:
- Export/packaging only. No solver/physics changes.
"""

from typing import Any, Dict, Optional, List, Tuple
import json, time, hashlib, io, zipfile

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        return str(x)
    except Exception:
        return ""

def _flatten(d: Any, prefix: str="") -> Dict[str,str]:
    out={}
    if isinstance(d, dict):
        for k,v in d.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, p))
    elif isinstance(d, list):
        for i,v in enumerate(d):
            p=f"{prefix}[{i}]"
            out.update(_flatten(v, p))
    else:
        out[prefix]=_safe_str(d)
    return out

def _csv_row(keys: List[str], row: Dict[str,str]) -> str:
    # minimal CSV escaping
    def esc(s: str) -> str:
        s = "" if s is None else str(s)
        if any(c in s for c in [",", "\n", "\r", '"']):
            s = '"' + s.replace('"', '""') + '"'
        return s
    return ",".join(esc(row.get(k,"")) for k in keys) + "\n"

def _run_to_process_mapping(run_artifact: Dict[str,Any]) -> Dict[str,Any]:
    # A conservative mapping of common tokamak-ish scalars where names exist in SHAMS inputs.
    inputs = run_artifact.get("inputs") or run_artifact.get("_inputs") or {}
    metrics = run_artifact.get("metrics") or {}
    constraints = run_artifact.get("constraints") or []

    # Attempt to grab common names. We keep SHAMS names as canonical; PROCESS names are "aliases".
    candidates = [
        ("R0", ["R0","R","major_radius","R_major"]),
        ("a", ["a","minor_radius","r_minor"]),
        ("B0", ["B0","Bt","B_t","Btor"]),
        ("Ip", ["Ip","plasma_current","I_p"]),
        ("kappa", ["kappa","elongation"]),
        ("delta", ["delta","triangularity"]),
        ("q95", ["q95","q_95"]),
        ("P_fus", ["P_fus","fusion_power","Pfus"]),
        ("Q", ["Q","gain"]),
        ("ne0", ["ne0","n_e0","n0"]),
        ("Te0", ["Te0","T_e0","T0"]),
    ]
    shams_to_process={}
    for proc_name, keys in candidates:
        val=None
        for k in keys:
            if k in inputs:
                val=inputs.get(k)
                break
            if k in metrics:
                val=metrics.get(k)
                break
        if val is not None:
            shams_to_process[proc_name] = {"value": val, "source": "inputs" if k in (inputs or {}) else "metrics", "shams_key": k}

    # Constraints table: name, margin, value if present
    cons_rows=[]
    if isinstance(constraints, list):
        for c in constraints:
            if not isinstance(c, dict): 
                continue
            cons_rows.append({
                "name": _safe_str(c.get("name")),
                "margin": _safe_str(c.get("margin")),
                "value": _safe_str(c.get("value")),
                "limit": _safe_str(c.get("limit")),
                "sense": _safe_str(c.get("sense")),
            })

    return {
        "kind":"shams_process_mapping",
        "version":"v170",
        "issued_utc": _utc(),
        "mapping": {
            "process_alias_scalars": shams_to_process,
            "constraints_table": cons_rows[:300],
            "notes": [
                "This mapping is an interoperability shim: it exports PROCESS-like tables without duplicating PROCESS physics.",
                "SHAMS remains the source of truth; PROCESS is treated as downstream post-processor.",
            ],
        },
    }

def build_process_export_pack(
    *,
    run_artifact: Dict[str,Any],
    completion_pack_v163: Optional[Dict[str,Any]] = None,
    citation_bundle_v168: Optional[Dict[str,Any]] = None,
    policy: Optional[Dict[str,Any]] = None,
) -> Dict[str,Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind")=="shams_run_artifact"):
        raise ValueError("run_artifact must be a shams_run_artifact dict")

    policy = policy if isinstance(policy, dict) else {}
    issued=_utc()

    mapping=_run_to_process_mapping(run_artifact)

    # Build PROCESS-like input/output tables (one-row CSV)
    flat_inputs=_flatten(run_artifact.get("inputs") or {}, prefix="inputs")
    flat_assum=_flatten(run_artifact.get("assumptions") or {}, prefix="assumptions")
    flat_solver=_flatten(run_artifact.get("solver") or run_artifact.get("solver_meta") or {}, prefix="solver")
    in_row={**flat_inputs, **flat_assum, **flat_solver}
    in_keys=sorted(in_row.keys())

    flat_metrics=_flatten(run_artifact.get("metrics") or {}, prefix="metrics")
    out_row={**flat_metrics, "min_margin": _safe_str(run_artifact.get("min_margin")), "dominant_constraint": _safe_str(run_artifact.get("dominant_constraint"))}
    out_keys=sorted(out_row.keys())

    inputs_csv="".join([",".join(in_keys)+"\n", _csv_row(in_keys, in_row)])
    outputs_csv="".join([",".join(out_keys)+"\n", _csv_row(out_keys, out_row)])

    # README
    sid=""
    if isinstance(citation_bundle_v168, dict):
        sid = str((citation_bundle_v168.get("payload") or {}).get("study_id") or "")
    readme=[]
    readme.append("# SHAMS → PROCESS Downstream Export Pack (v170)")
    readme.append("")
    readme.append(f"- Issued: {issued}")
    readme.append(f"- Generator: {policy.get('generator','ui')}")
    if sid:
        readme.append(f"- Study ID: {sid}")
    readme.append("")
    readme.append("## Purpose")
    readme.append("This pack exports SHAMS results into PROCESS-like tables so PROCESS can be used strictly as a downstream tool.")
    readme.append("")
    readme.append("## Files")
    readme.append("- process_like_inputs.csv: flattened SHAMS inputs/assumptions/solver meta")
    readme.append("- process_like_outputs.csv: flattened SHAMS metrics + min_margin + dominant_constraint")
    readme.append("- mapping_v170.json: conservative alias mapping for common scalar names + constraint table")
    if completion_pack_v163:
        readme.append("- completion_pack_v163.json: included if provided (feasibility completion recipe)")
    if citation_bundle_v168:
        readme.append("- citation_bundle_v168.json: included if provided (Study ID + citation text)")
    readme.append("- manifest.json: SHA-256 hashes for all files")
    readme.append("")
    readme.append("## Notes")
    readme.append("- This does NOT attempt to match PROCESS internals or physics models.")
    readme.append("- SHAMS remains the authority; exports are for interoperability only.")
    readme_md="\n".join(readme)+"\n"

    files={
        "process_like_inputs.csv": inputs_csv.encode("utf-8"),
        "process_like_outputs.csv": outputs_csv.encode("utf-8"),
        "mapping_v170.json": _canon_json(mapping),
        "README.md": readme_md.encode("utf-8"),
    }
    if isinstance(completion_pack_v163, dict):
        files["completion_pack_v163.json"]=_canon_json(completion_pack_v163)
    if isinstance(citation_bundle_v168, dict):
        files["citation_bundle_v168.json"]=_canon_json(citation_bundle_v168)

    manifest={
        "kind":"shams_process_export_manifest",
        "version":"v170",
        "issued_utc": issued,
        "generator": policy.get("generator","ui"),
        "files": [],
    }
    for name,b in sorted(files.items()):
        manifest["files"].append({"name": name, "sha256": _sha_bytes(b), "bytes": len(b)})
    man_bytes=_canon_json(manifest)
    files["manifest.json"]=man_bytes

    bio=io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name,b in files.items():
            z.writestr(name, b)
    zip_bytes=bio.getvalue()

    pack_meta={
        "kind":"shams_process_export_pack",
        "version":"v170",
        "issued_utc": issued,
        "integrity": {"zip_sha256": _sha_bytes(zip_bytes)},
        "payload": {"manifest": manifest},
    }
    return {"pack": pack_meta, "zip_bytes": zip_bytes, "manifest": manifest}
