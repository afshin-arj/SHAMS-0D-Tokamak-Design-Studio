from __future__ import annotations
"""Study Explorer + Comparator (v128)

Loads a v127 study_matrix zip (or extracted folder) and provides:
- index parsing (csv/json)
- case listing/filtering helpers
- per-case paper pack extraction (in-memory)
- pairwise comparison summaries (inputs, KPIs, constraints)

This is downstream-only and does not affect physics/solver behavior.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO, StringIO
import json, csv, zipfile

def _read_json_bytes(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))

def _safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, bool): return None
        return float(x)
    except Exception:
        return None

@dataclass
class StudyIndex:
    created_utc: str
    rows: List[Dict[str, Any]]

def load_study_zip(path: str) -> Dict[str, bytes]:
    """Return mapping of filename -> bytes for a study zip."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if p.is_dir():
        # load from folder (recursive)
        out: Dict[str, bytes] = {}
        base = p
        for f in base.rglob("*"):
            if f.is_file():
                out[str(f.relative_to(base)).replace("\\","/")] = f.read_bytes()
        return out

    with zipfile.ZipFile(p, "r") as z:
        out = {}
        for n in z.namelist():
            if n.endswith("/"):
                continue
            out[n] = z.read(n)
        return out

def parse_study_index(files: Dict[str, bytes]) -> StudyIndex:
    if "study_index.json" in files:
        j = _read_json_bytes(files["study_index.json"])
        return StudyIndex(created_utc=j.get("created_utc",""), rows=list(j.get("rows") or []))
    if "study_index.csv" in files:
        s = files["study_index.csv"].decode("utf-8", errors="replace")
        r = list(csv.DictReader(StringIO(s)))
        return StudyIndex(created_utc="", rows=r)
    raise ValueError("study_index.csv/json not found")

def list_cases(idx: StudyIndex) -> List[str]:
    return [str(r.get("case_id")) for r in (idx.rows or []) if r.get("case_id") is not None]

def filter_cases(
    idx: StudyIndex,
    *,
    feasible_only: bool = False,
    mission: Optional[str] = None,
    kpi_filters: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
) -> List[Dict[str, Any]]:
    rows = list(idx.rows or [])
    out = []
    for r in rows:
        if feasible_only and str(r.get("feasible")).lower() not in ("true","1","yes"):
            continue
        if mission and str(r.get("mission","")) != mission:
            continue
        ok = True
        if kpi_filters:
            for k,(lo,hi) in kpi_filters.items():
                v = _safe_float(r.get(k))
                if v is None:
                    ok = False; break
                if lo is not None and v < lo: ok = False; break
                if hi is not None and v > hi: ok = False; break
        if ok:
            out.append(r)
    return out

def _read_paper_pack_run_artifact(pack_bytes: bytes) -> Dict[str, Any]:
    with zipfile.ZipFile(BytesIO(pack_bytes), "r") as z:
        if "run_artifact.json" not in z.namelist():
            raise ValueError("run_artifact.json not found in paper pack")
        return json.loads(z.read("run_artifact.json").decode("utf-8"))

def load_case_run_artifact(files: Dict[str, bytes], row: Dict[str, Any]) -> Dict[str, Any]:
    p = str(row.get("pack_path") or "")
    if not p:
        raise ValueError("row missing pack_path")
    pack = files.get(p)
    if pack is None:
        raise FileNotFoundError(p)
    return _read_paper_pack_run_artifact(pack)

def compare_two_runs(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Return structured comparison summary."""
    ai = a.get("inputs", {}) if isinstance(a.get("inputs"), dict) else {}
    bi = b.get("inputs", {}) if isinstance(b.get("inputs"), dict) else {}
    ao = a.get("outputs", {}) if isinstance(a.get("outputs"), dict) else {}
    bo = b.get("outputs", {}) if isinstance(b.get("outputs"), dict) else {}
    acs = a.get("constraints_summary", {}) if isinstance(a.get("constraints_summary"), dict) else {}
    bcs = b.get("constraints_summary", {}) if isinstance(b.get("constraints_summary"), dict) else {}

    def _delta_map(keys):
        out=[]
        for k in keys:
            av=_safe_float(ai.get(k)) if k in ai else _safe_float(ao.get(k))
            bv=_safe_float(bi.get(k)) if k in bi else _safe_float(bo.get(k))
            if av is None or bv is None:
                continue
            out.append({"k": k, "a": av, "b": bv, "delta": bv-av})
        return out

    # common interesting KPIs (present in index)
    kpis=["Q","Pfus_MW","Pnet_MW"]
    inputs=["Bt_T","R0_m","a_m","Ip_MA"]

    return {
        "kind":"shams_case_comparison",
        "a_id": a.get("id"),
        "b_id": b.get("id"),
        "feasible_a": acs.get("feasible"),
        "feasible_b": bcs.get("feasible"),
        "worst_hard_a": acs.get("worst_hard"),
        "worst_hard_b": bcs.get("worst_hard"),
        "worst_hard_margin_frac_a": acs.get("worst_hard_margin_frac"),
        "worst_hard_margin_frac_b": bcs.get("worst_hard_margin_frac"),
        "inputs_delta": _delta_map(inputs),
        "kpis_delta": _delta_map(kpis),
    }
