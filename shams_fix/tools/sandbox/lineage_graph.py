"""Reactor Design Forge — Design Lineage Graph (v1)

Purpose
-------
Expose *how* candidates were discovered (parent → child), to build expert
trust and replace PROCESS's opaque search narrative.

Epistemic rules
--------------
This module never evaluates truth and never modifies any candidate. It only
re-arranges already audited archive records.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Tuple


def build_lineage_edges(archive: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Return (parent_id, child_id) edges from an archive.

    Candidates may store lineage in several fields depending on engine version:
    - parent_id: str
    - parents: list[str]
    - lineage: dict with keys
    """

    edges: List[Tuple[str, str]] = []
    for c in archive or []:
        cid = str(c.get("id") or c.get("candidate_id") or "")
        if not cid:
            continue

        parents: List[str] = []
        if c.get("parent_id"):
            parents.append(str(c["parent_id"]))
        if isinstance(c.get("parents"), list):
            parents.extend([str(x) for x in c.get("parents") if x])
        if isinstance(c.get("lineage"), dict):
            if c["lineage"].get("parent_id"):
                parents.append(str(c["lineage"]["parent_id"]))
            if isinstance(c["lineage"].get("parents"), list):
                parents.extend([str(x) for x in c["lineage"].get("parents") if x])

        # De-duplicate, drop self loops
        parents = [p for p in dict.fromkeys(parents) if p and p != cid]
        for p in parents:
            edges.append((p, cid))
    return edges


def compute_tree_layout(edges: List[Tuple[str, str]]) -> Dict[str, Dict[str, float]]:
    """Compute a simple layered layout for a DAG.

    Returns a mapping: node_id -> {"x": float, "y": float, "depth": int}
    Suitable for quick plotting (plotly/matplotlib). Deterministic.
    """

    if not edges:
        return {}

    children = defaultdict(list)
    parents = defaultdict(list)
    nodes = set()
    for p, c in edges:
        children[p].append(c)
        parents[c].append(p)
        nodes.add(p)
        nodes.add(c)

    # Roots: no parents
    roots = [n for n in nodes if not parents.get(n)]
    if not roots:
        # In cycles/fully connected weirdness, pick a stable root
        roots = [sorted(nodes)[0]]

    depth = {r: 0 for r in roots}
    q = deque(roots)
    while q:
        n = q.popleft()
        for ch in children.get(n, []):
            nd = depth[n] + 1
            if ch not in depth or nd < depth[ch]:
                depth[ch] = nd
                q.append(ch)

    # Group nodes by depth
    layers = defaultdict(list)
    for n in nodes:
        layers[depth.get(n, 0)].append(n)
    for d in layers:
        layers[d].sort()

    layout = {}
    for d in sorted(layers.keys()):
        layer = layers[d]
        # spread x within layer
        for i, n in enumerate(layer):
            layout[n] = {"x": float(i), "y": float(-d), "depth": int(d)}
    return layout
