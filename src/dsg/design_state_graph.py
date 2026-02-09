from __future__ import annotations

"""Design State Graph (DSG) — inter-panel continuity for SHAMS.

DSG is **not** physics truth. It is a deterministic ledger of evaluated design
points and their lineage across panels. It never changes evaluator outputs.

Identity: node_id = sha256(canonical_json(inputs)).

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json

from ..evaluator.cache_key import canonical_json, sha256_cache_key


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DesignNode:
    node_id: str
    inputs_sha256: str
    inputs_canonical_json: str
    outputs_sha256: str
    outputs_canonical_json: str
    ok: bool
    message: str
    elapsed_s: float
    origin: str
    parents: List[str]
    tags: List[str]
    seq: int


@dataclass(frozen=True)
class DesignEdge:
    src: str
    dst: str
    kind: str
    note: str = ""


class DesignStateGraph:
    def __init__(self) -> None:
        self.seq = 0
        self.nodes: Dict[str, DesignNode] = {}
        self.edges: List[DesignEdge] = []
        self.active_node_id: Optional[str] = None

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    @staticmethod
    def _canon_outputs(out: Dict[str, Any]) -> str:
        # Defensive scrub of obvious runtime fields
        scrub = dict(out or {})
        for k in list(scrub.keys()):
            if str(k).lower() in {"created_unix", "created_utc", "timestamp", "time"}:
                scrub.pop(k, None)
        return canonical_json(scrub)

    def record(
        self,
        *,
        inp: Any,
        out: Dict[str, Any],
        ok: bool,
        message: str,
        elapsed_s: float,
        origin: str,
        parents: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        edge_kind: Optional[str] = None,
        edge_note: str = "",
    ) -> DesignNode:
        origin = str(origin).strip() or "unknown"
        parents = [str(p) for p in (parents or []) if str(p)]
        tags = [str(t) for t in (tags or []) if str(t)]

        inputs_json = canonical_json(getattr(inp, "__dict__", inp))
        inputs_sha = _sha256_hex(inputs_json)
        node_id = inputs_sha  # stable identity

        outputs_json = self._canon_outputs(out)
        outputs_sha = _sha256_hex(outputs_json)

        if node_id in self.nodes:
            prev = self.nodes[node_id]
            # Truth should not diverge; if it does, preserve diagnostic by minting variant.
            if prev.outputs_sha256 != outputs_sha:
                node_id = _sha256_hex(inputs_sha + ":" + outputs_sha)

        if node_id in self.nodes:
            node = self.nodes[node_id]
        else:
            node = DesignNode(
                node_id=node_id,
                inputs_sha256=inputs_sha,
                inputs_canonical_json=inputs_json,
                outputs_sha256=outputs_sha,
                outputs_canonical_json=outputs_json,
                ok=bool(ok),
                message=str(message or ""),
                elapsed_s=float(elapsed_s),
                origin=origin,
                parents=sorted(set(parents)),
                tags=sorted(set(tags)),
                seq=self._next_seq(),
            )
            self.nodes[node_id] = node

        self.active_node_id = node_id

        if edge_kind and parents:
            for p in parents:
                e = DesignEdge(src=str(p), dst=node_id, kind=str(edge_kind), note=str(edge_note))
                if e not in self.edges:
                    self.edges.append(e)

        return node

    def set_active(self, node_id: Optional[str]) -> None:
        if node_id and node_id in self.nodes:
            self.active_node_id = node_id

    def get_node(self, node_id: str) -> Optional[DesignNode]:
        return self.nodes.get(str(node_id))

    def parents_of(self, node_id: str) -> List[str]:
        n = self.get_node(node_id)
        if n is None:
            return []
        # Prefer explicit node.parents; edges can be incomplete for legacy nodes.
        if n.parents:
            return list(n.parents)
        return [e.src for e in self.edges if e.dst == node_id]

    def children_of(self, node_id: str) -> List[str]:
        return [e.dst for e in self.edges if e.src == node_id]

    def lineage(self, node_id: str, *, max_hops: int = 12) -> List[str]:
        """Return a deterministic ancestry chain ending at node_id.

        If multiple parents exist, choose the parent with smallest seq (oldest).
        """
        node_id = str(node_id)
        if node_id not in self.nodes:
            return []
        chain = [node_id]
        cur = node_id
        seen = {cur}
        for _ in range(int(max_hops)):
            ps = [p for p in self.parents_of(cur) if p in self.nodes and p not in seen]
            if not ps:
                break
            # deterministic parent choice
            ps.sort(key=lambda pid: (self.nodes[pid].seq, pid))
            cur = ps[0]
            chain.append(cur)
            seen.add(cur)
        chain.reverse()
        return chain

    def edge_kind_between(self, src: str, dst: str) -> Optional[str]:
        for e in self.edges:
            if e.src == src and e.dst == dst:
                return e.kind
        return None

    def add_edge(self, *, src: str, dst: str, kind: str, note: str = "") -> None:
        """Add an edge between existing nodes (no node creation).

        This supports pipeline automation when a panel produces a *set* of
        nodes (e.g., scan results, Pareto frontier, trade-study subset) and
        we want to attach deterministic lineage without re-evaluating truth.
        """
        src = str(src)
        dst = str(dst)
        if not src or not dst:
            return
        if src not in self.nodes or dst not in self.nodes:
            return
        e = DesignEdge(src=src, dst=dst, kind=str(kind), note=str(note or ""))
        if e not in self.edges:
            self.edges.append(e)

    def add_edges(self, *, src: str, dst_list: List[str], kind: str, note: str = "") -> int:
        """Add many edges from src to each dst in dst_list. Returns count added."""
        n0 = len(self.edges)
        for d in dst_list:
            self.add_edge(src=src, dst=str(d), kind=kind, note=note)
        return len(self.edges) - n0

    def to_dict(self) -> Dict[str, Any]:
        nodes_sorted = sorted(self.nodes.values(), key=lambda n: (n.seq, n.node_id))
        return {
            "schema": "shams.dsg.v1",
            "active_node_id": self.active_node_id,
            "nodes": [asdict(n) for n in nodes_sorted],
            "edges": [asdict(e) for e in self.edges],
        }

    def to_canonical_json(self) -> str:
        return canonical_json(self.to_dict())

    def inputs_dict(self, node_id: str) -> Dict[str, Any]:
        """Return decoded inputs dict for node_id (canonical JSON)."""
        n = self.get_node(str(node_id))
        if n is None:
            return {}
        try:
            return json.loads(n.inputs_canonical_json)
        except Exception:
            return {}

    def outputs_dict(self, node_id: str) -> Dict[str, Any]:
        """Return decoded outputs dict for node_id (canonical JSON)."""
        n = self.get_node(str(node_id))
        if n is None:
            return {}
        try:
            return json.loads(n.outputs_canonical_json)
        except Exception:
            return {}

    def to_point_inputs(self, node_id: str, PointInputsCls: Any) -> Any:
        """Best-effort conversion of DSG node inputs into a PointInputs-like object.

        Filters keys to dataclass fields if available.
        """
        data = self.inputs_dict(node_id)
        if not data:
            return None
        try:
            fields = getattr(PointInputsCls, "__dataclass_fields__", None)
            if fields:
                filt = {k: data[k] for k in fields.keys() if k in data}
            else:
                filt = dict(data)
            return PointInputsCls(**filt)
        except Exception:
            try:
                return PointInputsCls(**dict(data))
            except Exception:
                return None

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_canonical_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "DesignStateGraph":
        p = Path(path)
        g = cls()
        if not p.exists():
            return g
        data = json.loads(p.read_text(encoding="utf-8"))
        g.active_node_id = data.get("active_node_id")
        for nd in data.get("nodes", []):
            node = DesignNode(
                node_id=str(nd["node_id"]),
                inputs_sha256=str(nd["inputs_sha256"]),
                inputs_canonical_json=str(nd["inputs_canonical_json"]),
                outputs_sha256=str(nd["outputs_sha256"]),
                outputs_canonical_json=str(nd["outputs_canonical_json"]),
                ok=bool(nd.get("ok", True)),
                message=str(nd.get("message", "")),
                elapsed_s=float(nd.get("elapsed_s", 0.0)),
                origin=str(nd.get("origin", "unknown")),
                parents=list(nd.get("parents", []) or []),
                tags=list(nd.get("tags", []) or []),
                seq=int(nd.get("seq", 0)),
            )
            g.nodes[node.node_id] = node
            g.seq = max(g.seq, node.seq)
        for ed in data.get("edges", []):
            g.edges.append(DesignEdge(src=str(ed["src"]), dst=str(ed["dst"]), kind=str(ed["kind"]), note=str(ed.get("note", ""))))
        if g.active_node_id not in g.nodes:
            g.active_node_id = next(iter(g.nodes.keys()), None)
        return g
