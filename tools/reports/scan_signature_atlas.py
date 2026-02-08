"""SHAMS — Scan Lab Signature Atlas (0-D).

Creates a *fixed-length* 10-page PDF intended as SHAMS' signature artifact.

The atlas is built from a single Scan Lab cartography report plus optional
pre-rendered map PNGs (dominance maps per intent).

Design goals:
- Deterministic layout and content (audit-grade)
- Human-readable, publication-ready
- No optimization, no recommendations

Pages (10):
1. Cover (contract + provenance)
2. Executive narrative (per intent)
3. Dominance cartography (map)
4. Intent split (Research vs Reactor)
5. First-failure / cliffs summary
6. Robustness summary
7. Local scaling-law snapshot
8. Constraint interaction (coupling) matrix
9. Uncertainty lens summary (if available)
10. Claim builder page (fillable summary of a chosen claim)
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Short, human-readable glossary for common blocking constraints (UI/teaching aid).
# This is descriptive and does not recommend actions.
_CONSTRAINT_GLOSSARY = {
    "q_div": "Divertor heat flux limit (surface power density).",
    "sigma_vm": "Structural stress limit (von Mises).",
    "HTS margin": "Superconductor temperature/current margin limit.",
    "TBR": "Tritium breeding ratio requirement (Reactor intent).",
    "q95": "Edge safety factor constraint (stability/operability).",
    "betaN": "Normalized beta limit (MHD pressure limit proxy).",
    "fG": "Greenwald fraction (density limit proxy).",
    "B_peak": "Peak field constraint (coil/structure).",
}

def _glossary_for_intent(report: Dict[str, Any], intent: str, max_items: int = 6) -> list:
    nar = (report.get("narrative") or {}).get("intents") or {}
    top = (nar.get(intent) or {}).get("dominance_ranked") or []
    out = []
    for row in top[:max_items]:
        name = str(row.get("constraint") or "").strip()
        if not name or name == "PASS":
            continue
        key = name
        # normalize common variants
        k2 = key.replace(" ", "").lower()
        if "hts" in k2:
            g = _CONSTRAINT_GLOSSARY.get("HTS margin")
        elif "sigma" in k2:
            g = _CONSTRAINT_GLOSSARY.get("sigma_vm")
        elif "tbr" in k2:
            g = _CONSTRAINT_GLOSSARY.get("TBR")
        elif "q_div" in k2 or "qdiv" in k2:
            g = _CONSTRAINT_GLOSSARY.get("q_div")
        elif "q95" in k2:
            g = _CONSTRAINT_GLOSSARY.get("q95")
        elif "betan" in k2:
            g = _CONSTRAINT_GLOSSARY.get("betaN")
        elif k2 == "fg" or "gre" in k2:
            g = _CONSTRAINT_GLOSSARY.get("fG")
        else:
            g = _CONSTRAINT_GLOSSARY.get(key)
        if g:
            out.append(f"{name}: {g}")
    return out



def _fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _bar_png(title: str, counts: Dict[str, int]) -> bytes:
    labels = list(counts.keys())
    values = [counts[k] for k in labels]
    fig = plt.figure(figsize=(7.5, 2.4))
    ax = fig.add_subplot(1, 1, 1)
    ax.bar(range(len(labels)), values)
    ax.set_title(title)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("count")
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _heatmap_png(title: str, mat: Dict[str, Dict[str, int]], order: Optional[list] = None) -> bytes:
    names = order or list(mat.keys())
    # build array
    arr = []
    for r in names:
        row = []
        for c_ in names:
            row.append(float((mat.get(r) or {}).get(c_, 0)))
        arr.append(row)
    fig = plt.figure(figsize=(7.0, 3.2))
    ax = fig.add_subplot(1, 1, 1)
    im = ax.imshow(arr, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=6)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=6)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _draw_text_block(c: canvas.Canvas, x: float, y: float, text: str, max_chars: int = 105, line_h: float = 0.18 * inch):
    for line in _wrap(text, max_chars):
        c.drawString(x, y, line)
        y -= line_h
    return y


def _wrap(text: str, width: int) -> list:
    if not text:
        return []
    words = str(text).split()
    lines = []
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    return lines


def build_signature_atlas_pdf_bytes(
    *,
    report: Dict[str, Any],
    title: str,
    contract_md: str,
    fingerprints: Dict[str, str],
    map_png_by_intent: Dict[str, bytes],
    intent_split_png: Optional[bytes] = None,
    claim: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Build the 10-page SHAMS Scan Lab Signature Atlas."""

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER

    intents = list((report.get("intents") or []) or [])
    if not intents:
        intents = ["Reactor"]

    # ---------- Page 1: Cover ----------
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.75 * inch, H - 0.9 * inch, title)
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, H - 1.15 * inch, f"Scan ID: {report.get('id')}   Axes: {report.get('x_key')} × {report.get('y_key')}   Grid: {report.get('nx')}×{report.get('ny')}")

    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, H - 1.33 * inch, "Restore token: use the Scan Lab artifact for this run (if available). If you only have this PDF, cite Scan ID above.")
    c.drawString(0.75 * inch, H - 1.48 * inch, "Restore in UI: Scan Lab → Restore Scan Artifact (JSON) → upload the artifact that contains this Scan ID.")


    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, H - 1.55 * inch, "Contract")
    c.setFont("Helvetica", 9)
    y = H - 1.75 * inch
    y = _draw_text_block(c, 0.75 * inch, y, contract_md.replace("**", ""), max_chars=110)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y - 0.2 * inch, "Provenance")
    c.setFont("Helvetica", 9)
    y2 = y - 0.42 * inch
    fp = fingerprints or {}
    c.drawString(0.75 * inch, y2, f"Fingerprint: {fp.get('fingerprint','n/a')}")
    y2 -= 0.18 * inch
    for k in sorted([kk for kk in fp.keys() if kk != "fingerprint"])[:8]:
        c.drawString(0.75 * inch, y2, f"{k}: {fp.get(k)}")
        y2 -= 0.16 * inch
    c.showPage()

    # ---------- Page 2: Executive narrative ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Executive narrative")
    y = H - 1.15 * inch
    nar_all = (report.get("narrative") or {}).get("intents") or {}
    for it in intents[:2]:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.75 * inch, y, f"Intent: {it}")
        y -= 0.25 * inch
        c.setFont("Helvetica", 9)
        txt = str((nar_all.get(it) or {}).get("plain_language") or "")
        if not txt:
            txt = "(narrative unavailable)"
        y = _draw_text_block(c, 0.75 * inch, y, txt, max_chars=110)
        y -= 0.2 * inch
    c.showPage()

    # ---------- Page 3: Dominance map (primary intent) ----------
    it0 = intents[0]
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, f"Constraint-dominance cartography — {it0}")
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, H - 1.05 * inch, "Color shows dominant blocking constraint. PASS means blocking-feasible.")
    _draw_image(c, map_png_by_intent.get(it0), 0.75 * inch, 0.75 * inch, 6.9 * inch, 4.2 * inch)

    # Glossary sidebar (teaching aid)
    gl = _glossary_for_intent(report, it0, max_items=6)
    if gl:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.75 * inch, 0.62 * inch, "Glossary (dominant constraints)")
        c.setFont("Helvetica", 8)
        yy = 0.48 * inch
        for line in gl[:6]:
            c.drawString(0.75 * inch, yy, line[:120])
            yy -= 0.14 * inch

    c.showPage()

    # ---------- Page 4: Intent split ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Intent split (Research vs Reactor)")
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, H - 1.05 * inch, "Same physics; different acceptance rules. Overlay highlights Research-feasible but Reactor-infeasible regions.")
    _draw_image(c, intent_split_png or b"", 0.75 * inch, 0.75 * inch, 6.9 * inch, 4.2 * inch)
    c.showPage()

    # ---------- Page 5: First-failure / cliffs ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "First-failure topology (cliffs)")
    top = (report.get("topology") or {}).get("intents") or {}
    y = H - 1.2 * inch
    c.setFont("Helvetica", 9)
    for it in intents[:2]:
        blob = top.get(it) or {}
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.75 * inch, y, f"Intent: {it}")
        y -= 0.22 * inch
        c.setFont("Helvetica", 9)
        c.drawString(0.75 * inch, y, f"Connected feasible components: {blob.get('n_components', 'n/a')}   Holes: {blob.get('hole_count', 'n/a')}")
        y -= 0.22 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Interpretation: more components/holes indicates sharper cliffs and regime fragmentation.")
    c.showPage()

    # ---------- Page 6: Robustness summary ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Robustness (brutally honest)")
    robust_counts = _count_labels(report, intents[0], key="robustness_label")
    png = _bar_png(f"Robustness labels — {intents[0]}", robust_counts)
    _draw_image(c, png, 0.75 * inch, 2.2 * inch, 6.9 * inch, 2.8 * inch)
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, 1.65 * inch, "Robust: stays feasible locally. Knife-edge: tiny perturbations trigger failures.")
    c.showPage()

    # ---------- Page 7: Local scaling-law snapshot ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Local scaling-law snapshot")
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, H - 1.05 * inch, "Locally fitted power-law exponents (interpret as approximate).")
    sl = report.get("local_scaling") or {}
    y = H - 1.35 * inch
    c.setFont("Helvetica", 9)
    if isinstance(sl, dict) and sl:
        for k, v in list(sl.items())[:14]:
            c.drawString(0.75 * inch, y, f"{k}: {v}")
            y -= 0.18 * inch
    else:
        c.drawString(0.75 * inch, y, "(local scaling not available in this report)")
    c.showPage()

    # ---------- Page 8: Constraint interaction ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Constraint interaction (coupling)")
    inter = report.get("interaction") or {}
    blob = ((inter.get("intents") or {}).get(intents[0]) or {}) if isinstance(inter, dict) else {}
    names = blob.get("names") if isinstance(blob, dict) else None
    mat = blob.get("before_counts") if isinstance(blob, dict) else None
    if isinstance(mat, dict) and isinstance(names, list) and names:
        png = _heatmap_png(f"A before B counts — {intents[0]}", mat, order=names)
        _draw_image(c, png, 0.75 * inch, 1.5 * inch, 6.9 * inch, 3.8 * inch)
    else:
        c.setFont("Helvetica", 9)
        c.drawString(0.75 * inch, H - 1.2 * inch, "(interaction matrix unavailable in this report)")
    c.showPage()

    # ---------- Page 9: Uncertainty lens ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Uncertainty lens")
    uc = report.get("uncertainty") or {}
    y = H - 1.2 * inch
    c.setFont("Helvetica", 9)
    if isinstance(uc, dict) and uc:
        y = _draw_text_block(c, 0.75 * inch, y, str(uc.get("summary") or ""), max_chars=110)
        domp = uc.get("dominance_prob")
        if isinstance(domp, dict) and domp:
            png = _bar_png("Dominant constraint probability (uncertainty)", {str(k): int(v) for k, v in domp.items()})
            _draw_image(c, png, 0.75 * inch, 1.2 * inch, 6.9 * inch, 2.8 * inch)
    else:
        c.drawString(0.75 * inch, y, "(uncertainty summary unavailable — run the uncertainty lens in Scan Lab)")
    c.showPage()

    # ---------- Page 10: Claim page ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, H - 0.85 * inch, "Claim (evidence-backed)")
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, H - 1.05 * inch, "Use Claim Builder to export a filled version of this page.")
    if claim and isinstance(claim, dict):
        y = H - 1.35 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.75 * inch, y, str(claim.get("title") or ""))
        y -= 0.25 * inch
        c.setFont("Helvetica", 9)
        y = _draw_text_block(c, 0.75 * inch, y, str(claim.get("statement") or ""), max_chars=110)
    else:
        c.setFont("Helvetica", 9)
        c.drawString(0.75 * inch, H - 1.35 * inch, "(no claim selected)")
    c.showPage()

    c.save()
    return buf.getvalue()


def _draw_image(c: canvas.Canvas, img_bytes: bytes, x: float, y: float, w: float, h: float) -> None:
    if not img_bytes:
        c.setFont("Helvetica", 9)
        c.drawString(x, y + h - 0.2 * inch, "(image unavailable)")
        return
    try:
        img = ImageReader(io.BytesIO(img_bytes))
        c.drawImage(img, x, y, width=w, height=h, preserveAspectRatio=True, anchor="sw")
    except Exception:
        c.setFont("Helvetica", 9)
        c.drawString(x, y + h - 0.2 * inch, "(image render failed)")


def _count_labels(report: Dict[str, Any], intent: str, key: str) -> Dict[str, int]:
    pts = report.get("points") or []
    labels = []
    for r in pts:
        it = ((r.get("intent") or {}).get(intent) or {})
        labels.append(str(it.get(key) or ""))
    labels = [l for l in labels if l]
    out: Dict[str, int] = {}
    for l in sorted(set(labels)):
        out[l] = labels.count(l)
    if not out:
        out["(none)"] = 0
    return out
