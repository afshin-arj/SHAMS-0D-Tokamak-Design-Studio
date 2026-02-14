from __future__ import annotations

"""Scan Lab — Cartography & topology helpers (0‑D framework).

These helpers power the "world‑class" Scan Lab visualizations:

1) Constraint‑Dominance Cartography (killer feature)
2) First‑Failure Topology (cliff intelligence)
3) Intent‑Split feasibility (Research vs Reactor)
4) Optional margin vector fields (advanced)
5) Narrative scan summaries (structured, reproducible)
6) Brutally honest robustness scoring (no marketing)

Design rules:
- Point Designer physics/constraints remain authoritative; we only *map* outputs.
- No optimization, relaxation, or ranking of designs.
- Deterministic and exportable.
"""

from dataclasses import asdict
import hashlib
import json
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))



def _serialize_inputs(obj: Any) -> Dict[str, Any]:
    """Best-effort, JSON-safe snapshot of a PointInputs-like object.

    Purpose: allow downstream tools (e.g., external optimizer clients) to reuse the
    exact base point used in Scan Lab without re-entering all fixed fields.

    This does NOT change physics; it only improves auditability and replay.
    """
    try:
        from dataclasses import asdict, is_dataclass
        if is_dataclass(obj):
            d = asdict(obj)
        elif isinstance(obj, dict):
            d = dict(obj)
        else:
            d = dict(getattr(obj, "__dict__", {}) or {})
    except Exception:
        d = dict(getattr(obj, "__dict__", {}) or {})
    # Make JSON-safe scalars/strings only (leave nested dicts/lists as-is; json will coerce via default=str upstream)
    return d


def _stable_hash(obj: Any) -> str:
    try:
        b = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        b = str(obj).encode("utf-8")
    return hashlib.sha1(b).hexdigest()[:12]


# -----------------------------
# Intent policy (Scan Lab lens)
# -----------------------------

def classify_constraints_by_intent(constraints: List[Dict[str, Any]], intent: str) -> Dict[str, List[Dict[str, Any]]]:
    """Classify constraints into blocking/diagnostic/ignored based on design intent.

    The policy here matches SHAMS intent semantics:
    - Reactor intent: all hard constraints are blocking.
    - Research intent: q95 remains blocking; TBR is ignored; most engineering limits are diagnostic.
    """

    it = (intent or "Reactor").strip().lower()

    blocking: List[Dict[str, Any]] = []
    diagnostic: List[Dict[str, Any]] = []
    ignored: List[Dict[str, Any]] = []

    for c in constraints or []:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", ""))
        sev = str(c.get("severity", "hard")).lower()

        # Non-hard are never blocking
        if sev != "hard":
            diagnostic.append(c)
            continue

        if it.startswith("react"):
            blocking.append(c)
            continue

        # Research intent
        n = name.strip().lower()
        if n.startswith("q95"):
            blocking.append(c)
        elif n == "tbr" or "tbr" in n:
            ignored.append(c)
        else:
            diagnostic.append(c)

    return {
        "blocking": blocking,
        "diagnostic": diagnostic,
        "ignored": ignored,
    }


def _margin(c: Dict[str, Any]) -> float:
    m = c.get("margin_frac")
    try:
        return float(m)
    except Exception:
        # fallback from passed/value/limit if available
        v = c.get("value")
        lim = c.get("limit")
        sense = str(c.get("sense", "<="))
        if not _finite(v) or not _finite(lim) or float(lim) == 0:
            return float("nan")
        if sense.strip() in ("<=", "max"):
            return (float(lim) - float(v)) / float(lim)
        return (float(v) - float(lim)) / float(lim)


def failure_order(constraints: List[Dict[str, Any]], *, only_failed: bool = True) -> List[Dict[str, Any]]:
    """Return constraints sorted by increasing margin (worst first)."""
    rows = []
    for c in constraints or []:
        if not isinstance(c, dict):
            continue
        passed = bool(c.get("passed", True))
        if only_failed and passed:
            continue
        m = _margin(c)
        if not _finite(m):
            continue
        rows.append((m, c))
    rows.sort(key=lambda t: float(t[0]))
    return [c for _, c in rows]


def dominant_constraint(constraints: List[Dict[str, Any]]) -> Optional[str]:
    """Return the 'first' failing constraint name (worst margin) if any."""
    fo = failure_order(constraints, only_failed=True)
    if not fo:
        return None
    return str(fo[0].get("name"))


def min_margin(constraints: List[Dict[str, Any]]) -> float:
    ms = [
        _margin(c)
        for c in (constraints or [])
        if isinstance(c, dict) and _finite(_margin(c))
    ]
    return float(min(ms)) if ms else float("nan")


def intent_feasible(constraints: List[Dict[str, Any]], intent: str) -> Dict[str, Any]:
    cls = classify_constraints_by_intent(constraints, intent)
    blk = cls["blocking"]
    failed_blk = [c for c in blk if not bool(c.get("passed", True))]
    out = {
        "intent": intent,
        "blocking_feasible": (len(failed_blk) == 0),
        "failed_blocking": [str(c.get("name")) for c in failed_blk],
        "failed_diagnostic": [str(c.get("name")) for c in cls["diagnostic"] if not bool(c.get("passed", True))],
        "failed_ignored": [str(c.get("name")) for c in cls["ignored"] if not bool(c.get("passed", True))],
        "dominant_blocking": dominant_constraint(blk),
        "dominant_any": dominant_constraint([c for c in constraints if isinstance(c, dict) and str(c.get("severity","hard")).lower()=="hard"]),
        "min_blocking_margin": min_margin(blk),
    }
    return out


def robustness_label(p: float) -> str:
    """Brutally honest robustness label from local feasibility probability."""
    if not _finite(p):
        return "Unknown"
    p = float(p)
    if p >= 0.85:
        return "Robust"
    if p >= 0.60:
        return "Balanced"
    if p >= 0.30:
        return "Brittle"
    return "Knife-edge"


def local_robustness(grid_ok: List[List[bool]], i: int, j: int, *, radius: int = 1) -> float:
    """Local neighborhood feasibility fraction (Moore neighborhood)."""
    ny = len(grid_ok)
    nx = len(grid_ok[0]) if ny else 0
    if ny == 0 or nx == 0:
        return float("nan")
    c = 0
    t = 0
    for jj in range(max(0, j - radius), min(ny, j + radius + 1)):
        for ii in range(max(0, i - radius), min(nx, i + radius + 1)):
            t += 1
            if bool(grid_ok[jj][ii]):
                c += 1
    return c / max(t, 1)


def _extract_boundary_segments(ok_grid: List[List[bool]], x_vals: List[float], y_vals: List[float]) -> List[Dict[str, Any]]:
    """Deterministic boundary extractor for a boolean feasibility grid.

    Returns a list of axis-aligned boundary segments along cell edges where feasibility flips.
    This is intentionally simple (no marching-squares stitching) but is reviewer-safe and stable.
    Each segment is represented as {x0,y0,x1,y1}.
    """
    ny = len(ok_grid)
    nx = len(ok_grid[0]) if ny else 0
    if ny == 0 or nx == 0:
        return []
    if len(x_vals) != nx or len(y_vals) != ny:
        return []

    def x_edge(i0: int, i1: int) -> float:
        if i0 == i1:
            return float(x_vals[i0])
        return 0.5 * (float(x_vals[i0]) + float(x_vals[i1]))

    def y_edge(j0: int, j1: int) -> float:
        if j0 == j1:
            return float(y_vals[j0])
        return 0.5 * (float(y_vals[j0]) + float(y_vals[j1]))

    segs: List[Dict[str, Any]] = []

    for j in range(ny):
        for i in range(1, nx):
            a = bool(ok_grid[j][i-1])
            b = bool(ok_grid[j][i])
            if a == b:
                continue
            x = x_edge(i-1, i)
            y0 = y_edge(max(j-1, 0), j) if j > 0 else float(y_vals[j])
            y1 = y_edge(j, min(j+1, ny-1)) if j < ny-1 else float(y_vals[j])
            if y1 < y0:
                y0, y1 = y1, y0
            segs.append({"x0": float(x), "y0": float(y0), "x1": float(x), "y1": float(y1)})

    for j in range(1, ny):
        for i in range(nx):
            a = bool(ok_grid[j-1][i])
            b = bool(ok_grid[j][i])
            if a == b:
                continue
            y = y_edge(j-1, j)
            x0 = x_edge(max(i-1, 0), i) if i > 0 else float(x_vals[i])
            x1 = x_edge(i, min(i+1, nx-1)) if i < nx-1 else float(x_vals[i])
            if x1 < x0:
                x0, x1 = x1, x0
            segs.append({"x0": float(x0), "y0": float(y), "x1": float(x1), "y1": float(y)})

    segs.sort(key=lambda s: (s["y0"], s["x0"], s["y1"], s["x1"]))
    return segs


def _build_field_cube(points: List[Dict[str, Any]], *, x_vals: List[float], y_vals: List[float], intents: List[str]) -> Dict[str, Any]:
    """Build a labelled 2D field-cube for downstream plotting and evidence.

    This is SHAMS-owned (no xarray dependency) but mirrors the labelled-semantic pattern.
    Arrays are stored as nested lists [j][i] (row-major, y then x).
    """
    ny = len(y_vals)
    nx = len(x_vals)
    grid = [[None for _ in range(nx)] for _ in range(ny)]
    for p in points or []:
        try:
            i = int(p.get("i"))
            j = int(p.get("j"))
            if 0 <= j < ny and 0 <= i < nx:
                grid[j][i] = p
        except Exception:
            pass

    cube: Dict[str, Any] = {
        "schema": "shams_field_cube.v1",
        "dims": {"x": int(nx), "y": int(ny)},
        "coords": {"x": [float(v) for v in x_vals], "y": [float(v) for v in y_vals]},
        "intent_vars": {},
        "vars": {},
        "notes": "All arrays are [j][i] indexing (y then x). Values are JSON-safe scalars/strings.",
    }

    for it in intents or []:
        ok = [[False for _ in range(nx)] for _ in range(ny)]
        dom = [["" for _ in range(nx)] for _ in range(ny)]
        minm = [[float("nan") for _ in range(nx)] for _ in range(ny)]
        rob = [["" for _ in range(nx)] for _ in range(ny)]
        pfe = [[float("nan") for _ in range(nx)] for _ in range(ny)]
        for j in range(ny):
            for i in range(nx):
                cell = grid[j][i] or {}
                s = ((cell.get("intent") or {}).get(str(it)) or {})
                ok[j][i] = bool(s.get("blocking_feasible"))
                dom[j][i] = str(s.get("dominant_blocking") or ("PASS" if ok[j][i] else ""))
                try:
                    minm[j][i] = float(s.get("min_blocking_margin", float("nan")))
                except Exception:
                    minm[j][i] = float("nan")
                rob[j][i] = str(s.get("robustness") or "")
                try:
                    pfe[j][i] = float(s.get("local_p_feasible", float("nan")))
                except Exception:
                    pfe[j][i] = float("nan")
        cube["intent_vars"][str(it)] = {
            "blocking_feasible": ok,
            "dominant_blocking": dom,
            "min_blocking_margin": minm,
            "robustness": rob,
            "local_p_feasible": pfe,
        }

    if any(isinstance((grid[j][i] or {}).get("outputs"), dict) for j in range(ny) for i in range(nx)):
        keys = set()
        for j in range(ny):
            for i in range(nx):
                outs = (grid[j][i] or {}).get("outputs")
                if isinstance(outs, dict):
                    keys |= set(outs.keys())
        for k in sorted(keys):
            arr = [[float("nan") for _ in range(nx)] for _ in range(ny)]
            for j in range(ny):
                for i in range(nx):
                    outs = (grid[j][i] or {}).get("outputs")
                    if isinstance(outs, dict) and k in outs:
                        try:
                            v = outs.get(k)
                            arr[j][i] = float(v) if _finite(v) else float("nan")
                        except Exception:
                            arr[j][i] = float("nan")
            cube["vars"][str(k)] = arr

    return cube



def build_cartography_report(
    *,
    evaluator,
    base_inputs,
    x_key: str,
    y_key: str,
    x_vals: List[float],
    y_vals: List[float],
    intents: List[str],
    include_outputs: bool = False,
    include_margins: bool = True,
    progress_cb=None,
) -> Dict[str, Any]:
    """Run a deterministic 2D scan and compute dominance/topology/intent split.

    Returns a JSON-serializable report.
    """
    if not intents:
        intents = ["Reactor"]

    pts: List[Dict[str, Any]] = []
    # Preallocate for robustness computation per intent
    ok_grid: Dict[str, List[List[bool]]] = {it: [[False for _ in x_vals] for _ in y_vals] for it in intents}

    # Evaluate all points once (constraints are intent-agnostic; policy lens applied later)
    total = max(len(x_vals) * len(y_vals), 1)
    done = 0
    for j, y in enumerate(y_vals):
        for i, x in enumerate(x_vals):
            inp = base_inputs
            # dataclass (frozen) => use replace if available
            try:
                from dataclasses import replace
                inp = replace(inp, **{x_key: float(x), y_key: float(y)})
            except Exception:
                # fallback: shallow copy dict
                d = getattr(base_inputs, "__dict__", {})
                d2 = dict(d)
                d2[x_key] = float(x)
                d2[y_key] = float(y)
                inp = type(base_inputs)(**d2)

            res = evaluator.evaluate(inp)
            out = dict(res.out or {})
            cons = out.get("constraints") or []

            # Per-intent feasibility
            intent_summ = {}
            for it in intents:
                s = intent_feasible(cons, it)
                intent_summ[it] = s
                ok_grid[it][j][i] = bool(s.get("blocking_feasible"))

            row = {
                "i": int(i),
                "j": int(j),
                "x": float(x),
                "y": float(y),
                "inputs": {x_key: float(x), y_key: float(y)},
                "intent": intent_summ,
                "failure_order_any": [str(c.get("name")) for c in failure_order(cons, only_failed=True)[:6]],
            }

            # Optional: include hard-constraint margins for iso-contours and interaction analysis.
            # Keep this compact: name -> margin_frac, only for hard constraints.
            if include_margins:
                mh: Dict[str, float] = {}
                for c in cons or []:
                    if not isinstance(c, dict):
                        continue
                    if str(c.get("severity", "hard")).lower() != "hard":
                        continue
                    nm = str(c.get("name", "")).strip()
                    if not nm:
                        continue
                    m = _margin(c)
                    if _finite(m):
                        mh[nm] = float(m)
                row["margins_hard"] = mh
            if include_outputs:
                # keep it compact; avoid giant exports by default
                keep = {k: out.get(k) for k in ["Q", "Q_DT_eqv", "P_fus_MW", "P_e_net_MW", "q_div_MW_m2", "B_peak_T", "q95", "betaN", "fG"] if k in out}
                row["outputs"] = keep
            pts.append(row)

            done += 1
            if callable(progress_cb) and (done == 1 or done == total or (done % max(1, total // 100) == 0)):
                try:
                    progress_cb(done, total)
                except Exception:
                    pass

    # Add local robustness labels
    for row in pts:
        i = int(row["i"])
        j = int(row["j"])
        for it in intents:
            p = local_robustness(ok_grid[it], i, j, radius=1)
            row["intent"][it]["local_p_feasible"] = p
            row["intent"][it]["robustness"] = robustness_label(p)

    # Narrative summary (structured)
    narrative = build_narrative(pts, intents=intents)

    # Feasible-region topology per intent (alerts: disconnection / holes)
    topology = {it: analyze_grid_topology(ok_grid[it]) for it in intents}

    # Constraint interaction map (from failure orders)
    interaction = build_constraint_interaction(points=pts, intents=intents)


    # Boundary extraction (reviewer-safe, deterministic) for each intent
    boundaries: Dict[str, Any] = {}
    for it in intents:
        try:
            boundaries[str(it)] = {
                "schema": "shams_boundary_segments.v1",
                "segments": _extract_boundary_segments(ok_grid[it], x_vals, y_vals),
            }
        except Exception:
            boundaries[str(it)] = {"schema": "shams_boundary_segments.v1", "segments": []}

    # Field-cube export (labelled semantics; no external deps)
    field_cube = _build_field_cube(pts, x_vals=x_vals, y_vals=y_vals, intents=intents)


    report = {
        "kind": "shams_scan_cartography",
        "schema_version": 1,
        "base_inputs": _serialize_inputs(base_inputs),
        "base_inputs_hash": _stable_hash(_serialize_inputs(base_inputs)),
        "x_key": str(x_key),
        "y_key": str(y_key),
        "x_vals": [float(v) for v in x_vals],
        "y_vals": [float(v) for v in y_vals],
        "intents": list(intents),
        "n_points": int(len(pts)),
        "points": pts,
        "narrative": narrative,
        "topology": topology,
        "interaction": interaction,
        "boundaries": boundaries,
        "field_cube": field_cube,
        "id": _stable_hash({"x": x_key, "y": y_key, "xv": x_vals, "yv": y_vals, "intents": intents}),
    }
    return report


def analyze_grid_topology(ok_grid: List[List[bool]]) -> Dict[str, Any]:
    """Lightweight topology diagnostics for a 2D feasibility grid.

    Returns:
      - n_components (4-neighborhood)
      - largest_component_frac
      - has_holes (approx: infeasible cells fully surrounded by feasible)
    """
    ny = len(ok_grid)
    nx = len(ok_grid[0]) if ny else 0
    if ny == 0 or nx == 0:
        return {"n_components": 0, "largest_component_frac": 0.0, "has_holes": False}

    # components
    seen = [[False for _ in range(nx)] for _ in range(ny)]
    comps = []
    for j in range(ny):
        for i in range(nx):
            if seen[j][i] or not bool(ok_grid[j][i]):
                continue
            stack = [(i, j)]
            seen[j][i] = True
            cnt = 0
            while stack:
                x, y = stack.pop()
                cnt += 1
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x+dx, y+dy
                    if 0 <= xx < nx and 0 <= yy < ny and (not seen[yy][xx]) and bool(ok_grid[yy][xx]):
                        seen[yy][xx] = True
                        stack.append((xx, yy))
            comps.append(cnt)
    comps.sort(reverse=True)
    n_ok = sum(1 for j in range(ny) for i in range(nx) if bool(ok_grid[j][i]))
    largest = comps[0] if comps else 0
    n_components = len(comps)

    # hole heuristic: infeasible cell whose 4-neighbors are feasible (not on boundary)
    holes = 0
    for j in range(1, ny-1):
        for i in range(1, nx-1):
            if bool(ok_grid[j][i]):
                continue
            if bool(ok_grid[j][i-1]) and bool(ok_grid[j][i+1]) and bool(ok_grid[j-1][i]) and bool(ok_grid[j+1][i]):
                holes += 1
    return {
        "n_components": int(n_components),
        "largest_component_frac": (float(largest) / max(float(n_ok), 1.0)),
        "has_holes": bool(holes > 0),
        "hole_count": int(holes),
    }


def build_constraint_interaction(*, points: List[Dict[str, Any]], intents: List[str], top_n: int = 10) -> Dict[str, Any]:
    """Build a simple interaction map from failure orders.

    For each intent, counts how often constraint A appears before B in the failure list.
    Uses only the first-failure order of hard constraints captured in points.
    """
    out: Dict[str, Any] = {"intents": {}}
    # global candidate set from failure lists
    all_names: List[str] = []
    for p in points or []:
        fo = p.get("failure_order_any")
        if isinstance(fo, list):
            for n in fo:
                if isinstance(n, str) and n:
                    all_names.append(n)
    # most frequent
    freq: Dict[str, int] = {}
    for n in all_names:
        freq[n] = freq.get(n, 0) + 1
    names = [k for k, _ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]

    for it in intents or []:
        mat = {a: {b: 0 for b in names} for a in names}
        for p in points or []:
            fo = p.get("failure_order_any")
            if not isinstance(fo, list):
                continue
            # order index map
            idx = {str(n): i for i, n in enumerate(fo) if str(n) in names}
            for a in names:
                for b in names:
                    if a == b:
                        continue
                    if a in idx and b in idx and idx[a] < idx[b]:
                        mat[a][b] += 1
        out["intents"][it] = {"names": names, "before_counts": mat}
    return out


def build_narrative(points: List[Dict[str, Any]], *, intents: List[str]) -> Dict[str, Any]:
    """Structured scan narrative: dominant limits, feasibility rate, cliffiness."""
    out: Dict[str, Any] = {"intents": {}}
    for it in intents:
        dom_counts: Dict[str, int] = {}
        ok = 0
        tot = 0
        cliff = 0
        last_dom: Optional[str] = None
        for p in points:
            s = (p.get("intent") or {}).get(it, {})
            tot += 1
            if bool(s.get("blocking_feasible")):
                ok += 1
            dom = s.get("dominant_blocking") or "PASS"
            dom_counts[str(dom)] = dom_counts.get(str(dom), 0) + 1
            if last_dom is not None and str(dom) != str(last_dom):
                cliff += 1
            last_dom = dom
        # rank dominance
        ranked = sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)
        top = [{"constraint": k, "share": v / max(tot, 1), "count": v} for k, v in ranked[:8]]

        out["intents"][it] = {
            "blocking_feasible_rate": ok / max(tot, 1),
            "dominance_ranked": top,
            "cliffiness_proxy": cliff / max(tot - 1, 1),
            "plain_language": _plain_language(it, ok / max(tot, 1), top),
        }
    return out


def _plain_language(intent: str, feasible_rate: float, top: List[Dict[str, Any]]) -> str:
    it = intent
    dom = top[0]["constraint"] if top else "(none)"
    share = (top[0]["share"] if top else 0.0)
    f = feasible_rate
    if f >= 0.8:
        feel = "a large contiguous feasible region"
    elif f >= 0.4:
        feel = "a mixed feasibility region with meaningful tradeoffs"
    else:
        feel = "a mostly infeasible region with narrow islands"
    return (
        f"Under **{it}** intent, this scan shows {feel} (blocking-feasible fraction ≈ {f:.0%}). "
        f"The most common limiting constraint is **{dom}** (≈ {share:.0%} of points)."
    )
