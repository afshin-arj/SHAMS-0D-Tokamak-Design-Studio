"""Structural diff utilities for SHAMS run artifacts.

These diffs focus on *schema/structure* changes rather than numeric tolerance.
Used for regression hygiene and release-note generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


_CONSTRAINT_META_FIELDS = ("sense", "limit", "severity", "units", "group", "note", "meaning", "best_knobs", "validity", "maturity")


def _index_constraints(artifact: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    items = artifact.get("constraints") or []
    out: Dict[str, Dict[str, Any]] = {}
    for c in items:
        name = str(c.get("name", ""))
        if name:
            out[name] = c
    return out


def structural_diff(new_artifact: Dict[str, Any], old_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Return a structural diff summary between two run artifacts.

    Includes:
      - constraints: added/removed, and meta-field changes
      - model_cards: added/removed/changed hashes/versions
      - schema_version changes
    """
    new_c = _index_constraints(new_artifact)
    old_c = _index_constraints(old_artifact)

    new_names = set(new_c.keys())
    old_names = set(old_c.keys())

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)

    changed: List[Dict[str, Any]] = []
    for name in sorted(new_names & old_names):
        a = new_c[name]
        b = old_c[name]
        fields_changed = {}
        for f in _CONSTRAINT_META_FIELDS:
            va = a.get(f)
            vb = b.get(f)
            if va != vb:
                fields_changed[f] = {"new": va, "old": vb}
        # Also detect renames of human-readable units/note etc only; value/margin are numeric and belong in tolerance diff.
        if fields_changed:
            changed.append({"name": name, "fields": fields_changed})

    # model cards
    new_mc = new_artifact.get("model_cards") or {}
    old_mc = old_artifact.get("model_cards") or {}
    new_ids = set(new_mc.keys())
    old_ids = set(old_mc.keys())
    mc_added = sorted(new_ids - old_ids)
    mc_removed = sorted(old_ids - new_ids)

    mc_changed: List[Dict[str, Any]] = []
    for mid in sorted(new_ids & old_ids):
        na = new_mc.get(mid) or {}
        ob = old_mc.get(mid) or {}
        # consider hash + version as identity
        keys = ("hash", "version")
        delta = {}
        for k in keys:
            if na.get(k) != ob.get(k):
                delta[k] = {"new": na.get(k), "old": ob.get(k)}
        if delta:
            mc_changed.append({"id": mid, "fields": delta})

    return {
        "schema_version": {
            "new": new_artifact.get("schema_version"),
            "old": old_artifact.get("schema_version"),
        },
        "constraints": {
            "added": added,
            "removed": removed,
            "changed_meta": changed,
        },
        "model_cards": {
            "added": mc_added,
            "removed": mc_removed,
            "changed": mc_changed,
        },
    }


def classify_severity(old_artifact: Dict[str, Any], new_artifact: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
    """Classify structural diffs into severities.

    Severities:
      - info: low-impact / expected bookkeeping changes
      - warn: likely behavior change but not necessarily breaking
      - breaking: likely to break downstream assumptions or feasibility expectations

    Heuristics (transparent, deterministic):
      - Constraint removed -> breaking
      - New hard constraint added -> warn/breaking (breaking if severity == 'hard')
      - Constraint rename -> breaking (detected via removed+added with identical meta)
      - Model card hash/version changed -> warn; breaking if validity is violated in new artifact
    """
    findings: List[Dict[str, Any]] = []
    cons = (diff.get("constraints") or {})
    added = cons.get("added") or []
    removed = cons.get("removed") or []
    changed = cons.get("changed_meta") or []

    # Detect possible renames: removed + added with identical meta fields
    def _meta(c):
        if not isinstance(c, dict):
            return None
        return tuple((c.get(k) for k in _CONSTRAINT_META_FIELDS))

    removed_meta = { _meta(c): c.get("name") for c in removed if _meta(c) is not None }
    added_meta = { _meta(c): c.get("name") for c in added if _meta(c) is not None }
    renames = []
    for meta, old_name in removed_meta.items():
        if meta in added_meta:
            renames.append({"old": old_name, "new": added_meta[meta], "meta": dict(zip(_CONSTRAINT_META_FIELDS, meta))})

    for r in renames:
        findings.append({"severity":"breaking","kind":"constraint_rename","detail":r})

    # Removed constraints (excluding those accounted for as renames)
    renamed_old = {r["old"] for r in renames}
    for c in removed:
        if c.get("name") in renamed_old:
            continue
        findings.append({"severity":"breaking","kind":"constraint_removed","detail":{"name":c.get("name"), "meta":{k:c.get(k) for k in _CONSTRAINT_META_FIELDS}}})

    # Added constraints
    renamed_new = {r["new"] for r in renames}
    for c in added:
        if c.get("name") in renamed_new:
            continue
        sev = str((c.get("severity") or "")).lower()
        severity = "warn"
        if sev in ("hard","required"):
            severity = "breaking"
        findings.append({"severity":severity,"kind":"constraint_added","detail":{"name":c.get("name"), "meta":{k:c.get(k) for k in _CONSTRAINT_META_FIELDS}}})

    # Meta changes
    for ch in changed:
        fields = ch.get("fields") or {}
        severity = "warn"
        # If sense/limit changed, likely behavior change
        if any(k in fields for k in ("sense","limit")):
            severity = "breaking"
        findings.append({"severity":severity,"kind":"constraint_meta_changed","detail":ch})

    # Model cards
    mc = diff.get("model_cards") or {}
    for mid in mc.get("added") or []:
        findings.append({"severity":"info","kind":"model_card_added","detail":{"id":mid}})
    for mid in mc.get("removed") or []:
        findings.append({"severity":"warn","kind":"model_card_removed","detail":{"id":mid}})
    for ch in mc.get("changed") or []:
        mid = ch.get("id")
        sev = "warn"
        # If new artifact flags validity violation for this card, classify as breaking
        try:
            vnew = (new_artifact.get("outputs") or {}).get("model_cards_validity") or new_artifact.get("model_cards_validity") or {}
            ok = (vnew.get(mid) or {}).get("ok", True)
            if ok is False:
                sev = "breaking"
        except Exception:
            pass
        findings.append({"severity":sev,"kind":"model_card_changed","detail":ch})

    # Summarize counts and max severity
    order = {"info":0,"warn":1,"breaking":2}
    max_sev = "info"
    counts = {"info":0,"warn":0,"breaking":0}
    for f in findings:
        s=f.get("severity","info")
        if s not in counts:
            continue
        counts[s]+=1
        if order.get(s,0) > order.get(max_sev,0):
            max_sev=s

    return {"max_severity": max_sev, "counts": counts, "findings": findings}
