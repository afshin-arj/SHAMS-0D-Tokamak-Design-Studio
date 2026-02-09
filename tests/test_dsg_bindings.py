from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_adopt_active_node_no_graph(monkeypatch):
    # Import should succeed without importing ui/app.py (no circular)
    from ui.dsg_bindings import adopt_active_node_into_point_designer

    ok = adopt_active_node_into_point_designer(g=None, node_id=None)
    assert ok is False


def test_dsg_inputs_dict_and_to_point_inputs():
    from src.dsg.design_state_graph import DesignStateGraph

    g = DesignStateGraph()
    # Record a simple node with dict input (no PointInputs needed)
    g.record(inp={"R0_m": 1.0, "a_m": 0.5, "kappa": 1.7, "Bt_T": 5.0, "Ip_MA": 10.0, "Ti_keV": 12.0, "fG": 0.9, "Paux_MW": 20.0},
             out={"ok": True},
             ok=True, message="ok", elapsed_s=0.0, origin="test", parents=None, tags=None, edge_kind=None)

    nid = g.active_node_id
    assert nid is not None
    d = g.inputs_dict(nid)
    assert str(d["R0_m"]) in ("1.0","1")

    # Fake PointInputs dataclass-like
    class PI:
        __dataclass_fields__ = {"R0_m": None, "a_m": None}
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    pi = g.to_point_inputs(nid, PI)
    assert float(getattr(pi, "R0_m")) == 1.0
    assert float(getattr(pi, "a_m")) == 0.5
