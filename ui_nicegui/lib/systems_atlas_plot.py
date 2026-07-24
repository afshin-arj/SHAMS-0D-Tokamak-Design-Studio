"""Atlas visualization helpers — matplotlib heatmap for NiceGUI."""

from __future__ import annotations

import io
from typing import Any, Optional

# Screening palette — blue blocking-OK, amber/blue-grey fails (never PD hero green/red).
_OK_COLOR = "#1565c0"
_FAIL_CYCLE = (
    "#ef6c00",
    "#6a1b9a",
    "#00838f",
    "#5d4037",
    "#455a64",
    "#f9a825",
    "#ad1457",
    "#37474f",
)


def atlas_heatmap_png(atlas: dict, *, title: str = "Dominant hard limiter (screening)") -> Optional[bytes]:
    """Render categorical dominant-limiter grid as PNG bytes.

    ``ok`` / ``pass`` cells use blue; fail mechanisms use amber/blue-grey —
    never PD hero green / red.
    """
    if not isinstance(atlas, dict) or not atlas.get("ok", True):
        return None
    dom = atlas.get("dominant") or []
    if not dom:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        import numpy as np

        cats = sorted({str(c) for row in dom for c in row})
        # Put blocking-OK first so index 0 is always blue when present.
        ok_names = [c for c in cats if str(c).lower() in ("ok", "pass", "")]
        fail_names = [c for c in cats if c not in ok_names]
        ordered = ok_names + fail_names
        cmap_idx = {c: i for i, c in enumerate(ordered)}
        colors = []
        for c in ordered:
            if str(c).lower() in ("ok", "pass", ""):
                colors.append(_OK_COLOR)
            else:
                colors.append(_FAIL_CYCLE[len(colors) % len(_FAIL_CYCLE)])
        listed = ListedColormap(colors if colors else [_OK_COLOR])
        arr = np.array([[cmap_idx[str(c)] for c in row] for row in dom], dtype=float)
        labels = []
        for c in ordered:
            if str(c).lower() in ("ok", "pass", ""):
                labels.append("blocking-OK")
            else:
                labels.append(str(c))

        fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=120)
        im = ax.imshow(
            arr,
            origin="lower",
            aspect="auto",
            cmap=listed,
            vmin=-0.5,
            vmax=max(len(ordered) - 0.5, 0.5),
        )
        ax.set_title(title)
        # dominant[i][j] with i=x, j=y → imshow rows=x, cols=y
        ax.set_xlabel(str(atlas.get("var_y", "Y")))
        ax.set_ylabel(str(atlas.get("var_x", "X")))
        cbar = fig.colorbar(im, ax=ax, ticks=range(len(ordered)))
        cbar.ax.set_yticklabels(labels, fontsize=7)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return None
