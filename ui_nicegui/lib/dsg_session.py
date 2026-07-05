"""Design State Graph session bootstrap (Streamlit ui/app.py parity)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from ui_nicegui.bootstrap import repo_root

if TYPE_CHECKING:
    from ui_nicegui.session import DesignSession

_DSG_SNAPSHOT = "artifacts/dsg/current_dsg.json"

try:
    from src.dsg import DesignStateGraph
except Exception:
    try:
        from dsg import DesignStateGraph  # type: ignore
    except Exception:
        DesignStateGraph = None  # type: ignore


def ensure_dsg(session: "DesignSession") -> Optional[Any]:
    """Load or create DSG on session if available."""
    if DesignStateGraph is None:
        return None
    g = getattr(session, "_shams_dsg", None)
    if g is not None:
        return g
    path = Path(repo_root()) / _DSG_SNAPSHOT
    try:
        if path.is_file():
            session._shams_dsg = DesignStateGraph.load(str(path))
        else:
            session._shams_dsg = DesignStateGraph()
    except Exception:
        try:
            session._shams_dsg = DesignStateGraph()
        except Exception:
            session._shams_dsg = None
    return session._shams_dsg


def save_dsg_best_effort(session: "DesignSession") -> None:
    """Persist DSG snapshot (exploration layer only)."""
    if DesignStateGraph is None:
        return
    g = getattr(session, "_shams_dsg", None)
    if g is None:
        return
    try:
        path = Path(repo_root()) / _DSG_SNAPSHOT
        path.parent.mkdir(parents=True, exist_ok=True)
        g.save(str(path))
    except Exception:
        pass
