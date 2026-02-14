from __future__ import annotations

from src.dsg.design_state_graph import DesignStateGraph


def test_ui_dsg_panel_import_and_summary() -> None:
    # Import should be safe (streamlit is a UI dependency)
    from ui.dsg_panel import build_active_node_markdown

    g = DesignStateGraph()
    n1 = g.record(inp={"a": 1}, out={"b": 2}, ok=True, message="ok", elapsed_s=0.0, origin="test")
    md = build_active_node_markdown(g=g, node_id=n1.node_id)
    assert "Active Design Node" in md
    assert n1.node_id in md