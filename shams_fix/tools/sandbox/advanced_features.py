from __future__ import annotations

"""Optimization Sandbox — World-class feature extensions.

Implements Tier-1…Tier-4 upgrades in a lightweight, SHAMS-consistent way.

Discipline:
- Frozen evaluator remains the only truth.
- These tools propose/analyze/explain; they never relax constraints.
- All results are explicitly labeled non-authoritative.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import math
import numpy as np

try:
    from sklearn.cluster import KMeans
except Exception:  # pragma: no cover
    KMeans = None  # type: ignore


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _vector(inp: Dict[str, Any], keys: Sequence[str]) -> np.ndarray:
    return np.array([_safe_float(inp.get(k)) for k in keys], dtype=float)


def constraint_surface_surf_proposals(
    *,
    archive: List[Dict[str, Any]],
    var_keys: Sequence[str],
    constraint_name: str,
    n_proposals: int = 40,
    step_scale: float = 0.15,
    rng: Optional[np.random.Generator] = None,
) -> List[Dict[str, Any]]:
    """Tier-1: constraint-surface surfing proposals.

    Uses near-boundary points (signed_margin ~ 0) to fit a local linear model:
        m(x) ~= a + g·x
    and proposes steps approximately tangent to the surface (orthogonal to g).

    This is intentionally lightweight and uses archive data only.
    """
    rng = rng or np.random.default_rng(0)
    # collect near-boundary feasible-ish points for this constraint
    pts = []
    ms = []
    for r in archive or []:
        cons = r.get("constraints") or []
        sm = None
        for c in cons:
            if str(c.get("name")) == str(constraint_name):
                sm = _safe_float(c.get("signed_margin"))
                break
        if sm is None or not math.isfinite(sm):
            continue
        inp = r.get("inputs") or {}
        x = _vector(inp, var_keys)
        if not np.all(np.isfinite(x)):
            continue
        # accept points in a band around the surface
        if abs(sm) <= 0.25:
            pts.append(x)
            ms.append(sm)
    if len(pts) < max(8, len(var_keys) + 3):
        return []
    X = np.vstack(pts)
    y = np.array(ms, dtype=float)
    # linear regression with intercept
    A = np.c_[np.ones((X.shape[0], 1)), X]
    try:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    except Exception:
        return []
    g = coef[1:]
    ng = np.linalg.norm(g)
    if not math.isfinite(ng) or ng < 1e-12:
        return []
    g = g / ng
    # choose a handful of base points near the boundary
    base_idx = rng.choice(np.arange(X.shape[0]), size=min(12, X.shape[0]), replace=False)
    props: List[Dict[str, Any]] = []
    for _ in range(int(n_proposals)):
        b = X[int(rng.choice(base_idx))].copy()
        # random direction then project to tangent plane (remove g component)
        d = rng.normal(size=b.shape[0])
        d = d - np.dot(d, g) * g
        nd = np.linalg.norm(d)
        if nd < 1e-12:
            continue
        d = d / nd
        step = float(step_scale) * float(rng.uniform(0.5, 1.5))
        x_new = b + step * d
        props.append({k: float(v) for k, v in zip(var_keys, x_new.tolist())})
    return props


def constraint_surface_map(
    *,
    archive: List[Dict[str, Any]],
    var_keys: Sequence[str],
    constraint_name: str,
) -> Dict[str, Any]:
    """Build a local, transparent linear surface model for one constraint.

    Fits signed_margin ≈ a + g·x using near-boundary points (|margin| <= 0.25).
    Returns a normalized gradient vector g (surface normal) and a simple tangent basis.

    This is an *instrument*: it summarizes geometry implied by evaluated archive data.
    """
    pts = []
    ms = []
    for r in archive or []:
        cons = r.get("constraints") or []
        sm = None
        for c in cons:
            if str(c.get("name")) == str(constraint_name):
                sm = _safe_float(c.get("signed_margin"))
                break
        if sm is None or not math.isfinite(sm):
            continue
        if abs(sm) > 0.25:
            continue
        x = _vector(r.get("inputs") or {}, var_keys)
        if not np.all(np.isfinite(x)):
            continue
        pts.append(x)
        ms.append(sm)

    if len(pts) < max(8, len(var_keys) + 3):
        return {
            "ok": False,
            "reason": "insufficient_near_boundary_points",
            "n_used": int(len(pts)),
            "constraint": str(constraint_name),
            "var_keys": list(var_keys),
        }

    X = np.vstack(pts)
    y = np.array(ms, dtype=float)
    A = np.c_[np.ones((X.shape[0], 1)), X]
    try:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    except Exception:
        return {"ok": False, "reason": "lstsq_failed", "n_used": int(len(pts))}
    g = coef[1:]
    ng = float(np.linalg.norm(g))
    if not math.isfinite(ng) or ng < 1e-12:
        return {"ok": False, "reason": "degenerate_gradient", "n_used": int(len(pts))}
    g = g / ng

    # Build a simple tangent basis: pick two random directions and orthogonalize
    # against g. If dimension=1, basis is empty.
    basis = []
    if len(var_keys) >= 2:
        rng = np.random.default_rng(0)
        for _ in range(3):
            d = rng.normal(size=len(var_keys))
            d = d - float(np.dot(d, g)) * g
            nd = float(np.linalg.norm(d))
            if nd < 1e-12:
                continue
            d = d / nd
            # avoid duplicates
            if basis and abs(float(np.dot(d, np.array(basis[-1], dtype=float)))) > 0.95:
                continue
            basis.append(d.tolist())
            if len(basis) >= 2:
                break

    return {
        "ok": True,
        "constraint": str(constraint_name),
        "var_keys": list(var_keys),
        "n_used": int(len(pts)),
        "gradient_normal": {k: float(v) for k, v in zip(var_keys, g.tolist())},
        "tangent_basis": [{k: float(v) for k, v in zip(var_keys, vec)} for vec in basis],
        "band_abs_margin_max": 0.25,
        "note": "Gradient points in direction of increasing signed_margin (more feasible for this constraint).",
    }


def feasibility_skeleton(
    *,
    archive: List[Dict[str, Any]],
    var_keys: Sequence[str],
    max_nodes: int = 10,
    rng_seed: int = 0,
) -> Dict[str, Any]:
    """Tier-1: Feasibility skeleton extraction.

    Builds a coarse connectivity graph between feasible clusters.
    """
    feas = [r for r in (archive or []) if r.get("feasible", False)]
    if len(feas) < 8:
        return {"n_feasible": len(feas), "clusters": [], "edges": []}
    X = np.array([_vector(r.get("inputs") or {}, var_keys) for r in feas], dtype=float)
    # clean non-finite
    for j in range(X.shape[1]):
        col = X[:, j]
        good = col[np.isfinite(col)]
        med = float(np.median(good)) if good.size else 0.0
        col[~np.isfinite(col)] = med
        X[:, j] = col
    k = int(min(max_nodes, max(2, round(math.sqrt(len(feas) / 2)))))
    if KMeans is None:
        # simple fallback: pick k random representatives
        idx = np.random.default_rng(rng_seed).choice(np.arange(len(feas)), size=k, replace=False)
        centers = X[idx]
        labels = np.argmin(((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2), axis=1)
    else:
        km = KMeans(n_clusters=k, random_state=rng_seed, n_init=10)
        labels = km.fit_predict(X)
        centers = km.cluster_centers_
    clusters = []
    for ci in range(k):
        members = np.where(labels == ci)[0]
        if members.size == 0:
            continue
        # representative: closest member to the cluster center (no "best" semantics)
        # Clustering is descriptive only.
        c0 = centers[ci]
        d2 = ((X[members] - c0[None, :]) ** 2).sum(axis=1)
        best_i = int(members[int(np.argmin(d2))])
        clusters.append({
            "id": int(ci),
            "n": int(members.size),
            "center": {k: float(v) for k, v in zip(var_keys, centers[ci].tolist())},
            "representative": feas[best_i],
        })
    # edges: connect centers by nearest neighbors
    edges = []
    C = np.array([list(c["center"].values()) for c in clusters], dtype=float)
    for i in range(C.shape[0]):
        d = np.linalg.norm(C - C[i], axis=1)
        nn = np.argsort(d)[1: min(3, len(d))]
        for j in nn:
            edges.append({"a": int(clusters[i]["id"]), "b": int(clusters[int(j)]["id"]), "dist": float(d[int(j)])})
    return {"n_feasible": len(feas), "clusters": clusters, "edges": edges}


def multi_intent_audit(
    *,
    evaluate_fn: Callable[[Dict[str, Any], str], Dict[str, Any]],
    cand_inputs: Dict[str, Any],
    intents: Sequence[str] = ("Reactor", "Research"),
) -> Dict[str, Any]:
    """Tier-1: Multi-intent evaluation for the same candidate."""
    out = {}
    for it in intents:
        out[str(it)] = evaluate_fn(dict(cand_inputs), str(it))
    return out


def uq_monte_carlo(
    *,
    evaluate_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    base_inputs: Dict[str, Any],
    var_keys: Sequence[str],
    sigma_frac: float = 0.03,
    n: int = 60,
    seed: int = 0,
) -> Dict[str, Any]:
    """Tier-3: Input-uncertainty propagation via Monte Carlo.

    We perturb selected variables (Gaussian, fractional sigma) and re-audit.
    Reports probability of feasibility and distribution of score/margins.
    """
    rng = np.random.default_rng(int(seed))
    feas = 0
    scores = []
    margins = []
    for i in range(int(n)):
        cand = dict(base_inputs)
        for k in var_keys:
            v0 = _safe_float(base_inputs.get(k))
            if not math.isfinite(v0) or v0 == 0:
                continue
            cand[k] = float(v0 * (1.0 + rng.normal(scale=float(sigma_frac))))
        r = evaluate_fn(cand)
        if r.get("feasible", False):
            feas += 1
        scores.append(_safe_float(r.get("_score")))
        margins.append(_safe_float(r.get("min_signed_margin")))
    scores = np.array(scores, dtype=float)
    margins = np.array(margins, dtype=float)
    return {
        "n": int(n),
        "sigma_frac": float(sigma_frac),
        "p_feasible": float(feas) / float(n) if n else 0.0,
        "score_mean": float(np.nanmean(scores)) if scores.size else float("nan"),
        "score_p10": float(np.nanpercentile(scores, 10)) if scores.size else float("nan"),
        "score_p90": float(np.nanpercentile(scores, 90)) if scores.size else float("nan"),
        "margin_mean": float(np.nanmean(margins)) if margins.size else float("nan"),
        "margin_p10": float(np.nanpercentile(margins, 10)) if margins.size else float("nan"),
        "margin_p90": float(np.nanpercentile(margins, 90)) if margins.size else float("nan"),
    }


def local_adaptive_cartography(
    *,
    evaluate_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    anchor_inputs: Dict[str, Any],
    x_key: str,
    y_key: str,
    x_span_frac: float = 0.08,
    y_span_frac: float = 0.08,
    n: int = 21,
) -> Dict[str, Any]:
    """Tier-3: Optimization-native local cartography (adaptive micro-scan).

    Creates a small 2D grid around an anchor (usually best feasible) and evaluates.
    Returns dominance labels and feasibility fraction.
    """
    x0 = _safe_float(anchor_inputs.get(x_key))
    y0 = _safe_float(anchor_inputs.get(y_key))
    if not (math.isfinite(x0) and math.isfinite(y0)):
        return {"ok": False, "reason": "non_finite_anchor"}
    xs = np.linspace(x0 * (1 - x_span_frac), x0 * (1 + x_span_frac), int(n))
    ys = np.linspace(y0 * (1 - y_span_frac), y0 * (1 + y_span_frac), int(n))
    labels = []
    feas = 0
    for yy in ys:
        row = []
        for xx in xs:
            cand = dict(anchor_inputs)
            cand[x_key] = float(xx)
            cand[y_key] = float(yy)
            r = evaluate_fn(cand)
            if r.get("feasible", False):
                feas += 1
                row.append("PASS")
            else:
                ac = (r.get("active_constraints") or [])
                row.append(str(ac[0]) if ac else "FAIL")
        labels.append(row)
    return {
        "ok": True,
        "x_key": str(x_key),
        "y_key": str(y_key),
        "xs": xs.tolist(),
        "ys": ys.tolist(),
        "labels": labels,
        "feasible_frac": float(feas) / float(len(xs) * len(ys)) if xs.size and ys.size else 0.0,
    }


def process_style_objective_contract() -> Dict[str, Any]:
    """Tier-2: PROCESS emulator objective stack (transparent).

    This is NOT a dependency on PROCESS. It's a common-style scalar contract
    (cost proxy + performance proxy) to help users compare behaviors.
    """
    return {
        "name": "PROCESS-like scalar stack (transparent)",
        "description": "Scalarized objective: minimize COE_proxy and maximize P_e_net. No hidden penalties.",
        "objectives": [
            {"key": "COE_proxy", "sense": "min", "weight": 1.0},
            {"key": "P_e_net_MW", "sense": "max", "weight": 0.15},
        ],
    }


def physics_aware_operator_proposals(
    *,
    base_inputs: Dict[str, Any],
    var_keys: Sequence[str],
    rng: Optional[np.random.Generator] = None,
    n: int = 40,
) -> List[Dict[str, Any]]:
    """Tier-3: Physics-aware mutation/operator proposals.

    Operators are intentionally simple and only touch provided var_keys.
    - scale_size: scale R0 and a together
    - scale_field_current: scale Bt and Ip together
    - aux_power_sweep: sweep Paux
    """
    rng = rng or np.random.default_rng(0)
    out: List[Dict[str, Any]] = []
    for _ in range(int(n)):
        cand = dict(base_inputs)
        op = int(rng.integers(0, 3))
        if op == 0 and ("R0_m" in var_keys or "a_m" in var_keys):
            s = float(rng.uniform(0.92, 1.08))
            if "R0_m" in var_keys and math.isfinite(_safe_float(cand.get("R0_m"))):
                cand["R0_m"] = float(_safe_float(cand.get("R0_m")) * s)
            if "a_m" in var_keys and math.isfinite(_safe_float(cand.get("a_m"))):
                cand["a_m"] = float(_safe_float(cand.get("a_m")) * s)
        elif op == 1 and ("Bt_T" in var_keys or "Ip_MA" in var_keys):
            s = float(rng.uniform(0.93, 1.07))
            if "Bt_T" in var_keys and math.isfinite(_safe_float(cand.get("Bt_T"))):
                cand["Bt_T"] = float(_safe_float(cand.get("Bt_T")) * s)
            if "Ip_MA" in var_keys and math.isfinite(_safe_float(cand.get("Ip_MA"))):
                cand["Ip_MA"] = float(_safe_float(cand.get("Ip_MA")) * s)
        else:
            if "Paux_MW" in var_keys and math.isfinite(_safe_float(cand.get("Paux_MW"))):
                cand["Paux_MW"] = float(_safe_float(cand.get("Paux_MW")) * float(rng.uniform(0.85, 1.20)))
        out.append(cand)
    return out
