"""Systems Mode artifact helpers — framework-agnostic."""

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





# Provenance tokens for Systems Mode artifacts (PHYS / UX honesty).
SYSTEMS_RESULT_SOURCES = frozenset({"systems_solve", "systems_recovery", "systems_restored"})
PD_BASELINE_SOURCES = frozenset(
    {"point_designer_fallback", "point_designer_apply", "systems_apply_reeval"}
)


def normalize_systems_artifact_source(art: Dict[str, Any]) -> str:
    """Return explicit provenance; never invent systems_solve for PD-shaped blobs."""
    src = str(art.get("source") or "").strip()
    if src in SYSTEMS_RESULT_SOURCES or src in PD_BASELINE_SOURCES:
        return src
    # Uploaded / restored Systems-shaped packs without an explicit source token.
    if str(art.get("artifact_kind") or "").strip().lower() == "systems":
        return "systems_restored"
    # Missing source on a session "solve" slot is almost always Apply→PD re-eval residue.
    return "point_designer_fallback"


def is_systems_result_source(source: Optional[str]) -> bool:
    return str(source or "").strip() in SYSTEMS_RESULT_SOURCES


def fetch_systems_artifact(session: DesignSession) -> Optional[dict]:
    if isinstance(session.systems_last_solve_artifact, dict):
        art = dict(session.systems_last_solve_artifact)
        if pick_first(art, [["verdict"], ["summary", "verdict"]]) or extract_constraints(art):
            if not pick_first(art, [["verdict"], ["summary", "verdict"]]):
                out = art.get("outputs") if isinstance(art.get("outputs"), dict) else None
                if isinstance(out, dict):
                    synth = synthesize_from_point(out)
                    art.setdefault("verdict", synth["verdict"])
                    art.setdefault("dominant_constraint", synth["dominant_constraint"])
            art["source"] = normalize_systems_artifact_source(art)
            return art

    art, _, point_out = get_point_artifact_triple(session)

    if isinstance(art, dict):
        if pick_first(art, [["verdict"], ["summary", "verdict"], ["ledger", "verdict"]]):
            merged = dict(art)
            # Point Designer / Suite artifacts are not Systems Mode solves.
            if not isinstance(session.systems_last_solve_artifact, dict):
                merged["source"] = "point_designer_fallback"
            else:
                merged.setdefault("source", "point_designer_fallback")
            return merged
        if extract_constraints(art) or isinstance(art.get("outputs"), dict):
            out = art.get("outputs") if isinstance(art.get("outputs"), dict) else point_out
            if isinstance(out, dict) and out:
                synth = synthesize_from_point(out)
                merged = dict(art)
                merged.setdefault("verdict", synth["verdict"])
                merged.setdefault("dominant_constraint", synth["dominant_constraint"])
                if not extract_constraints(merged):
                    merged["constraints"] = synth["constraints"]
                merged["source"] = "point_designer_fallback"
                return merged
            return art

    if isinstance(point_out, dict) and point_out:
        return synthesize_from_point(point_out)

    return None


