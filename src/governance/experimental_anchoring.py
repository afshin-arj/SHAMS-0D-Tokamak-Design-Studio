from __future__ import annotations

"""Experimental evidence anchoring (metadata-only).

This layer tags constraints and key physics claims with an evidence level:
  - demonstrated
  - extrapolated
  - undemonstrated
  - unknown

It never tunes physics and never affects feasibility; it only annotates artifacts.

Author: © 2026 Afshin Arjhangmehr
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ALLOWED_LEVELS = {"demonstrated","extrapolated","undemonstrated","unknown"}


def load_anchoring_db(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if raw.get('schema') != 'experimental_anchoring.v1':
        raise ValueError(f"Unsupported schema: {raw.get('schema')}")
    tags = dict(raw.get('tags') or {})
    # normalize
    for k,v in list(tags.items()):
        if not isinstance(v, dict):
            tags.pop(k, None)
            continue
        ev = str(v.get('evidence','unknown')).strip().lower()
        if ev not in ALLOWED_LEVELS:
            ev = 'unknown'
        v['evidence'] = ev
        v.setdefault('citations', [])
    raw['tags'] = tags
    return raw


def annotate_constraints(constraints: List[Dict[str, Any]], db: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a new list of constraint records annotated with evidence tags."""
    tag_map = dict((db.get('tags') or {}))
    out: List[Dict[str, Any]] = []
    for c in constraints:
        cc = dict(c)
        name = str(c.get('name',''))
        tag = tag_map.get(name)
        if isinstance(tag, dict):
            cc['evidence'] = tag.get('evidence','unknown')
            cc['evidence_citations'] = list(tag.get('citations') or [])
        else:
            cc['evidence'] = 'unknown'
            cc['evidence_citations'] = []
        out.append(cc)
    return out


def summarize_evidence(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {k: 0 for k in ["demonstrated","extrapolated","undemonstrated","unknown"]}
    for c in constraints:
        ev = str(c.get('evidence','unknown'))
        if ev not in counts:
            ev = 'unknown'
        counts[ev] += 1
    return {
        'schema': 'experimental_evidence_summary.v1',
        'counts': counts,
        'total': sum(counts.values()),
    }
