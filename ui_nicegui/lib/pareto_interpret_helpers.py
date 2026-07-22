"""Pareto interpretability helpers — interaction matrix, knees, exports, handoffs."""
from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.lib.pareto_helpers import OBJ_CATALOG, artifact_to_json_bytes, build_pareto_artifact


def _rows_to_dicts(rows: list) -> List[dict]:
    return [r for r in rows if isinstance(r, dict)]


def interaction_matrix(feasible: list, obj_keys: List[str]) -> Tuple[List[str], List[Dict[str, str]]]:
    if len(obj_keys) < 2 or len(feasible) < 8:
        return obj_keys, []
    try:
        import numpy as np

        mat = []
        for k in obj_keys:
            mat.append([float(r.get(k)) for r in feasible if r.get(k) is not None])
        if not mat or min(len(x) for x in mat) < 8:
            return obj_keys, []
        arr = np.array(mat, dtype=float)
        corr = np.corrcoef(arr)
        rows: List[Dict[str, str]] = []
        for i, a in enumerate(obj_keys):
            row: Dict[str, str] = {"objective": a}
            for j, b in enumerate(obj_keys):
                v = float(corr[i, j])
                if abs(v) < 0.25:
                    sym = "~"
                elif v > 0:
                    sym = "+"
                else:
                    sym = "-"
                row[b] = sym
            rows.append(row)
        return obj_keys, rows
    except Exception:
        return obj_keys, []


def redundancy_pairs(feasible: list, obj_keys: List[str], *, thr: float = 0.92) -> List[Tuple[str, str, float]]:
    out: List[Tuple[str, str, float]] = []
    if len(obj_keys) < 2 or len(feasible) < 8:
        return out
    try:
        import numpy as np

        mat = []
        for k in obj_keys:
            mat.append([float(r.get(k)) for r in feasible if r.get(k) is not None])
        arr = np.array(mat, dtype=float)
        corr = np.corrcoef(arr)
        for i, a in enumerate(obj_keys):
            for j, b in enumerate(obj_keys):
                if j <= i:
                    continue
                v = float(corr[i, j])
                if abs(v) >= thr:
                    out.append((a, b, v))
    except Exception:
        pass
    return out


def knee_candidates(pareto: list, x_key: str, y_key: str, *, top_k: int = 8) -> List[dict]:
    pts = _rows_to_dicts(pareto)
    if len(pts) < 5:
        return []
    try:
        import numpy as np

        xs = np.array([float(p.get(x_key)) for p in pts], dtype=float)
        ys = np.array([float(p.get(y_key)) for p in pts], dtype=float)
        order = np.argsort(xs)
        xs, ys = xs[order], ys[order]
        pts = [pts[i] for i in order]
        dx = np.diff(xs)
        dy = np.diff(ys)
        kappa = np.abs(np.diff(np.arctan2(dy, dx + 1e-12)))
        scores = list(kappa) + [0.0]
        ranked = sorted(zip(scores, pts), key=lambda t: -t[0])[:top_k]
        return [{**p, "knee_score": float(s)} for s, p in ranked if s == s]
    except Exception:
        return []


def failure_atlas_points(all_samples: list, x_key: str, y_key: str) -> List[dict]:
    """Infeasible shadow for Pareto Explore — geometry/margin axes only (PHYS-KPI-001)."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import allow_infeasible_scatter_point

    if not allow_infeasible_scatter_point(x_key=str(x_key), y_key=str(y_key)):
        return []
    rows = []
    for r in _rows_to_dicts(all_samples):
        if r.get("is_feasible"):
            continue
        if r.get(x_key) is None or r.get(y_key) is None:
            continue
        rows.append(
            {
                x_key: r.get(x_key),
                y_key: r.get(y_key),
                "first_failure": r.get("first_failure") or r.get("dominant_constraint"),
            }
        )
    return rows


def robust_filtered(pareto: list, thr: float) -> List[dict]:
    out = []
    for p in _rows_to_dicts(pareto):
        try:
            m = float(p.get("min_constraint_margin", float("nan")))
            if m == m and m >= float(thr):
                out.append(p)
        except (TypeError, ValueError):
            pass
    return out


def promote_point_inputs(session, row: dict, bounds: dict) -> None:
    """Merge pareto row decision vars into session.inputs from full baseline."""
    from dataclasses import asdict

    base = session.build_point_inputs()
    merged = asdict(base)
    for k, v in row.items():
        if k in merged and v is not None:
            try:
                merged[k] = float(v)
            except (TypeError, ValueError):
                pass
    for k in bounds:
        if k in row and row[k] is not None:
            try:
                merged[k] = float(row[k])
            except (TypeError, ValueError):
                pass
    session.inputs = {k: merged[k] for k in merged}


def systems_mode_handoff(row: dict, bounds: dict) -> dict:
    cand = {}
    for k in list(bounds.keys()) + [
        "R0_m", "Bt_T", "Ip_MA", "fG", "Paux_MW", "kappa", "a_m", "Ti_keV",
    ]:
        if k in row and row[k] is not None:
            try:
                cand[k] = float(row[k])
            except (TypeError, ValueError):
                pass
    return cand


def scan_lab_focus(
    row: dict,
    bounds: dict,
    objectives: dict,
    *,
    plot_x: str = "",
    plot_y: str = "",
) -> dict:
    obj_keys = list(objectives.keys()) if isinstance(objectives, dict) else []
    xk = plot_x or (obj_keys[0] if obj_keys else next(iter(bounds.keys()), "Ip_MA"))
    yk = plot_y or (obj_keys[1] if len(obj_keys) > 1 else (list(bounds.keys())[1] if len(bounds) > 1 else "R0_m"))
    return {
        "x_key": xk,
        "y_key": yk,
        "x": float(row.get(xk)) if row.get(xk) is not None else None,
        "y": float(row.get(yk)) if row.get(yk) is not None else None,
        "objectives": obj_keys,
        "dominant_constraint": row.get("dominant_constraint"),
        "min_constraint_margin": row.get("min_constraint_margin"),
        "source": "Pareto Lab",
    }


def policy_filter_front(
    feasible: list,
    objectives: dict,
    *,
    tbr_min: float | None = None,
    qdiv_max: float | None = None,
    sigma_max: float | None = None,
    hts_min: float | None = None,
) -> List[dict]:
    """Filter feasible set by policy thresholds, then recompute Pareto front."""
    filtered: List[dict] = []
    for p in _rows_to_dicts(feasible):
        if tbr_min is not None:
            tbr = float(p.get("TBR", float("nan")))
            if tbr != tbr or tbr < float(tbr_min):
                continue
        if qdiv_max is not None:
            qd = float(p.get("q_div_MW_m2", float("nan")))
            if qd != qd or qd > float(qdiv_max):
                continue
        if sigma_max is not None:
            sig = float(p.get("sigma_vm_MPa", float("nan")))
            if sig != sig or sig > float(sigma_max):
                continue
        if hts_min is not None:
            hts = float(p.get("hts_margin_cs", p.get("hts_margin", float("nan"))))
            if hts != hts or hts < float(hts_min):
                continue
        filtered.append(p)
    if len(objectives) < 2 or not filtered:
        return filtered
    try:
        from src.solvers.optimize import pareto_front
    except ImportError:
        from solvers.optimize import pareto_front  # type: ignore
    return pareto_front(filtered, objectives)


def explain_segment(
    seg_rows: list,
    *,
    y_key: str,
    bounds_keys: list[str] | None = None,
) -> dict:
    rows = _rows_to_dicts(seg_rows)
    if not rows:
        return {"dominant": "(unknown)", "n": 0, "driver": "", "narrative": "Empty segment."}
    dom = str(rows[0].get("dominant_constraint") or "(unknown)")
    drivers = bounds_keys or ["R0_m", "Bt_T", "Ip_MA", "fG", "Paux_MW"]
    driver_msg = ""
    try:
        import numpy as np

        corrs = []
        for dv in drivers:
            if dv not in rows[0]:
                continue
            a = np.array([float(r.get(dv, float("nan"))) for r in rows], dtype=float)
            b = np.array([float(r.get(y_key, float("nan"))) for r in rows], dtype=float)
            m = np.isfinite(a) & np.isfinite(b)
            if m.sum() < 4:
                continue
            c = float(np.corrcoef(a[m], b[m])[0, 1])
            if c == c:
                corrs.append((dv, c))
        if corrs:
            dv, cc = sorted(corrs, key=lambda kv: -abs(kv[1]))[0]
            driver_msg = f"Within this segment, `{y_key}` co-moves most with `{dv}` (ρ≈{cc:.2f})."
    except Exception:
        pass
    narrative = f"Segment pinned by **{dom}** ({len(rows)} points)."
    if driver_msg:
        narrative += f" {driver_msg}"
    return {"dominant": dom, "n": len(rows), "driver": driver_msg, "narrative": narrative}


def detect_free_lunch_steps(pareto: list, x_key: str, y_key: str, objectives: dict) -> List[dict]:
    """Flag stretches where both plotted objectives improve together (projection artifact)."""
    pts = sorted(_rows_to_dicts(pareto), key=lambda p: float(p.get(x_key) or 0))
    if len(pts) < 4:
        return []
    sx = str(objectives.get(x_key, "min"))
    sy = str(objectives.get(y_key, "min"))
    steps: List[dict] = []
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        try:
            dx = float(b.get(x_key)) - float(a.get(x_key))
            dy = float(b.get(y_key)) - float(a.get(y_key))
        except (TypeError, ValueError):
            continue
        if dx == 0 and dy == 0:
            continue
        x_better = (dx < 0) if sx == "min" else (dx > 0)
        y_better = (dy < 0) if sy == "min" else (dy > 0)
        if x_better and y_better:
            steps.append({"from_idx": i - 1, "to_idx": i, "note": "Both objectives improve along this step — check redundancy or sampling."})
    return steps[:12]


def objective_relevance_table(feasible: list, pareto: list, obj_keys: List[str]) -> List[dict]:
    rows_out: List[dict] = []
    if not obj_keys:
        return rows_out
    try:
        import numpy as np

        for k in obj_keys:
            fvals = [float(r.get(k)) for r in _rows_to_dicts(feasible) if r.get(k) is not None]
            pvals = [float(r.get(k)) for r in _rows_to_dicts(pareto) if r.get(k) is not None]
            vf = float(np.nanstd(np.array(fvals, dtype=float))) if len(fvals) >= 3 else float("nan")
            vp = float(np.nanstd(np.array(pvals, dtype=float))) if len(pvals) >= 2 else float("nan")
            if vp != vp or vf == 0:
                label = "flat on front"
            elif vp / (vf + 1e-12) < 0.05:
                label = "low front variation"
            else:
                label = "shapes front"
            rows_out.append({"objective": k, "std_feasible": vf, "std_front": vp, "relevance": label})
    except Exception:
        pass
    return rows_out


def possible_next_questions(pareto_last: dict) -> List[str]:
    summary = pareto_last.get("summary") or {}
    qs: List[str] = []
    n_pareto = int(summary.get("n_pareto") or 0)
    conf = str(summary.get("confidence") or "")
    if n_pareto < 3:
        qs.append("Increase samples or widen bounds — is the front incomplete?")
    if conf in ("Low", "Sparse"):
        qs.append("Where is sampling coverage thin (confidence halo)?")
    robust = str(summary.get("robust_mix") or "")
    if robust and robust not in ("-", "0/0") and robust.startswith("0/"):
        qs.append("Most Pareto points are fragile under the margin threshold — run Phase+UQ robust screening?")
    top = str(summary.get("top_constraint") or "")
    if "q_div" in top.lower():
        qs.append("Where is heat exhaust (q_div) shaping the trade-off?")
    if str(pareto_last.get("intent_mode", "")).startswith("Both"):
        qs.append("Do Reactor and Research fronts disagree on the same axes?")
    if not qs:
        qs.append("Explore policy lens — how sensitive is the front to TBR / exhaust thresholds?")
    return qs


def restore_pareto_artifact(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Invalid artifact")
    if payload.get("schema") != "shams.pareto.v1" and "pareto" not in payload:
        raise ValueError("Not a Pareto artifact")
    from ui_nicegui.lib.pareto_helpers import summarize_pareto_run

    art = dict(payload)
    if "summary" not in art:
        art["summary"] = summarize_pareto_run(art)
    return art


def publication_pack_bytes(pareto_last: dict, *, narrative: str = "") -> bytes:
    art = build_pareto_artifact(pareto_last)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pareto/shams_pareto_artifact.json", artifact_to_json_bytes(art).decode("utf-8"))
        pareto = pareto_last.get("pareto") or []
        feasible = pareto_last.get("feasible") or []
        if pareto:
            zf.writestr("pareto/pareto_front.csv", _csv_from_rows(pareto))
        if feasible:
            zf.writestr("pareto/feasible_set_sampled.csv", _csv_from_rows(feasible[:5000]))
        zf.writestr(
            "pareto/README.md",
            "\n".join([
                "# SHAMS Pareto Publication Pack",
                "",
                "- JSON artifact (authoritative) + CSV exports",
                "- Feasible-only, non-optimizing, intent-aware",
                "",
                f"- intent_mode: {pareto_last.get('intent_mode')}",
                f"- n_samples: {pareto_last.get('n_samples')}",
                f"- seed: {pareto_last.get('seed')}",
            ]),
        )
        zf.writestr("pareto/narrative_summary.md", narrative or "(no narrative)")
    return buf.getvalue()


def _csv_from_rows(rows: list) -> str:
    import csv

    if not rows:
        return ""
    keys = sorted({k for r in rows if isinstance(r, dict) for k in r.keys()})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        if isinstance(r, dict):
            w.writerow(r)
    return buf.getvalue()


def trade_narrative(pareto_last: dict) -> str:
    summary = pareto_last.get("summary") or {}
    objs = pareto_last.get("objectives") or {}
    lines = [
        "# Pareto trade-off summary",
        "",
        f"- Feasible: {summary.get('n_feasible', '-')} · Pareto: {summary.get('n_pareto', '-')}",
        f"- Top dominant constraint on front: {summary.get('top_constraint', '-')} ",
        f"- Robust mix (margin ≥ thr): {summary.get('robust_mix', '-')}",
        f"- Sampling confidence: {summary.get('confidence', '-')}",
        f"- Objectives: {', '.join(objs.keys()) if isinstance(objs, dict) else objs}",
        "",
        "Conditional on declared bounds, intent, and LHS sample — not a design recommendation.",
    ]
    enriched = pareto_last.get("pareto_enriched")
    if isinstance(enriched, list) and enriched:
        flat = sum(1 for r in enriched if r.get("freedom_left") == "Flat")
        tight = sum(1 for r in enriched if r.get("freedom_left") == "Tight")
        ex = sum(1 for r in enriched if r.get("freedom_left") == "Exhausted")
        lines.append(f"- Freedom-left mix: Flat={flat}, Tight={tight}, Exhausted={ex}")
    return "\n".join(lines)


def objective_sanity_warnings(objectives: dict, intent_mode: str, pareto_last: dict | None = None) -> List[str]:
    warns: List[str] = []
    keys = list(objectives.keys()) if isinstance(objectives, dict) else []
    if any(str(k).upper().startswith("TBR") for k in keys) and str(intent_mode).startswith("Research"):
        warns.append(
            "TBR is typically ignored as blocking in Research intent — using it as an objective may be uninformative."
        )
    if "P_e_net_MW" in keys and str(intent_mode).startswith("Research"):
        warns.append("Net electric power is usually not a Research driver — confirm this objective is meaningful.")
    if len(set(keys)) != len(keys):
        warns.append("Duplicate objective keys detected.")
    if "Q_DT_eqv" in keys:
        bounds = (pareto_last or {}).get("bounds") or {}
        if "Paux_MW" not in bounds:
            warns.append(
                "Q is an objective but Paux is not in sampling bounds — Q trade-offs may be misleading."
            )
    if "Bt_T" in keys and "B_peak_T" in keys:
        warns.append("Both on-axis Bt and peak B are objectives — they are correlated; confirm both are needed.")
    nan_rates = pareto_last.get("_nan_objective_rates") if isinstance(pareto_last, dict) else None
    if isinstance(nan_rates, dict):
        for k, rate in nan_rates.items():
            if rate > 0.5:
                warns.append(f"Objective {k} is NaN in >50% of feasible rows — check evaluator outputs.")
    return warns


def explain_why_not(pareto_last: dict) -> dict:
    feasible = pareto_last.get("feasible") or []
    pareto = pareto_last.get("pareto") or []
    samples = pareto_last.get("all") or []
    out: dict = {"messages": [], "failure_counts": []}
    if not feasible:
        out["messages"].append(
            "No feasible designs in sampled bounds for selected intent(s) — not a plotting issue."
        )
    elif not pareto:
        out["messages"].append(
            "Feasible designs exist but no non-dominated Pareto set (objective redundancy or low variation)."
        )
    counts: dict[str, int] = {}
    for row in samples:
        if row.get("is_feasible"):
            continue
        ff = str(row.get("first_failure") or row.get("dominant_constraint") or "(unknown)")
        counts[ff] = counts.get(ff, 0) + 1
    out["failure_counts"] = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    return out


def sampling_honesty(pareto_last: dict) -> dict:
    samples = pareto_last.get("all") or []
    feasible = pareto_last.get("feasible") or []
    objectives = pareto_last.get("objectives") or {}
    obj_keys = list(objectives.keys()) if isinstance(objectives, dict) else []
    n_all = len(samples)
    n_feas = len(feasible)
    rep: dict = {
        "n_samples_total": n_all,
        "n_feasible": n_feas,
        "feasible_fraction": float(n_feas) / max(n_all, 1),
        "seed": pareto_last.get("seed"),
        "intent_mode": pareto_last.get("intent_mode"),
        "incompleteness_flags": [],
    }
    ff = rep["feasible_fraction"]
    n_pareto = len(pareto_last.get("pareto") or [])
    if ff < 0.001:
        rep["incompleteness_flags"].append("Feasible sample is extremely sparse — front may be empty or misleading.")
    elif ff < 0.01 and n_pareto < 5:
        rep["incompleteness_flags"].append("Low feasible fraction with thin Pareto set — increase samples.")
    if n_pareto >= 1 and n_pareto < 5:
        rep["incompleteness_flags"].append("Few Pareto points — trade-off geometry may be under-resolved.")
    if len(obj_keys) >= 2 and n_feas >= 10:
        try:
            import numpy as np

            mat = []
            for k in obj_keys[:2]:
                mat.append([float(r.get(k)) for r in feasible if r.get(k) is not None])
            if mat and len(mat[0]) >= 10:
                X = np.array(mat, dtype=float).T
                k = min(10, len(X) - 1)
                d2 = ((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2)
                np.fill_diagonal(d2, np.inf)
                knn = np.sort(d2, axis=1)[:, :k]
                rho = np.sqrt(np.mean(knn, axis=1))
                rep["median_local_spacing"] = float(np.median(rho))
                rep["p95_spacing"] = float(np.percentile(rho, 95))
        except Exception:
            pass
    return rep


def enrich_pareto_front(
    pareto: list,
    feasible: list,
    *,
    x_key: str,
    y_key: str,
    robust_margin_thr: float = 0.10,
) -> list[dict]:
    """Pareto v2 annotations: freedom_left, confidence, segment_id, geography."""
    pts = [dict(p) for p in _rows_to_dicts(pareto)]
    if not pts:
        return []
    try:
        import numpy as np

        order = sorted(range(len(pts)), key=lambda i: float(pts[i].get(x_key) or 0))
        sorted_pts = [pts[i] for i in order]
        xs = np.array([float(p.get(x_key, 0)) for p in sorted_pts], dtype=float)
        ys = np.array([float(p.get(y_key, 0)) for p in sorted_pts], dtype=float)
        dy = np.gradient(ys)
        dx = np.gradient(xs)
        slope = np.abs(dy / (dx + 1e-12))
        freedom = []
        for s in slope:
            if not np.isfinite(s):
                freedom.append("Tight")
            elif s < 0.15:
                freedom.append("Flat")
            elif s < 0.6:
                freedom.append("Tight")
            else:
                freedom.append("Exhausted")
        for i, orig_i in enumerate(order):
            pts[orig_i]["freedom_left"] = freedom[i]

        if len(feasible) >= 10:
            Fx = np.array([float(r.get(x_key, np.nan)) for r in feasible], dtype=float)
            Fy = np.array([float(r.get(y_key, np.nan)) for r in feasible], dtype=float)
            mF = np.isfinite(Fx) & np.isfinite(Fy)
            Fx, Fy = Fx[mF], Fy[mF]
            k = int(max(5, min(25, len(Fx) // 30)))
            conf_vals = []
            for p in pts:
                px, py = float(p.get(x_key, np.nan)), float(p.get(y_key, np.nan))
                if not (np.isfinite(px) and np.isfinite(py)) or len(Fx) == 0:
                    conf_vals.append(float("nan"))
                    continue
                d2 = (Fx - px) ** 2 + (Fy - py) ** 2
                kk = min(k, len(d2))
                idx = np.argpartition(d2, kk - 1)[:kk]
                conf_vals.append(float(np.mean(np.sqrt(d2[idx]) + 1e-12)))
            arr = np.asarray(conf_vals, dtype=float)
            if np.any(np.isfinite(arr)):
                lo, hi = np.nanmin(arr), np.nanmax(arr)
                for p, md in zip(pts, conf_vals):
                    p["confidence"] = float((hi - md) / (hi - lo + 1e-12)) if md == md else float("nan")

        seg = 0
        prev_dom = None
        for p in pts:
            dom = str(p.get("dominant_constraint") or "(none)")
            if prev_dom is not None and dom != prev_dom:
                seg += 1
            p["segment_id"] = seg
            prev_dom = dom

        for i, p in enumerate(pts):
            dom = str(p.get("dominant_constraint") or "(none)")
            cliff = i > 0 and dom != str(pts[i - 1].get("dominant_constraint") or "(none)")
            if cliff:
                p["geography"] = "Cliff"
            else:
                mm = float(p.get("min_constraint_margin", float("nan")))
                fl = str(p.get("freedom_left", "-"))
                if mm == mm and mm < max(0.05, robust_margin_thr * 0.5):
                    p["geography"] = "Ridge"
                elif fl == "Flat" and (mm != mm or mm >= robust_margin_thr):
                    p["geography"] = "Plain"
                else:
                    p["geography"] = "Slope"
    except Exception:
        for p in pts:
            p.setdefault("freedom_left", "-")
            p.setdefault("geography", "-")
            p.setdefault("segment_id", 0)
    return pts


def governance_doc_paths() -> dict[str, str]:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "docs"
    names = {
        "PARETO_MODE_CONSTITUTION.md": "Constitution",
        "PARETO_V1_FREEZE_DECLARATION.md": "Freeze declaration",
        "PARETO_POST_FREEZE_CONTRIBUTION_RULES.md": "Contribution rules",
        "PARETO_TEACHING_FREEZE_POLICY.md": "Teaching policy",
    }
    out: dict[str, str] = {}
    for fn, _ in names.items():
        p = root / fn
        if p.is_file():
            out[fn] = p.read_text(encoding="utf-8")
    return out


def v351_empty_region_report(
    records: list,
    *,
    x_key: str,
    y_key: str,
    x_bins: int = 12,
    y_bins: int = 12,
    lane_rows: list | None = None,
) -> dict:
    try:
        from src.atlas.frontier_atlas_v351 import bin_counts
    except ImportError:
        from atlas.frontier_atlas_v351 import bin_counts  # type: ignore

    feas = [r for r in records if r.get("is_feasible")]
    map_feas = bin_counts(feas, x_key, y_key, x_bins=x_bins, y_bins=y_bins)
    map_rob = map_mir = None
    if lane_rows:
        map_rob = bin_counts(
            lane_rows, x_key, y_key, x_bins=x_bins, y_bins=y_bins,
            predicate=lambda r: bool(r.get("is_robust", False)),
        )
        map_mir = bin_counts(
            lane_rows, x_key, y_key, x_bins=x_bins, y_bins=y_bins,
            predicate=lambda r: bool(r.get("is_mirage", False)),
        )
    return {
        "feasible": {"total_points": map_feas.get("total_points"), "empty_cells": map_feas.get("empty_cells")},
        "robust": None if map_rob is None else {"total_points": map_rob.get("total_points"), "empty_cells": map_rob.get("empty_cells")},
        "mirage": None if map_mir is None else {"total_points": map_mir.get("total_points"), "empty_cells": map_mir.get("empty_cells")},
        "axes": {"x": x_key, "y": y_key, "bins": {"x": x_bins, "y": y_bins}},
    }

