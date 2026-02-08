from __future__ import annotations
"""DOI Export Helper (v153)

Goal:
Convert SHAMS study_registry_v149.json into metadata formats suitable for deposit systems
(eg. Zenodo JSON, Crossref-like minimal metadata).

This is *export only* and makes no changes to physics/solver behavior.

Notes:
- Zenodo supports a "metadata" object with fields like title, description, creators, upload_type, etc.
- Crossref deposit schemas are larger; here we provide a conservative, minimal crosswalk.
"""

from typing import Any, Dict, List, Optional
import time, json, hashlib

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(o: Any) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def _as_creators(authors: List[str]) -> List[Dict[str, str]]:
    out=[]
    for a in authors or []:
        # Zenodo expects "name" in "Family, Given" ideally; we keep as provided.
        out.append({"name": a})
    return out

def zenodo_metadata_from_registry(reg: Dict[str, Any], communities: Optional[List[str]] = None, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    if not (isinstance(reg, dict) and reg.get("kind") == "shams_study_registry"):
        raise ValueError("study registry kind mismatch")
    title=str(reg.get("title") or "SHAMS design study")
    desc=str(reg.get("description") or "")
    authors=list(reg.get("authors") or [])
    created=str(reg.get("date_utc") or _utc())
    shams_version=str(reg.get("shams_version") or "")
    md={
        "metadata": {
            "title": title,
            "description": desc,
            "creators": _as_creators(authors),
            "upload_type": "publication",
            "publication_type": "report",
            "publication_date": created[:10] if len(created)>=10 else created,
            "keywords": (keywords or []) + (["SHAMS","fusion","design study"] if "SHAMS" not in (keywords or []) else []),
            "version": shams_version,
            "notes": f"Exported from SHAMS study_registry_v149.json at {_utc()}",
        }
    }
    if communities:
        md["metadata"]["communities"]=[{"identifier": c} for c in communities]
    md["provenance"]={"registry_sha256": _sha(reg)}
    return md

def crossref_minimal_from_registry(reg: Dict[str, Any], doi: str = "", publisher: str = "SHAMS", resource_url: str = "") -> Dict[str, Any]:
    if not (isinstance(reg, dict) and reg.get("kind") == "shams_study_registry"):
        raise ValueError("study registry kind mismatch")
    title=str(reg.get("title") or "SHAMS design study")
    authors=list(reg.get("authors") or [])
    created=str(reg.get("date_utc") or _utc())
    year=created[:4] if len(created)>=4 else ""
    cr={
        "doi": doi or "",
        "title": title,
        "publisher": publisher,
        "published": {"year": year},
        "contributors": [{"name": a, "role":"author"} for a in authors],
        "url": resource_url or "",
        "description": str(reg.get("description") or ""),
        "version": str(reg.get("shams_version") or ""),
        "provenance": {"registry_sha256": _sha(reg), "exported_utc": _utc()},
    }
    return cr
