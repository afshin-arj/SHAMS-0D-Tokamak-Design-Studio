"""Scan Lab — One-page PDF summary exporter (0-D).

Design goals:
- Minimal dependencies (reportlab only)
- Deterministic, audit-friendly
- UI supplies a pre-rendered PNG (dominance map) so this module stays plotting-agnostic.

This is intentionally not a marketing report. It is a compact, truthful summary of
scan settings and the constraint-dominance landscape.
"""

from __future__ import annotations

from typing import Any, Dict


def build_scan_summary_pdf_bytes(*, report: Dict[str, Any], intent: str, map_png: bytes, title: str = "SHAMS — Scan Lab Summary") -> bytes:
    """Return a single-page PDF as bytes.

    Args:
        report: Scan cartography report dict.
        intent: Intent lens string.
        map_png: PNG bytes of a key map (typically dominance map).
        title: PDF title.
    """
    # reportlab is an optional dependency in SHAMS; guard import.
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    import io

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, H - 0.75 * inch, title)

    # Metadata line
    meta = []
    for k in ["shams_version", "build_utc"]:
        v = report.get(k)
        if v:
            meta.append(f"{k}: {v}")
    c.setFont("Helvetica", 8)
    if meta:
        c.drawString(0.75 * inch, H - 0.92 * inch, " | ".join(meta)[:120])

    # Scan settings
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75 * inch, H - 1.25 * inch, "Scan settings")
    c.setFont("Helvetica", 9)
    lines = [
        f"Intent lens: {intent}",
        f"x: {report.get('x_key')}   y: {report.get('y_key')}",
        f"Nx×Ny: {len(report.get('x_vals') or [])} × {len(report.get('y_vals') or [])}   n_points: {report.get('n_points')}",
        f"Report id: {report.get('id')}",
    ]
    y = H - 1.45 * inch
    for ln in lines:
        c.drawString(0.75 * inch, y, ln)
        y -= 0.18 * inch

    # Narrative
    nar = ((report.get("narrative") or {}).get("intents") or {}).get(intent, {})
    if nar:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.75 * inch, y - 0.05 * inch, "Narrative")
        y -= 0.25 * inch
        c.setFont("Helvetica", 9)
        text = str(nar.get("plain_language") or "")
        # wrap to ~90 chars
        words = text.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > 95:
                c.drawString(0.75 * inch, y, line)
                y -= 0.18 * inch
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            c.drawString(0.75 * inch, y, line)
            y -= 0.18 * inch

    # Map image
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75 * inch, 4.55 * inch, "Constraint-dominance map")
    try:
        img = ImageReader(io.BytesIO(map_png))
        # Fit into a 6.8" x 3.9" box
        c.drawImage(img, 0.75 * inch, 0.75 * inch, width=6.8 * inch, height=3.8 * inch, preserveAspectRatio=True, anchor='sw')
    except Exception:
        c.setFont("Helvetica", 9)
        c.drawString(0.75 * inch, 4.25 * inch, "(map image unavailable)")

    c.showPage()
    c.save()
    return buf.getvalue()
