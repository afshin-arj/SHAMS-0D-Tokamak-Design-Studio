"""Atlas visualization helpers — matplotlib heatmap for NiceGUI."""

from __future__ import annotations

import io
from typing import Any, Optional


def atlas_heatmap_png(atlas: dict, *, title: str = "Dominant hard constraint") -> Optional[bytes]:
    if not isinstance(atlas, dict) or not atlas.get("ok", True):
        return None
    dom = atlas.get("dominant") or []
    if not dom:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        cats = sorted({str(c) for row in dom for c in row})
        cmap = {c: i for i, c in enumerate(cats)}
        arr = np.array([[cmap[str(c)] for c in row] for row in dom], dtype=float)
        fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=120)
        im = ax.imshow(arr, origin="lower", aspect="auto", cmap="tab20")
        ax.set_title(title)
        ax.set_xlabel(str(atlas.get("var_y", "Y")))
        ax.set_ylabel(str(atlas.get("var_x", "X")))
        cbar = fig.colorbar(im, ax=ax, ticks=range(len(cats)))
        cbar.ax.set_yticklabels(cats, fontsize=7)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return None
