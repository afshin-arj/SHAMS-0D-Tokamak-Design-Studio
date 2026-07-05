"""Systems Mode artifact helpers — framework-agnostic (Batch 3)."""

from __future__ import annotations



import math

from typing import Any, Dict, List, Optional



from ui_nicegui.lib.artifact_access import get_point_artifact_triple

from ui_nicegui.lib.verdict_core import constraint_table_rows, verdict_summary

from ui_nicegui.session import DesignSession





def get_in(d: Any, path: List[str]) -> Any:

    cur: Any = d

    for k in path:

        if not isinstance(cur, dict):

            return None

        cur = cur.get(k)

    return cur





def pick_first(d: Any, paths: List[List[str]]) -> Any:

    for p in paths:

        v = get_in(d, p)

        if v is not None:

            return v

    return None





def fmt(v: Any, *, digits: int = 3) -> str:

    try:

        if v is None:

            return "-"

        if isinstance(v, bool):

            return "true" if v else "false"

        if isinstance(v, (int, float)):

            if not math.isfinite(float(v)):

                return "-"

            return f"{float(v):.{digits}g}"

        s = str(v)

        return s if s.strip() else "-"

    except Exception:

        return "-"





def extract_constraints(art: dict) -> list[dict]:

    paths = [

        ["ledger", "constraints"],

        ["constraint_ledger", "constraints"],

        ["constraints"],

        ["ledger_entries"],

    ]

    for p in paths:

        v = get_in(art, p)

        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):

            return v

    return []





def constraint_name(c: dict) -> str:

    return str(c.get("name") or c.get("constraint") or c.get("id") or c.get("key") or "constraint")





def constraint_margin(c: dict) -> float | None:

    for k in ["signed_margin", "margin", "m", "delta"]:

        v = c.get(k)

        if isinstance(v, (int, float)):

            return float(v)

    mv = c.get("metrics") if isinstance(c.get("metrics"), dict) else None

    if isinstance(mv, dict):

        for k in ["signed_margin", "margin"]:

            v = mv.get(k)

            if isinstance(v, (int, float)):

                return float(v)

    return None





def constraint_status(c: dict) -> str:

    v = c.get("status") or c.get("verdict") or c.get("result")

    if isinstance(v, str) and v:

        return v.upper()

    m = constraint_margin(c)

    if isinstance(m, (int, float)):

        return "FAIL" if m < 0 else "PASS"

    return "-"





def constraint_mechanism(c: dict) -> str:

    for k in ["mechanism_group", "mechanism", "group"]:

        v = c.get(k)

        if isinstance(v, str) and v:

            return v.upper()

    return "OTHER"





def synthesize_from_point(point_out: Dict[str, Any]) -> dict:

    summary = verdict_summary(point_out)

    rows = constraint_table_rows(point_out)

    constraints = [

        {

            "name": r["name"],

            "status": "PASS" if r["passed"] else "FAIL",

            "signed_margin": r["residual"],

            "margin": r["residual"],

        }

        for r in rows

    ]

    return {

        "verdict": summary["verdict"],

        "dominant_constraint": summary["dominant"],

        "constraints": constraints,

        "outputs": dict(point_out),

        "source": "point_designer_fallback",

    }





def fetch_systems_artifact(session: DesignSession) -> Optional[dict]:
    if isinstance(session.systems_last_solve_artifact, dict):
        art = session.systems_last_solve_artifact
        if pick_first(art, [["verdict"], ["summary", "verdict"]]) or extract_constraints(art):
            if not pick_first(art, [["verdict"], ["summary", "verdict"]]):
                out = art.get("outputs") if isinstance(art.get("outputs"), dict) else None
                if isinstance(out, dict):
                    synth = synthesize_from_point(out)
                    merged = dict(art)
                    merged.setdefault("verdict", synth["verdict"])
                    merged.setdefault("dominant_constraint", synth["dominant_constraint"])
                    return merged
            return art

    art, _, point_out = get_point_artifact_triple(session)

    if isinstance(art, dict):
        if pick_first(art, [["verdict"], ["summary", "verdict"], ["ledger", "verdict"]]):
            return art
        if extract_constraints(art) or isinstance(art.get("outputs"), dict):
            out = art.get("outputs") if isinstance(art.get("outputs"), dict) else point_out
            if isinstance(out, dict) and out:
                synth = synthesize_from_point(out)
                merged = dict(art)
                merged.setdefault("verdict", synth["verdict"])
                merged.setdefault("dominant_constraint", synth["dominant_constraint"])
                if not extract_constraints(merged):
                    merged["constraints"] = synth["constraints"]
                merged.setdefault("source", synth.get("source", "point_designer_fallback"))
                return merged
            return art

    if isinstance(point_out, dict) and point_out:

        return synthesize_from_point(point_out)

    return None


