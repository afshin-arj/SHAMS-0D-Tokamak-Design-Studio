from __future__ import annotations

"""Optimization Sandbox — Tier 5 & 6 instruments.

These tools are intentionally *instrumental*:
- They never change the frozen evaluator physics.
- They can introduce **hypothetical lenses** (counterfactual constraint disable),
  but always label outputs as hypothetical and keep raw evaluator results.

Tier 5
  - Intent trajectories (Research → Reactor highways)
  - Constraint credibility overlays (maturity / uncertainty)
  - Inverse design helpers ("closest feasible", "why not")

Tier 6
  - Optimization-derived laws / relations mined from archives
  - Counterfactual optimization lens (disable a constraint in the *gate* only)

All functions are deterministic given inputs.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import math
import json

import numpy as np


def _sf(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _vec(inp: Dict[str, Any], keys: Sequence[str]) -> np.ndarray:
    return np.array([_sf(inp.get(k)) for k in keys], dtype=float)


def _finite_rows(X: np.ndarray) -> np.ndarray:
    if X.size == 0:
        return X
    X2 = X.copy()
    for j in range(X2.shape[1]):
        col = X2[:, j]
        good = col[np.isfinite(col)]
        fill = float(np.median(good)) if good.size else 0.0
        col[~np.isfinite(col)] = fill
        X2[:, j] = col
    return X2


# -------------------------
# Constraint credibility
# -------------------------


@dataclass(frozen=True)
class ConstraintCred:
    name: str
    maturity: float = 0.7  # 0..1
    uncertainty_frac: float = 0.10  # 0..0.5
    conservative: bool = True


def credibility_adjusted_margin(signed_margin: float, cred: ConstraintCred) -> float:
    """Compute an adjusted margin used for *overlay* and filtering.

    This does NOT change the frozen truth. It is a user-selected epistemic lens:
    - Lower maturity / higher uncertainty makes the adjusted margin smaller.
    - conservative=True uses a stronger adjustment.
    """
    sm = _sf(signed_margin)
    if not math.isfinite(sm):
        return float("nan")
    m = float(np.clip(_sf(cred.maturity), 0.0, 1.0))
    u = float(np.clip(_sf(cred.uncertainty_frac), 0.0, 0.8))
    # Conservative adjustment: shrink margin by (1+u)/(m+eps)
    eps = 0.05
    if cred.conservative:
        denom = max(m, eps)
        return float(sm / ((1.0 + u) / denom))
    # Non-conservative: shrink only by uncertainty
    return float(sm / (1.0 + u))


def apply_credibility_overlay(
    constraints: List[Dict[str, Any]],
    cred_map: Dict[str, ConstraintCred],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in constraints or []:
        rr = dict(r)
        nm = str(rr.get("name", ""))
        cred = cred_map.get(nm)
        if cred is not None:
            rr["credibility"] = {
                "maturity": float(cred.maturity),
                "uncertainty_frac": float(cred.uncertainty_frac),
                "conservative": bool(cred.conservative),
            }
            rr["signed_margin_cred_adj"] = credibility_adjusted_margin(rr.get("signed_margin"), cred)
        out.append(rr)
    return out


# -------------------------
# Counterfactual gate
# -------------------------


def counterfactual_gate(
    eval_res: Dict[str, Any],
    disabled_constraints: Sequence[str],
) -> Dict[str, Any]:
    """Return a copy of eval_res with a *counterfactual* feasibility gate.

    We keep raw constraints, but recompute feasibility/min_margin/active_constraints
    ignoring disabled constraints.
    """
    disabled = {str(x) for x in (disabled_constraints or [])}
    res = dict(eval_res)
    cons = list(res.get("constraints") or [])
    feas = True
    min_sm = None
    active = []
    for r in cons:
        nm = str(r.get("name", ""))
        if nm in disabled:
            continue
        sm = _sf(r.get("signed_margin"))
        if math.isfinite(sm):
            min_sm = sm if (min_sm is None or sm < min_sm) else min_sm
            if sm < 0:
                feas = False
                active.append(nm)
    res["counterfactual"] = {
        "disabled_constraints": sorted(list(disabled)),
        "feasible": bool(feas),
        "min_signed_margin": float(min_sm) if min_sm is not None else float("nan"),
        "active_constraints": active[:8],
    }
    return res


# -------------------------
# Intent trajectories
# -------------------------


def build_intent_trajectory(
    *,
    evaluate_fn: Callable[[Dict[str, Any], str], Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    var_keys: Sequence[str],
    from_intent: str = "Research",
    to_intent: str = "Reactor",
    k_hubs: int = 12,
    k_steps: int = 5,
    seed: int = 0,
) -> Dict[str, Any]:
    """Tier-5: Build a simple Research→Reactor "highway".

    We:
    - Take feasible candidates under from_intent and to_intent.
    - Choose a small set of hub nodes (top score + diversity).
    - Find a shortest path from a from_intent hub to a to_intent hub through hubs.

    This is intentionally lightweight and deterministic.
    """
    rng = np.random.default_rng(int(seed))
    if not candidates:
        return {"ok": False, "reason": "empty_candidates"}

    # Evaluate feasibility under both intents (cached by inputs hash would be ideal, but keep simple)
    rows = []
    for r in candidates:
        inp = dict(r.get("inputs") or r)
        a = evaluate_fn(inp, from_intent)
        b = evaluate_fn(inp, to_intent)
        rows.append({
            "inputs": inp,
            "from": {"feasible": bool(a.get("feasible", False)), "score": float(a.get("_score", -1e30))},
            "to": {"feasible": bool(b.get("feasible", False)), "score": float(b.get("_score", -1e30))},
        })

    A = [x for x in rows if x["from"]["feasible"]]
    B = [x for x in rows if x["to"]["feasible"]]
    if not A or not B:
        return {"ok": False, "reason": "no_feasible_in_one_intent", "n_from": len(A), "n_to": len(B)}

    # Hub selection: take top by score then add a few random for diversity
    A = sorted(A, key=lambda z: z["from"]["score"], reverse=True)
    B = sorted(B, key=lambda z: z["to"]["score"], reverse=True)
    hubs = []
    hubs.extend(A[: max(2, k_hubs // 3)])
    hubs.extend(B[: max(2, k_hubs // 3)])
    pool = rows
    if len(hubs) < k_hubs and pool:
        idx = rng.choice(np.arange(len(pool)), size=min(k_hubs - len(hubs), len(pool)), replace=False)
        hubs.extend([pool[int(i)] for i in idx])

    # Build distance matrix
    X = _finite_rows(np.array([_vec(h["inputs"], var_keys) for h in hubs], dtype=float))
    D = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    # Create directed graph: allow transitions if distance below adaptive threshold
    thresh = float(np.percentile(D, 35)) if D.size else 1.0
    n = len(hubs)
    # Dijkstra
    start = int(np.argmax([h["from"]["score"] if h["from"]["feasible"] else -1e30 for h in hubs]))
    targets = [i for i, h in enumerate(hubs) if h["to"]["feasible"]]
    dist = [float("inf")] * n
    prev = [-1] * n
    dist[start] = 0.0
    visited = [False] * n
    for _ in range(n):
        u = int(np.argmin([dist[i] if not visited[i] else float("inf") for i in range(n)]))
        if not math.isfinite(dist[u]):
            break
        visited[u] = True
        if u in targets:
            break
        for v in range(n):
            if visited[v] or v == u:
                continue
            if D[u, v] <= thresh:
                alt = dist[u] + float(D[u, v])
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u

    # pick best reachable target
    best_t = None
    best = float("inf")
    for t in targets:
        if dist[t] < best:
            best = dist[t]
            best_t = t
    if best_t is None or not math.isfinite(best):
        # fallback: nearest to-intent feasible
        best_t = int(min(targets, key=lambda i: float(D[start, i])))

    # reconstruct path
    path = []
    cur = int(best_t)
    while cur != -1:
        path.append(cur)
        cur = prev[cur]
    path = path[::-1][: int(k_steps)]

    # format path with deltas
    nodes = []
    for i in path:
        h = hubs[i]
        nodes.append({
            "inputs": h["inputs"],
            "from_feasible": h["from"]["feasible"],
            "to_feasible": h["to"]["feasible"],
            "from_score": h["from"]["score"],
            "to_score": h["to"]["score"],
        })
    edges = []
    for a, b in zip(path[:-1], path[1:]):
        edges.append({
            "dist": float(D[a, b]),
            "delta": {k: float(_sf(hubs[b]["inputs"].get(k)) - _sf(hubs[a]["inputs"].get(k))) for k in var_keys},
        })
    return {
        "ok": True,
        "from_intent": str(from_intent),
        "to_intent": str(to_intent),
        "n_candidates": len(candidates),
        "n_hubs": len(hubs),
        "threshold": float(thresh),
        "nodes": nodes,
        "edges": edges,
    }


# -------------------------
# Inverse design & why-not
# -------------------------


def target_objectives_from_spec(targets: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """Create explicit objective rows that minimize absolute error to targets."""
    out = []
    weights = weights or {}
    for k, tv in (targets or {}).items():
        out.append({"key": str(k), "sense": "min", "weight": float(weights.get(k, 1.0)), "target": float(tv), "kind": "abs_error"})
    return out


def inverse_design_residual(outputs: Dict[str, Any], targets: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    weights = weights or {}
    s = 0.0
    for k, tv in (targets or {}).items():
        v = _sf(outputs.get(k))
        if not math.isfinite(v):
            return 1e30
        w = float(weights.get(k, 1.0))
        s += w * abs(v - float(tv))
    return float(s)


def why_not_report(
    *,
    eval_res: Dict[str, Any],
    disabled_constraints: Optional[Sequence[str]] = None,
    cred_map: Optional[Dict[str, ConstraintCred]] = None,
) -> Dict[str, Any]:
    """Tier-5: "Why not" explanation for a (possibly infeasible) design.

    Produces:
    - top violated constraints
    - minimal relaxations needed (margin deficits)
    - counterfactual feasibility if user disables some constraints
    - credibility-adjusted margins if provided
    """
    cons = list(eval_res.get("constraints") or [])
    viol = []
    for r in cons:
        sm = _sf(r.get("signed_margin"))
        if math.isfinite(sm) and sm < 0:
            viol.append({"name": str(r.get("name")), "need_relax": float(-sm), "signed_margin": float(sm)})
    viol = sorted(viol, key=lambda x: x["need_relax"], reverse=True)

    report: Dict[str, Any] = {
        "feasible": bool(eval_res.get("feasible", False)),
        "failure_mode": eval_res.get("failure_mode"),
        "top_violations": viol[:10],
    }

    if disabled_constraints:
        report["counterfactual"] = counterfactual_gate(eval_res, disabled_constraints).get("counterfactual")

    if cred_map:
        adj = apply_credibility_overlay(cons, cred_map)
        # collect worst adjusted
        worst = []
        for r in adj:
            sm = _sf(r.get("signed_margin_cred_adj"))
            if math.isfinite(sm):
                worst.append({"name": str(r.get("name")), "signed_margin_cred_adj": float(sm)})
        worst = sorted(worst, key=lambda x: x["signed_margin_cred_adj"])[:10]
        report["credibility_worst"] = worst

    return report


# -------------------------
# Derived laws / relations
# -------------------------


def discovered_relations(
    *,
    candidates: List[Dict[str, Any]],
    x_keys: Sequence[str],
    y_keys: Sequence[str],
    feasible_only: bool = True,
    top_k: int = 8,
) -> Dict[str, Any]:
    """Tier-6: Mine simple linear relations from the archive.

    Returns correlations and best linear-fit R^2 for (x -> y) pairs.
    This is intentionally conservative and explainable.
    """
    rows = [c for c in (candidates or []) if (not feasible_only or bool(c.get("feasible", False)))]
    if len(rows) < 12:
        return {"ok": False, "reason": "too_few_rows", "n": len(rows)}

    # Build matrices
    X = np.array([[_sf((r.get("inputs") or {}).get(k)) for k in x_keys] for r in rows], dtype=float)
    Y = np.array([[_sf((r.get("outputs") or {}).get(k)) for k in y_keys] for r in rows], dtype=float)
    X = _finite_rows(X)
    Y = _finite_rows(Y)
    # Standardize for correlation
    Xz = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)
    Yz = (Y - Y.mean(axis=0)) / (Y.std(axis=0) + 1e-12)
    corrs = np.clip((Xz.T @ Yz) / float(X.shape[0]), -1.0, 1.0)

    pairs = []
    for i, xk in enumerate(x_keys):
        for j, yk in enumerate(y_keys):
            pairs.append({"x": str(xk), "y": str(yk), "corr": float(corrs[i, j])})
    pairs = sorted(pairs, key=lambda p: abs(p["corr"]), reverse=True)

    # Simple linear regression y ~ a + b x for top correlated pairs (per-y)
    fits = []
    for p in pairs[: max(30, top_k * 3)]:
        xi = x_keys.index(p["x"])  # safe
        yj = y_keys.index(p["y"])
        x = X[:, xi]
        y = Y[:, yj]
        A = np.c_[np.ones_like(x), x]
        try:
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            yhat = A @ coef
            ssr = float(np.sum((y - yhat) ** 2))
            sst = float(np.sum((y - float(np.mean(y))) ** 2)) + 1e-12
            r2 = 1.0 - ssr / sst
        except Exception:
            continue
        fits.append({
            "x": p["x"],
            "y": p["y"],
            "a": float(coef[0]),
            "b": float(coef[1]),
            "r2": float(r2),
            "corr": float(p["corr"]),
        })
    fits = sorted(fits, key=lambda f: f["r2"], reverse=True)[: int(top_k)]

    return {
        "ok": True,
        "n": int(len(rows)),
        "top_corrs": pairs[: int(top_k)],
        "top_linear_fits": fits,
    }


def export_relations_markdown(rel: Dict[str, Any]) -> str:
    if not rel or not rel.get("ok"):
        return "# SHAMS discovered relations\n\n(No relations computed.)\n"
    lines = ["# SHAMS discovered relations", "", f"n={rel.get('n')}", "", "## Top linear fits", ""]
    for f in rel.get("top_linear_fits", []) or []:
        lines.append(f"- **{f['y']}** ≈ {f['a']:.4g} + ({f['b']:.4g})·{f['x']}  (R²={f['r2']:.3f}, corr={f['corr']:.3f})")
    lines.append("")
    lines.append("## Top correlations")
    lines.append("")
    for p in rel.get("top_corrs", []) or []:
        lines.append(f"- corr({p['x']}, {p['y']}) = {p['corr']:.3f}")
    lines.append("")
    return "\n".join(lines)
