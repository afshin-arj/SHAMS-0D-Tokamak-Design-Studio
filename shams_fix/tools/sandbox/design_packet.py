"""Reactor Design Forge — Design Packet (v1)

A reviewer-friendly packet for a single candidate:
- Design Card (markdown)
- Design Narrative (markdown)
- Key tables (margins/closure headline)
- Optional PDF rendering (best-effort)

Epistemic rule: purely descriptive; uses audited artifacts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_design_packet_markdown(
    *,
    title: str,
    card_md: str,
    narrative_md: str,
    candidate: Dict[str, Any],
) -> str:
    inp = candidate.get("inputs") or {}
    out = candidate.get("outputs") or {}
    closure = candidate.get("closure_bundle") or {}
    rg = candidate.get("reality_gates") or {}

    headline = []
    headline.append(f"# {title}\n")
    headline.append("## Snapshot\n")
    headline.append(f"- Intent: `{candidate.get('intent', '') or ''}`\n")
    headline.append(f"- Feasibility: `{candidate.get('feasibility_state')}` | Robustness: `{candidate.get('robustness_class')}`\n")
    headline.append(f"- First failure: `{candidate.get('first_failure')}`\n")

    if isinstance(closure, dict):
        ne = closure.get("net_electric_MW")
        re = closure.get("recirc_electric_MW")
        ge = closure.get("gross_electric_MW")
        headline.append("\n## Closure headline\n")
        headline.append(f"- Gross electric (MW): {ge}\n")
        headline.append(f"- Recirc electric (MW): {re}\n")
        headline.append(f"- Net electric (MW): {ne}\n")

    if isinstance(rg, dict):
        headline.append("\n## Reality Gates\n")
        for k, v in (rg.get("gates") or {}).items():
            headline.append(f"- {k}: {v.get('verdict')} (margin={v.get('margin')})\n")

    headline.append("\n---\n")
    return "".join(headline) + "\n" + (card_md or "") + "\n\n---\n\n" + (narrative_md or "")


def render_pdf_from_markdown(md_text: str) -> Optional[bytes]:
    """Best-effort PDF render.

    Uses reportlab if available. Falls back to None if not installed.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter

        # Very simple text renderer: wrap lines.
        x = 40
        y = height - 40
        line_height = 12
        max_chars = 95

        for raw_line in (md_text or "").splitlines():
            line = raw_line.rstrip("\n")
            if not line:
                y -= line_height
                continue
            while len(line) > max_chars:
                c.drawString(x, y, line[:max_chars])
                y -= line_height
                line = line[max_chars:]
                if y < 60:
                    c.showPage()
                    y = height - 40
            c.drawString(x, y, line)
            y -= line_height
            if y < 60:
                c.showPage()
                y = height - 40

        c.save()
        return buf.getvalue()
    except Exception:
        return None


def build_design_packet_files(
    *,
    title: str,
    card_md: str,
    narrative_md: str,
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    md = build_design_packet_markdown(
        title=title,
        card_md=card_md,
        narrative_md=narrative_md,
        candidate=candidate,
    )
    pdf = render_pdf_from_markdown(md)
    return {
        "schema": "shams.reactor_design_forge.design_packet.v1",
        "ok": True,
        "markdown": md,
        "pdf_bytes": pdf,
        "note": "PDF rendering is best-effort; markdown is authoritative.",
    }
