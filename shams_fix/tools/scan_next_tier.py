"""Scan Lab — next-tier 0-D insight suite.

This module adds *interpretability* features that remain fully within the
0-D framework (pure evaluation + analysis of evaluated points).

Implements:
1) Automatic local scaling-law extraction (power-law fit)
2) Regime labeling (human-readable region labels)
3) Impossible-region explanation (aggregate failure structure)
4) Constraint irrelevance detection (never-active constraints)
5) Projection stability checks (2D projection robustness vs a 3rd variable)
6) Path-following scans (follow a trajectory that holds a target output)
7) Assumption stress highlighting (near-threshold sensitivity hotspots)
8) Counterfactual lenses (visualize with one constraint removed)
9) Guided insight mode (scripted walkthrough steps)
10) Reference atlas export (multi-page PDF)
11) Surprise detector (identify high-surprise regions)

Design rules:
- No optimization, no relaxation, no hidden smoothing.
- Deterministic given inputs and seed.
- Uses existing Scan Lab cartography reports whenever possible.
"""

from __future__ import annotations

import io
import math
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except Exception:
        return None
    return v if _finite(v) else None


def _neighbors(report: Dict[str, Any], i0: int, j0: int, radius: int = 1) -> List[Dict[str, Any]]:
    pts = report.get("points") or []
    out: List[Dict[str, Any]] = []
    for r in pts:
        try:
            i = int(r.get("i"))
            j = int(r.get("j"))
        except Exception:
            continue
        if abs(i - i0) <= radius and abs(j - j0) <= radius:
            out.append(r)
    return out


# -----------------------------
# 1) Local scaling-law extraction
# -----------------------------


def local_powerlaw_fit(
    *,
    report: Dict[str, Any],
    intent: str,
    i0: int,
    j0: int,
    target: str = "min_blocking_margin",
    radius: int = 2,
) -> Dict[str, Any]:
    """Fit a local power-law: target ≈ C * x^a * y^b.

    Uses log-linear least squares on neighborhood samples. Only fits when
    target and x,y are positive.
    """
    x_key = str(report.get("x_key"))
    y_key = str(report.get("y_key"))
    pts = _neighbors(report, i0=i0, j0=j0, radius=int(max(1, radius)))

    X: List[Tuple[float, float, float]] = []  # (logx, logy, logt)
    for r in pts:
        x = _safe_float(r.get("x"))
        y = _safe_float(r.get("y"))
        if x is None or y is None or x <= 0 or y <= 0:
            continue
        t = None
        it = ((r.get("intent") or {}).get(intent) or {})
        if target == "min_blocking_margin":
            t = _safe_float(it.get("min_blocking_margin"))
        elif target == "local_p_feasible":
            t = _safe_float(it.get("local_p_feasible"))
        else:
            # hard margin by name
            mh = r.get("margins_hard") or {}
            t = _safe_float(mh.get(target))
        if t is None or t <= 0:
            continue
        X.append((math.log(x), math.log(y), math.log(t)))

    if len(X) < 6:
        return {
            "ok": False,
            "reason": "insufficient_positive_samples",
            "n": len(X),
            "model": None,
        }

    # Solve least squares for [c, a, b] in log(t) = c + a log(x) + b log(y)
    # Normal equations for small 3x3.
    s1 = float(len(X))
    sx = sum(a for a, _, _ in X)
    sy = sum(b for _, b, _ in X)
    st = sum(t for _, _, t in X)
    sxx = sum(a * a for a, _, _ in X)
    syy = sum(b * b for _, b, _ in X)
    sxy = sum(a * b for a, b, _ in X)
    sxt = sum(a * t for a, _, t in X)
    syt = sum(b * t for _, b, t in X)

    # Solve linear system
    # [s1  sx  sy][c]   [st]
    # [sx sxx sxy][a] = [sxt]
    # [sy sxy syy][b]   [syt]
    det = (
        s1 * (sxx * syy - sxy * sxy)
        - sx * (sx * syy - sxy * sy)
        + sy * (sx * sxy - sxx * sy)
    )
    if abs(det) < 1e-12:
        return {"ok": False, "reason": "singular_fit", "n": len(X), "model": None}

    # Cramer's rule (fine for 3x3)
    det_c = (
        st * (sxx * syy - sxy * sxy)
        - sx * (sxt * syy - sxy * syt)
        + sy * (sxt * sxy - sxx * syt)
    )
    det_a = (
        s1 * (sxt * syy - sxy * syt)
        - st * (sx * syy - sxy * sy)
        + sy * (sx * syt - sxt * sy)
    )
    det_b = (
        s1 * (sxx * syt - sxt * sxy)
        - sx * (sx * syt - sxt * sy)
        + st * (sx * sxy - sxx * sy)
    )

    c = det_c / det
    a = det_a / det
    b = det_b / det
    C = math.exp(c)

    return {
        "ok": True,
        "n": int(len(X)),
        "intent": str(intent),
        "target": str(target),
        "model": {
            "form": "t ≈ C * x^a * y^b (local)",
            "C": float(C),
            "a": float(a),
            "b": float(b),
            "x_key": x_key,
            "y_key": y_key,
        },
        "note": "Local log-linear fit on neighborhood samples; not a global scaling law.",
    }


# -----------------------------
# 2) Regime labeling
# -----------------------------


def label_regime(*, report: Dict[str, Any], intent: str, i0: int, j0: int) -> Dict[str, Any]:
    pts = _neighbors(report, i0=i0, j0=j0, radius=1)
    if not pts:
        return {"label": "(no data)", "detail": ""}
    r = pts[0]
    it = ((r.get("intent") or {}).get(intent) or {})
    dom = str(it.get("dominant_blocking") or "PASS")
    bf = bool(it.get("blocking_feasible"))
    # crude gradient sign from neighborhood medians
    def _tval(rr: Dict[str, Any]) -> Optional[float]:
        return _safe_float((((rr.get("intent") or {}).get(intent) or {}).get("min_blocking_margin")))

    m0 = _tval(r)
    mxp = next((_tval(p) for p in pts if int(p.get("i", 0)) == i0 + 1 and int(p.get("j", 0)) == j0), None)
    myp = next((_tval(p) for p in pts if int(p.get("i", 0)) == i0 and int(p.get("j", 0)) == j0 + 1), None)
    dx = None if (m0 is None or mxp is None) else mxp - m0
    dy = None if (m0 is None or myp is None) else myp - m0

    if dom == "PASS" and bf:
        base = "Feasible core"
    else:
        base = f"{dom}-limited"

    hints = []
    if dx is not None:
        hints.append("x helps" if dx > 0 else "x hurts")
    if dy is not None:
        hints.append("y helps" if dy > 0 else "y hurts")
    label = base + (" (" + ", ".join(hints) + ")" if hints else "")
    return {"label": label, "dominant": dom, "blocking_feasible": bf, "dx": dx, "dy": dy}


# -----------------------------
# 3) Impossible-region explanation
# -----------------------------


def explain_impossible_region(*, report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    pts = report.get("points") or []
    dom_counts: Dict[str, int] = {}
    fail_orders: Dict[str, int] = {}
    infeasible = 0
    for r in pts:
        it = ((r.get("intent") or {}).get(intent) or {})
        if bool(it.get("blocking_feasible")):
            continue
        infeasible += 1
        dom = str(it.get("dominant_blocking") or "PASS")
        dom_counts[dom] = dom_counts.get(dom, 0) + 1
        for nm in (r.get("failure_order_any") or [])[:3]:
            s = str(nm)
            fail_orders[s] = fail_orders.get(s, 0) + 1

    n = int(len(pts))
    if infeasible == 0:
        return {"ok": True, "message": "All points are blocking-feasible under this intent.", "infeasible": 0, "n": n}
    if infeasible == n:
        # fully impossible region
        top = sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        top_fail = sorted(fail_orders.items(), key=lambda kv: kv[1], reverse=True)[:6]
        return {
            "ok": True,
            "message": "No blocking-feasible points exist in this scan window under this intent.",
            "infeasible": infeasible,
            "n": n,
            "dominant_hist": top,
            "early_fail_hist": top_fail,
            "note": "This is a scan-window statement; a different window may contain feasible designs.",
        }
    # partially feasible; still explain infeasible subset
    top = sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "ok": True,
        "message": f"Infeasible subset explanation for {infeasible}/{n} points.",
        "infeasible": infeasible,
        "n": n,
        "dominant_hist": top,
    }


# -----------------------------
# 4) Constraint irrelevance detection
# -----------------------------


def detect_irrelevant_constraints(*, report: Dict[str, Any], intent: str) -> Dict[str, Any]:
    pts = report.get("points") or []
    all_constraints = set()
    dom_used = set()
    failed_any = set()
    for r in pts:
        mh = r.get("margins_hard") or {}
        for nm in mh.keys():
            all_constraints.add(str(nm))
        it = ((r.get("intent") or {}).get(intent) or {})
        dom = it.get("dominant_blocking")
        if dom:
            dom_used.add(str(dom))
        for nm, m in mh.items():
            mm = _safe_float(m)
            if mm is not None and mm < 0:
                failed_any.add(str(nm))

    irrelevant = sorted(list(all_constraints - failed_any - dom_used))
    return {
        "ok": True,
        "n_constraints_seen": int(len(all_constraints)),
        "n_irrelevant": int(len(irrelevant)),
        "irrelevant": irrelevant[:50],
        "note": "Irrelevant here means: never failed and never dominant within this scan window.",
    }


# -----------------------------
# 5) Projection stability checks
# -----------------------------


def projection_stability_check(
    *,
    evaluator,
    base_inputs,
    report: Dict[str, Any],
    intent: str,
    i0: int,
    j0: int,
    z_key: str,
    rel_step: float = 0.05,
    n: int = 7,
) -> Dict[str, Any]:
    """Perturb a 3rd variable around a picked cell and report dominance stability."""
    from tools.scan_cartography import intent_feasible

    # base point at cell
    pts = _neighbors(report, i0=i0, j0=j0, radius=0)
    if not pts:
        return {"ok": False, "reason": "cell_not_found"}
    r0 = pts[0]

    x_key = str(report.get("x_key"))
    y_key = str(report.get("y_key"))
    x = float(r0.get("x"))
    y = float(r0.get("y"))
    p0 = replace(base_inputs, **{x_key: x, y_key: y})
    if not hasattr(p0, z_key):
        return {"ok": False, "reason": "z_key_not_in_inputs"}
    z0 = _safe_float(getattr(p0, z_key))
    if z0 is None:
        return {"ok": False, "reason": "z0_not_numeric"}

    # sample z values
    zs = []
    for k in range(int(max(3, n))):
        t = -1.0 + 2.0 * (k / float(max(1, n - 1)))
        zs.append(z0 * (1.0 + rel_step * t))

    doms: List[str] = []
    oks: List[bool] = []
    for z in zs:
        p = replace(p0, **{z_key: float(z)})
        res = evaluator.evaluate(p)
        cons = (dict(res.out or {}).get("constraints") or [])
        s = intent_feasible(cons, intent)
        doms.append(str(s.get("dominant_blocking") or "PASS"))
        oks.append(bool(s.get("blocking_feasible")))

    # stability score
    mode_dom = max(set(doms), key=lambda d: doms.count(d)) if doms else "PASS"
    frac_mode = doms.count(mode_dom) / float(len(doms) or 1)
    return {
        "ok": True,
        "z_key": str(z_key),
        "z0": float(z0),
        "rel_step": float(rel_step),
        "zs": [float(z) for z in zs],
        "dominant": doms,
        "blocking_feasible": oks,
        "mode_dominant": mode_dom,
        "dominant_stability": float(frac_mode),
        "note": "If stability is low, the 2D projection may be misleading near this point.",
    }


# -----------------------------
# 6) Path-following scans
# -----------------------------


def path_follow(
    *,
    evaluator,
    base_inputs,
    x_key: str,
    y_key: str,
    x_vals: List[float],
    target_key: str,
    target_value: float,
    y_bounds: Tuple[float, float],
    max_iter: int = 30,
) -> Dict[str, Any]:
    """Follow a trajectory by adjusting y to hold a target output ~ constant.

    Uses bisection on y for each x. Deterministic.
    """

    lo0, hi0 = float(y_bounds[0]), float(y_bounds[1])
    rows = []
    for xv in x_vals:
        lo, hi = lo0, hi0
        best = None
        for _ in range(int(max_iter)):
            ym = 0.5 * (lo + hi)
            p = replace(base_inputs, **{x_key: float(xv), y_key: float(ym)})
            res = evaluator.evaluate(p)
            out = dict(res.out or {})
            tv = _safe_float(out.get(target_key))
            if tv is None:
                break
            best = (ym, tv, out)
            if tv < float(target_value):
                lo = ym
            else:
                hi = ym
        if best is None:
            rows.append({"x": float(xv), "y": None, "target": None, "ok": False})
        else:
            ym, tv, out = best
            rows.append({"x": float(xv), "y": float(ym), "target": float(tv), "ok": True})

    return {
        "ok": True,
        "x_key": str(x_key),
        "y_key": str(y_key),
        "target_key": str(target_key),
        "target_value": float(target_value),
        "y_bounds": [float(lo0), float(hi0)],
        "rows": rows,
        "note": "This is a numerical path follow; if the target is not reachable within bounds, points may fail.",
    }


# -----------------------------
# 7) Assumption stress highlighting
# -----------------------------


def assumption_stress_hotspots(*, report: Dict[str, Any], intent: str, tol: float = 0.05) -> Dict[str, Any]:
    """Identify constraints whose margins hover near zero (assumption-sensitive)."""
    pts = report.get("points") or []
    near_counts: Dict[str, int] = {}
    total = 0
    for r in pts:
        mh = r.get("margins_hard") or {}
        for nm, m in mh.items():
            mm = _safe_float(m)
            if mm is None:
                continue
            total += 1
            if abs(mm) <= float(tol):
                near_counts[str(nm)] = near_counts.get(str(nm), 0) + 1
    top = sorted(near_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "ok": True,
        "tol": float(tol),
        "near_zero_hist": top,
        "note": "Constraints frequently near margin≈0 are sensitive to limit assumptions or small modeling changes.",
    }


# -----------------------------
# 8) Counterfactual lenses
# -----------------------------


def counterfactual_feasibility(*, report: Dict[str, Any], intent: str, remove_constraint: str) -> Dict[str, Any]:
    """Recompute intent-feasibility while ignoring one hard constraint (viz-only)."""
    from tools.scan_cartography import classify_constraints_by_intent

    rm = (remove_constraint or "").strip().lower()
    pts = report.get("points") or []
    out_pts = []
    for r in pts:
        mh = r.get("margins_hard") or {}
        cons = []
        # reconstruct minimal constraint list with name, margin, passed, severity
        for nm, m in mh.items():
            if str(nm).strip().lower() == rm:
                continue
            mm = _safe_float(m)
            if mm is None:
                continue
            cons.append({"name": str(nm), "severity": "hard", "margin_frac": float(mm), "passed": bool(mm >= 0)})
        cls = classify_constraints_by_intent(cons, intent)
        blocking = cls.get("blocking") or []
        if not blocking:
            bf = True
            dom = "PASS"
            minm = float("inf")
        else:
            minm = min(float(c.get("margin_frac", 0.0)) for c in blocking)
            bf = bool(minm >= 0)
            dom = "PASS" if bf else str(min(blocking, key=lambda c: float(c.get("margin_frac", 0.0))).get("name"))
        out_pts.append({"i": int(r.get("i")), "j": int(r.get("j")), "blocking_feasible": bf, "dominant": dom, "min_margin": minm})
    return {"ok": True, "intent": str(intent), "removed": str(remove_constraint), "points": out_pts}


# -----------------------------
# 9) Guided insight mode
# -----------------------------


GUIDED_STEPS: List[Dict[str, str]] = [
    {
        "title": "1) Dominance first",
        "text": "Start with the constraint-dominance map. Ask: which limit shapes the landscape?",
    },
    {
        "title": "2) Find cliffs",
        "text": "Look for dominance-boundary flips and topology alerts. These are regime changes.",
    },
    {
        "title": "3) Intent split",
        "text": "Switch Research vs Reactor. Same physics; different acceptance. Note what vanishes.",
    },
    {
        "title": "4) Robustness",
        "text": "Check Robust/Brittle labeling and local feasible fraction. Avoid knife-edge regions.",
    },
    {
        "title": "5) Explain a point",
        "text": "Click a surprising cell; inspect failure order and causality trace.",
    },
]


def guided_steps() -> List[Dict[str, Any]]:
    """Return a small scripted walkthrough to help users build intuition."""
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(GUIDED_STEPS, start=1):
        out.append({
            "step": int(i),
            "title": str(s.get("title", "")),
            "hint": str(s.get("text", "")),
        })
    return out


# -----------------------------
# Compatibility wrappers for UI
# -----------------------------


def path_follow_scan(*, evaluator, base_inputs, x_key: str, y_key: str, x_vals: List[float], target_output: str, intent: str = "Reactor") -> Dict[str, Any]:
    """UI-friendly wrapper around :func:`path_follow`.

    Args:
        target_output: output key to hold approximately constant.
    """
    # Determine target value from the baseline point (current base inputs)
    res0 = evaluator.evaluate(base_inputs)
    out0 = dict(res0.out or {})
    tv = _safe_float(out0.get(target_output))
    if tv is None:
        return {"ok": False, "reason": "target_output_not_numeric"}

    # Choose y bounds conservatively around the baseline value
    y0 = _safe_float(getattr(base_inputs, y_key, None))
    if y0 is None:
        y0 = 0.0
    y_bounds = (float(y0) * 0.5 if float(y0) != 0 else -1.0, float(y0) * 1.5 if float(y0) != 0 else 1.0)
    if y_bounds[0] == y_bounds[1]:
        y_bounds = (float(y_bounds[0]) - 1.0, float(y_bounds[1]) + 1.0)

    return path_follow(
        evaluator=evaluator,
        base_inputs=base_inputs,
        x_key=x_key,
        y_key=y_key,
        x_vals=x_vals,
        target_key=target_output,
        target_value=float(tv),
        y_bounds=y_bounds,
    )


def counterfactual_lens(*, report: Dict[str, Any], intent: str, drop_constraint: Optional[str] = None, remove_constraint: Optional[str] = None) -> Dict[str, Any]:
    """Wrapper that accepts either drop_constraint or remove_constraint."""
    nm = remove_constraint if remove_constraint is not None else drop_constraint
    return counterfactual_feasibility(report=report, intent=intent, remove_constraint=str(nm or ""))



# -----------------------------
# 10) Reference atlas export (multi-page)
# -----------------------------


def build_scan_atlas_pdf_bytes(*, pages: List[Dict[str, Any]], title: str = "SHAMS — Scan Lab Atlas") -> bytes:
    """Build a multi-page PDF atlas.

    Each page dict must include: {report, intent, map_png, page_title}
    """
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER
    for pg in pages:
        report = pg.get("report") or {}
        intent = str(pg.get("intent") or "Reactor")
        map_png = pg.get("map_png") or b""
        page_title = str(pg.get("page_title") or title)

        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.75 * inch, H - 0.75 * inch, page_title)
        c.setFont("Helvetica", 9)
        c.drawString(0.75 * inch, H - 0.98 * inch, f"Intent: {intent}   x: {report.get('x_key')}   y: {report.get('y_key')}   id: {report.get('id')}")

        # Narrative
        nar = ((report.get("narrative") or {}).get("intents") or {}).get(intent, {})
        c.setFont("Helvetica", 9)
        text = str(nar.get("plain_language") or "")
        y = H - 1.25 * inch
        if text:
            words = text.split()
            line = ""
            for w in words:
                if len(line) + len(w) + 1 > 95:
                    c.drawString(0.75 * inch, y, line)
                    y -= 0.17 * inch
                    line = w
                else:
                    line = f"{line} {w}".strip()
            if line:
                c.drawString(0.75 * inch, y, line)

        # Map
        try:
            img = ImageReader(io.BytesIO(map_png))
            c.drawImage(img, 0.75 * inch, 0.75 * inch, width=6.8 * inch, height=3.8 * inch, preserveAspectRatio=True, anchor='sw')
        except Exception:
            c.drawString(0.75 * inch, 4.0 * inch, "(map unavailable)")

        c.showPage()
    c.save()
    return buf.getvalue()


# -----------------------------
# 11) Surprise detector
# -----------------------------


def surprise_regions(*, report: Dict[str, Any], intent: str, radius: int = 1) -> Dict[str, Any]:
    """Identify high-surprise cells: high entropy of local dominance in neighborhood."""
    pts = report.get("points") or []
    # index by (i,j)
    idx: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for r in pts:
        try:
            idx[(int(r.get("i")), int(r.get("j")))] = r
        except Exception:
            pass

    def entropy(doms: List[str]) -> float:
        if not doms:
            return 0.0
        tot = float(len(doms))
        h = 0.0
        for u in set(doms):
            p = doms.count(u) / tot
            if p > 0:
                h -= p * math.log(p + 1e-12)
        return h

    rows = []
    for (i0, j0), r in idx.items():
        doms = []
        for dj in range(-radius, radius + 1):
            for di in range(-radius, radius + 1):
                rr = idx.get((i0 + di, j0 + dj))
                if not rr:
                    continue
                it = ((rr.get("intent") or {}).get(intent) or {})
                doms.append(str(it.get("dominant_blocking") or "PASS"))
        h = entropy(doms)
        rows.append({"i": i0, "j": j0, "x": float(r.get("x")), "y": float(r.get("y")), "entropy": h})
    rows.sort(key=lambda rr: float(rr.get("entropy", 0.0)), reverse=True)
    return {
        "ok": True,
        "intent": str(intent),
        "radius": int(radius),
        "top": rows[:25],
        "note": "High local dominance entropy indicates regime boundaries or surprising transitions.",
    }
