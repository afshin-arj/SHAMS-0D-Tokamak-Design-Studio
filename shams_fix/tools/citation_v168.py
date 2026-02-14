from __future__ import annotations
"""Citation-Grade Study ID + BibTeX (v168)

Goal:
- Convert study artifacts (protocol v165, lock v166, authority pack v167) into a citable research object.
- Produce a stable Study ID plus CITATION.cff and BibTeX.

Inputs:
- study_protocol_v165 (dict)
- repro_lock_v166 (dict)
- authority_pack_manifest_v167 (dict) OR authority_pack_zip_sha256 (str)
- optional metadata: authors, title, year, version, repository, doi/url

Outputs:
- kind: shams_citation_bundle, version v168
- includes study_id, citation_cff_text, bibtex_text, reference_markdown
"""

from typing import Any, Dict, Optional, List
import json, time, hashlib

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(s: str) -> str:
    h=hashlib.sha256(); h.update(s.encode("utf-8")); return h.hexdigest()

def _get(p: Dict[str,Any], *keys, default=""):
    cur=p
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur=cur.get(k)
    return cur if cur is not None else default

def compute_study_id(*, protocol_sha: str, lock_sha: str, pack_sha: str) -> str:
    # Short stable identifier derived from key hashes
    base = f"prot:{protocol_sha}|lock:{lock_sha}|pack:{pack_sha}"
    h=_sha(base)
    return "SHAMS-" + h[:16].upper()

def build_citation_bundle(
    *,
    study_protocol_v165: Dict[str,Any],
    repro_lock_v166: Optional[Dict[str,Any]] = None,
    authority_pack_manifest_v167: Optional[Dict[str,Any]] = None,
    authority_pack_zip_sha256: Optional[str] = None,
    metadata: Optional[Dict[str,Any]] = None,
) -> Dict[str,Any]:
    if not isinstance(study_protocol_v165, dict) or study_protocol_v165.get("kind")!="shams_study_protocol":
        raise ValueError("study_protocol_v165 must be shams_study_protocol")
    repro_lock_v166 = repro_lock_v166 if isinstance(repro_lock_v166, dict) else None
    authority_pack_manifest_v167 = authority_pack_manifest_v167 if isinstance(authority_pack_manifest_v167, dict) else None
    metadata = metadata if isinstance(metadata, dict) else {}

    protocol_sha = str(_get(study_protocol_v165, "payload", "integrity", "protocol_sha256", default=""))
    lock_sha = str(_get(repro_lock_v166, "payload", "integrity", "lock_sha256", default="")) if repro_lock_v166 else ""
    pack_sha = ""
    if authority_pack_zip_sha256:
        pack_sha=str(authority_pack_zip_sha256)
    elif authority_pack_manifest_v167:
        # derive a stable hash of manifest contents
        pack_sha=_sha(json.dumps(authority_pack_manifest_v167, sort_keys=True, default=str))
    else:
        pack_sha=""

    study_id = compute_study_id(protocol_sha=protocol_sha, lock_sha=lock_sha, pack_sha=pack_sha)

    # Metadata defaults
    title = str(metadata.get("title") or _get(study_protocol_v165, "payload", "study", "title", default="SHAMS Design Study"))
    year = int(metadata.get("year") or time.gmtime().tm_year)
    version = str(metadata.get("version") or "v168")
    repo_url = str(metadata.get("repository") or "")
    url = str(metadata.get("url") or repo_url)
    doi = str(metadata.get("doi") or "")
    authors = metadata.get("authors") or [{"name":"SHAMS–FUSION-X Contributors"}]
    # CITATION.cff (minimal, valid-ish)
    # Note: Keep conservative fields to avoid schema brittleness.
    cff_lines=[]
    cff_lines.append("cff-version: 1.2.0")
    cff_lines.append('message: "If you use this study object, please cite it as below."')
    cff_lines.append(f'title: "{title} ({study_id})"')
    cff_lines.append("type: dataset")
    cff_lines.append(f'version: "{version}"')
    cff_lines.append(f'date-released: "{year}-01-01"')
    cff_lines.append("authors:")
    for a in authors:
        if isinstance(a, dict) and a.get("name"):
            cff_lines.append(f'  - name: "{a["name"]}"')
    if url:
        cff_lines.append(f'url: "{url}"')
    if doi:
        cff_lines.append(f'doi: "{doi}"')
    cff_lines.append('abstract: "Citable SHAMS design-study object with protocol hash, lock hash, and authority pack."')
    cff_lines.append('keywords: ["fusion", "tokamak", "feasibility", "design study", "SHAMS"]')
    citation_cff="\n".join(cff_lines) + "\n"

    # BibTeX
    key = study_id.replace("-","")
    bib = []
    bib.append(f"@misc{{{key},")
    bib.append(f"  title = {{{title} ({study_id})}}," )
    if authors and isinstance(authors, list):
        names=[a.get("name") for a in authors if isinstance(a, dict) and a.get("name")]
        if names:
            bib.append(f"  author = {{{' and '.join(names)}}},")
    bib.append(f"  year = {{{year}}},")
    if doi:
        bib.append(f"  doi = {{{doi}}},")
    if url:
        bib.append(f"  url = {{{url}}},")
    bib.append(f"  note = {{SHAMS study object; protocol_sha256={protocol_sha}; lock_sha256={lock_sha}; pack_sha={pack_sha}}}")
    bib.append("}")
    bibtex="\n".join(bib) + "\n"

    ref_md = []
    ref_md.append("# SHAMS Study Reference (v168)")
    ref_md.append("")
    ref_md.append(f"**Study ID:** `{study_id}`")
    ref_md.append("")
    ref_md.append("## How to cite (BibTeX)")
    ref_md.append("```bibtex")
    ref_md.append(bibtex.strip())
    ref_md.append("```")
    ref_md.append("")
    ref_md.append("## Integrity anchors")
    ref_md.append(f"- protocol_sha256: `{protocol_sha}`")
    ref_md.append(f"- lock_sha256: `{lock_sha}`")
    ref_md.append(f"- authority_pack_sha: `{pack_sha}`")
    ref_md.append("")
    reference_markdown="\n".join(ref_md) + "\n"

    out={
        "kind":"shams_citation_bundle",
        "version":"v168",
        "issued_utc": _utc(),
        "payload": {
            "study_id": study_id,
            "protocol_sha256": protocol_sha,
            "lock_sha256": lock_sha,
            "authority_pack_sha": pack_sha,
            "citation_cff_text": citation_cff,
            "bibtex_text": bibtex,
            "reference_markdown": reference_markdown,
        },
    }
    # stable object sha
    out["integrity"]={"object_sha256": _sha(json.dumps(out, sort_keys=True, default=str))}
    return out
