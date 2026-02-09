from __future__ import annotations

from src.dsg.design_state_graph import DesignStateGraph


def test_dsg_lineage_deterministic_parent_choice() -> None:
    g = DesignStateGraph()
    # Create three nodes with explicit lineage
    n1 = g.record(inp={"x": 1}, out={"y": 1}, ok=True, message="", elapsed_s=0.0, origin="test")
    n2 = g.record(inp={"x": 2}, out={"y": 2}, ok=True, message="", elapsed_s=0.0, origin="test", parents=[n1.node_id], edge_kind="derived")
    n3 = g.record(inp={"x": 3}, out={"y": 3}, ok=True, message="", elapsed_s=0.0, origin="test", parents=[n1.node_id, n2.node_id], edge_kind="derived")
    chain = g.lineage(n3.node_id, max_hops=10)
    # Deterministic rule chooses smallest seq parent (n1)
    assert chain[0] == n1.node_id
    assert chain[-1] == n3.node_id
