from __future__ import annotations
"""
Figure export utilities (v91)
- Deterministic PNG+SVG export with reserved margins
"""
from pathlib import Path

def save_png_svg(fig, out_png: str | None = None, out_svg: str | None = None, dpi: int = 220) -> None:
    if out_png:
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    if out_svg:
        Path(out_svg).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_svg, format="svg", bbox_inches="tight")
