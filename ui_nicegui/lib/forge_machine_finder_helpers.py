"""Reactor Design Forge — Machine Finder + capsule helpers."""
from __future__ import annotations

import json
import math
import tempfile
import time
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ui_nicegui.evaluate import ui_evaluate

FORGE_INTENT_LABELS = [
    "Power Reactor (net-electric)",
    "Experimental Device (research)",
]
FORGE_DEFAULT_VAR_KEYS = ["R0_m", "Bt_T", "Ip_MA", "Paux_MW"]
FORGE_BOUND_FRACS = {
    "Tight (±10%)": 0.10,
    "Medium (±20%)": 0.20,
    "Wide (±35%)": 0.35,
}


def _records_as_dicts(records) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in records or []:
        if isinstance(r, dict):
            out.append(dict(r))
            continue
        try:
            out.append(asdict(r))
        except Exception:
            out.append(
                {
                    "name": getattr(r, "name", ""),
                    "value": getattr(r, "value", float("nan")),
                    "lo": getattr(r, "lo", None),
                    "hi": getattr(r, "hi", None),
                    "ok": getattr(r, "ok", False),
                    "residual": getattr(r, "residual", float("nan")),
                    "signed_margin": getattr(r, "signed_margin", float("nan")),
                }
            )
    return out


def intent_from_label(label: str) -> str:
    return "Reactor" if str(label).lower().startswith("power") else "Research"


def anchor_from_session(base) -> Dict[str, float]:
    try:
        d = asdict(base)
    except Exception:
        d = dict(getattr(base, "__dict__", {}) or {})
    out: Dict[str, float] = {}
    for k, v in d.items():
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            out[k] = float(v)
    return out


def all_var_key_options(anchor: Dict[str, float]) -> List[str]:
    keys = list(anchor.keys())
    for k in ["R0_m", "a_m", "kappa", "delta", "Bt_T", "Ip_MA", "Paux_MW", "nbar_1e20_m3", "Ti_keV"]:
        if k not in keys:
            keys.append(k)
    return keys


def compute_bounds(
    anchor: Dict[str, float],
    var_keys: List[str],
    *,
    bound_mode: str = "Medium (±20%)",
    custom_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Dict[str, Tuple[float, float]]:
    frac = FORGE_BOUND_FRACS.get(bound_mode, 0.20)
    bounds: Dict[str, Tuple[float, float]] = {}
    for k in var_keys:
        if custom_bounds and k in custom_bounds:
            lo, hi = custom_bounds[k]
            bounds[k] = (float(lo), float(hi))
            continue
        v0 = float(anchor.get(k, 0.0))
        if bound_mode == "Custom" and custom_bounds and k not in custom_bounds:
            lo, hi = v0 * 0.8, v0 * 1.2
        else:
            lo, hi = v0 * (1 - frac), v0 * (1 + frac)
        if hi < lo:
            hi = lo
        bounds[k] = (float(lo), float(hi))
    return bounds


def load_objective_packs(intent: str):
    try:
        from tools.sandbox.optimizer_engines import default_objective_packs
    except ImportError:
        from tools.sandbox.optimizer_engines import default_objective_packs  # type: ignore
    return default_objective_packs(intent)


def objectives_for_pack(intent: str, pack_name: str):
    try:
        from tools.sandbox.hybrid_engine import Objective
    except ImportError:
        from tools.sandbox.hybrid_engine import Objective  # type: ignore

    if pack_name == "Custom (manual objectives)":
        return [
            Objective(key="P_e_net_MW", sense="max", weight=1.0),
            Objective(key="Q_DT_eqv", sense="max", weight=0.5),
        ]
    packs = load_objective_packs(intent)
    for p in packs:
        if p.name == pack_name:
            return [Objective(**o.__dict__) for o in p.objectives]
    packs = load_objective_packs(intent)
    return [Objective(**o.__dict__) for o in packs[0].objectives]


def lens_contract(intent: str, pack_name: str, objectives) -> dict:
    packs = load_objective_packs(intent)
    desc = "Custom objectives (manual)"
    if pack_name != "Custom (manual objectives)":
        for p in packs:
            if p.name == pack_name:
                desc = str(p.description)
                break
    return {
        "name": str(pack_name),
        "description": desc,
        "intent": str(intent),
        "objectives": [{"key": o.key, "sense": o.sense, "weight": float(o.weight)} for o in objectives],
    }


def evaluate_forge_candidate(inp: dict, intent: str, *, origin: str = "NiceGUI:Forge audit") -> dict:
    try:
        from src.models.inputs import PointInputs
        from src.constraints.system import build_constraints_from_outputs
        from tools.process_compat.process_compat import (
            constraints_to_records,
            active_constraints,
            feasibility_flag,
            failure_mode,
        )
        from src.economics.cost import cost_proxies
    except ImportError:
        from models.inputs import PointInputs  # type: ignore
        from constraints.system import build_constraints_from_outputs  # type: ignore
        from tools.process_compat.process_compat import (  # type: ignore
            constraints_to_records,
            active_constraints,
            feasibility_flag,
            failure_mode,
        )
        from economics.cost import cost_proxies  # type: ignore

    pi = PointInputs(**dict(inp))
    outputs = ui_evaluate(pi, origin=origin)
    cons = build_constraints_from_outputs(outputs, design_intent=intent)
    records = constraints_to_records(cons)
    record_dicts = _records_as_dicts(records)
    feas = feasibility_flag(records, design_intent=intent)
    fm = failure_mode(records, design_intent=intent)
    try:
        from solvers.pareto_feasibility import annotate_pareto_feasibility
    except ImportError:
        from src.solvers.pareto_feasibility import annotate_pareto_feasibility
    ann = annotate_pareto_feasibility(outputs, intent)
    min_sm = None
    for r in records:
        try:
            sm = float(getattr(r, "signed_margin", float("nan")))
        except (TypeError, ValueError):
            continue
        if min_sm is None or sm < min_sm:
            min_sm = sm
    cost = cost_proxies(outputs) if isinstance(outputs, dict) else {}
    res = {
        "inputs": dict(inp),
        "outputs": dict(outputs),
        "constraints": record_dicts,
        "feasible": bool(feas),
        "governance_feasible": bool(ann.get("governance_feasible", feas)),
        "intent_feasible": bool(ann.get("is_feasible", feas)),
        "blocking_failures": list(ann.get("blocking_failures") or []),
        "active_constraints": active_constraints(records, design_intent=intent),
        "failure_mode": fm,
        "min_signed_margin": float(min_sm) if min_sm is not None else float("nan"),
        "cost": cost,
    }
    if isinstance(res.get("outputs"), dict) and isinstance(cost, dict):
        for ck, cv in cost.items():
            if ck not in res["outputs"]:
                res["outputs"][ck] = cv
    try:
        from tools.sandbox.hybrid_engine import scalar_score, violation_distance

        res["_score"] = scalar_score(res.get("outputs") or {}, [])
        res["_violation"] = violation_distance(res.get("constraints") or [])
    except Exception:
        pass
    return res


def make_evaluate_fn(
    intent: str,
    objectives,
    *,
    min_margin: float = 0.0,
    track_other_intent: bool = False,
) -> Callable[[dict], dict]:
    other_intent = "Research" if str(intent) == "Reactor" else "Reactor"

    def _fn(cand_inputs: dict) -> dict:
        res = evaluate_forge_candidate(cand_inputs, intent)
        try:
            from tools.sandbox.hybrid_engine import scalar_score, violation_distance

            res["_score"] = scalar_score(res.get("outputs") or {}, objectives)
            res["_violation"] = violation_distance(res.get("constraints") or [])
        except Exception:
            pass
        if min_margin and float(min_margin) > 0:
            try:
                if float(res.get("min_signed_margin", float("nan"))) < float(min_margin):
                    res["feasible"] = False
                    res["failure_mode"] = res.get("failure_mode") or "min_margin_guardrail"
            except (TypeError, ValueError):
                pass
        if track_other_intent:
            try:
                oth = evaluate_forge_candidate(
                    cand_inputs,
                    other_intent,
                    origin="NiceGUI:Forge other-intent",
                )
                res["other_intent"] = other_intent
                res["other_feasible"] = bool(oth.get("feasible"))
                res["other_failure_mode"] = oth.get("failure_mode")
                res["other_governance_feasible"] = oth.get("governance_feasible")
            except Exception:
                pass
        return res

    return _fn


def run_machine_finder(
    *,
    intent: str,
    anchor: Dict[str, float],
    var_keys: List[str],
    bounds: Dict[str, Tuple[float, float]],
    objectives,
    pop_size: int = 64,
    generations: int = 40,
    surrogate_rounds: int = 6,
    local_steps: int = 70,
    archive_topk: int = 60,
    require_feasible_only: bool = True,
    seed: int = 1,
    enable_surface_surf: bool = True,
    enable_skeleton: bool = True,
    min_margin: float = 0.0,
    surf_steps: int = 80,
    use_knowledge_store: bool = False,
    track_other_intent: bool = False,
) -> dict:
    try:
        from tools.sandbox.hybrid_engine import VarSpec, run_hybrid_machine_finder, build_archive
        from tools.sandbox.feasibility_ladder import classify_candidate
        from tools.sandbox.resistance_report import build_resistance_report
    except ImportError as exc:
        raise RuntimeError("Machine Finder engine unavailable") from exc

    var_specs = [VarSpec(key=k, lo=float(bounds[k][0]), hi=float(bounds[k][1])) for k in var_keys]
    eval_fn = make_evaluate_fn(
        intent,
        objectives,
        min_margin=float(min_margin),
        track_other_intent=bool(track_other_intent),
    )
    budgets = {
        "pop_size": int(pop_size),
        "generations": int(generations),
        "surrogate_rounds": int(surrogate_rounds),
        "propose_per_round": 36,
        "local_steps": int(local_steps),
        "archive_topk": int(archive_topk),
        "resistance_window": 250,
        "enable_surface_surf": bool(enable_surface_surf),
        "enable_skeleton": bool(enable_skeleton),
        "use_knowledge_store": bool(use_knowledge_store),
        "surf_steps": int(surf_steps),
    }
    run = run_hybrid_machine_finder(
        evaluate_fn=eval_fn,
        intent=intent,
        anchor_inputs=dict(anchor),
        var_specs=var_specs,
        objectives=objectives,
        budgets=budgets,
        seed=int(seed),
    )
    if require_feasible_only:
        run["archive"] = [a for a in run.get("archive", []) if a.get("feasible", False)]
    try:
        run["archive"] = build_archive(
            run.get("archive", []) or [],
            var_specs,
            topk=int(archive_topk),
            objectives=objectives,
        )
    except Exception:
        pass
    try:
        for c in run.get("archive") or []:
            c.update(classify_candidate(c, dominant=bool(c.get("is_dominant", False))))
        for t in run.get("trace") or []:
            t.update(classify_candidate(t))
    except Exception:
        pass
    try:
        bounds_dict = {k: list(bounds[k]) for k in var_keys if k in bounds}
        run["resistance_report"] = build_resistance_report(
            trace=run.get("trace") or [],
            archive=run.get("archive") or [],
            intent=intent,
            lens_contract={},
            bounds=bounds_dict,
            var_specs=[v.__dict__ for v in var_specs],
        )
    except Exception:
        pass
    run["kind"] = run.get("kind") or "optimization_sandbox_hybrid_run"
    return run


def summarize_workbench_run(run: Optional[dict]) -> Dict[str, Any]:
    if not isinstance(run, dict) or run.get("archive") is None:
        return {"loaded": False}
    archive = run.get("archive") or []
    trace = run.get("trace") or []
    n_af = sum(1 for a in archive if bool(a.get("feasible", False)))
    n_dom = sum(1 for a in archive if bool(a.get("is_dominant", False)))
    resist = run.get("resistance") or {}
    feas_rate = resist.get("feasible_rate")
    dom = resist.get("dominant_constraints") or {}
    dom_top = sorted(dom.items(), key=lambda kv: kv[1], reverse=True)[:1]
    dom_txt = dom_top[0][0] if dom_top else "-"
    rr = run.get("resistance_report")
    top_blocker = "-"
    if isinstance(rr, dict):
        topb = rr.get("primary_blockers") or rr.get("blockers") or []
        if topb:
            b0 = topb[0]
            top_blocker = b0.get("name", b0) if isinstance(b0, dict) else str(b0)
    return {
        "loaded": True,
        "intent": str(run.get("intent") or "-"),
        "n_archive": len(archive),
        "n_feasible_archive": n_af,
        "n_dominant": n_dom,
        "n_trace": len(trace),
        "n_feasible_trace": sum(1 for t in trace if bool(t.get("feasible", False))),
        "feasible_rate_recent": feas_rate,
        "dominant_resistance": dom_txt,
        "top_blocker": top_blocker,
        "best_score": (run.get("best_feasible") or {}).get("_score"),
    }


def archive_table_rows(run: dict, *, limit: int = 40) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, a in enumerate(run.get("archive") or []):
        if i >= limit:
            break
        if not isinstance(a, dict):
            continue
        inp = a.get("inputs") or {}
        rows.append(
            {
                "idx": i,
                "feasible": bool(a.get("feasible", False)),
                "score": a.get("_score"),
                "failure_mode": a.get("failure_mode") or "-",
                "min_margin": a.get("min_signed_margin"),
                "R0_m": inp.get("R0_m"),
                "Bt_T": inp.get("Bt_T"),
                "Ip_MA": inp.get("Ip_MA"),
                "Paux_MW": inp.get("Paux_MW"),
                "dominant": bool(a.get("is_dominant", False)),
            }
        )
    return rows


def resistance_atlas_rows(run: dict) -> List[Dict[str, Any]]:
    resist = run.get("resistance") or {}
    dom = resist.get("dominant_constraints") or {}
    if not isinstance(dom, dict):
        return []
    total = sum(float(v) for v in dom.values() if isinstance(v, (int, float)))
    rows = []
    for name, count in sorted(dom.items(), key=lambda kv: float(kv[1]), reverse=True)[:15]:
        frac = float(count) / total if total > 0 else 0.0
        rows.append({"constraint": str(name), "count": count, "fraction": f"{frac * 100:.1f}%"})
    return rows


def promote_archive_row(session_inputs: dict, run: dict, row_idx: int) -> dict:
    archive = run.get("archive") or []
    if row_idx < 0 or row_idx >= len(archive):
        raise IndexError("Invalid archive row")
    cand = dict((archive[row_idx].get("inputs") or {}))
    merged = dict(session_inputs)
    valid = set(session_inputs.keys())
    for k, v in cand.items():
        if k in valid:
            try:
                merged[k] = float(v)
            except (TypeError, ValueError):
                pass
    return merged


def build_capsule_zip_bytes(run: dict, *, lens_contract: dict, bounds: dict, settings_extra: Optional[dict] = None) -> Tuple[bytes, str]:
    try:
        from tools.sandbox.persistence import save_run_capsule_v2
        from tools.sandbox.export_capsule import export_run_capsule_zip
    except ImportError as exc:
        raise RuntimeError("Capsule export unavailable") from exc

    run_id = f"run_{int(time.time())}"
    settings = {
        "bounds": {k: list(v) if isinstance(v, tuple) else v for k, v in bounds.items()},
        "var_specs": run.get("var_specs") or [],
        "objectives": run.get("objectives") or [],
    }
    if settings_extra:
        settings.update(settings_extra)
    rr = run.get("resistance_report")
    with tempfile.TemporaryDirectory() as tmp:
        cap_path = save_run_capsule_v2(
            run,
            run_id=run_id,
            settings=settings,
            evaluator_hash=str(run.get("fingerprint") or ""),
            archive=run.get("archive") or [],
            trace=run.get("trace") or [],
            lens_contract=lens_contract,
            resistance_report=rr if isinstance(rr, dict) else None,
            root=Path(tmp),
        )
        out_zip = Path(cap_path).with_suffix(".zip")
        capsule = json.loads(Path(cap_path).read_text(encoding="utf-8"))
        export_run_capsule_zip(
            capsule=capsule,
            archive={"schema": "shams.opt_sandbox.archive_snapshot.v1", "archive": run.get("archive") or []},
            resistance_report=rr if isinstance(rr, dict) else None,
            out_path=out_zip,
        )
        raw = out_zip.read_bytes()
        try:
            from ui_nicegui.lib.external_optimizer_helpers import watermark_extopt_zip_bytes

            return watermark_extopt_zip_bytes(raw), out_zip.name
        except Exception:
            return raw, out_zip.name


def restore_workbench_from_capsule(capsule: dict) -> dict:
    if str(capsule.get("schema")) != "shams.opt_sandbox.run_capsule.v2":
        raise ValueError(f"Unsupported capsule schema: {capsule.get('schema')}")
    return {
        "kind": "optimization_sandbox_hybrid_run_replay",
        "intent": capsule.get("intent"),
        "seed": capsule.get("seed", 1),
        "objectives": (capsule.get("lens") or {}).get("objectives", capsule.get("objectives", [])),
        "var_specs": capsule.get("var_specs", []),
        "budgets": {"bounds": capsule.get("bounds", {})},
        "archive": capsule.get("archive", []),
        "trace": capsule.get("trace", []),
        "telemetry": capsule.get("telemetry", {}),
        "resistance_report": capsule.get("resistance_report"),
        "capsule_v2": capsule,
        "non_authoritative_notice": "Replayed from capsule. Truth remains the frozen evaluator.",
    }


def parse_capsule_upload(content: bytes, filename: str) -> dict:
    name = (filename or "").lower()
    if name.endswith(".zip"):
        try:
            from tools.sandbox.export_capsule import import_run_capsule_zip
        except ImportError as exc:
            raise RuntimeError("Capsule import unavailable") from exc
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            data = import_run_capsule_zip(tmp_path)
            capsule = data.get("capsule") or {}
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        capsule = json.loads(content.decode("utf-8"))
    if not isinstance(capsule, dict):
        raise ValueError("Invalid capsule payload")
    return capsule


def diff_capsule_json(a: dict, b: dict) -> dict:
    try:
        from tools.sandbox.persistence import diff_capsules
    except ImportError as exc:
        raise RuntimeError("Capsule diff unavailable") from exc
    return diff_capsules(a, b)


def build_forge_audit_pack_zip(
    run: dict,
    *,
    row_idx: int,
    lens_contract: dict,
    bounds: dict,
    intent: str = "Reactor",
) -> Tuple[bytes, str]:
    """Bundle narrative, reviewer packet, and run capsule for reviewer-room export."""
    import io
    import zipfile

    from tools.sandbox.report_pack import build_report_pack
    from tools.sandbox.reviewer_packet_builder import ReviewerPacketOptions, build_reviewer_packet_zip

    from ui_nicegui.lib.forge_interpret_helpers import design_card_markdown

    archive = run.get("archive") or []
    if row_idx < 0 or row_idx >= len(archive):
        raise IndexError("Invalid archive row for audit pack")
    cand = archive[row_idx]
    if not isinstance(cand, dict):
        raise ValueError("Invalid archive candidate")

    run_capsule = run.get("capsule_v2")
    if not isinstance(run_capsule, dict):
        run_capsule = {
            "schema": "shams.opt_sandbox.run_capsule.v2",
            "intent": run.get("intent"),
            "seed": run.get("seed"),
            "archive": archive,
            "trace": run.get("trace") or [],
            "lens": lens_contract,
            "bounds": bounds,
            "resistance_report": run.get("resistance_report"),
        }

    reviewer_bytes, reviewer_summary = build_reviewer_packet_zip(
        candidate=cand,
        run_capsule=run_capsule,
        options=ReviewerPacketOptions(),
    )
    capsule_bytes, capsule_name = build_capsule_zip_bytes(
        run,
        lens_contract=lens_contract,
        bounds=bounds,
    )
    rp = build_report_pack(candidate=cand)
    narrative_md = str(rp.get("markdown") or "")
    design_md = design_card_markdown(cand, intent)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("narrative/report_pack.md", narrative_md.encode("utf-8"))
        if design_md:
            zf.writestr("narrative/design_card.md", design_md.encode("utf-8"))
        zf.writestr("reviewer_packet/shams_reviewer_packet.zip", reviewer_bytes)
        zf.writestr(
            "reviewer_packet/summary.json",
            json.dumps(reviewer_summary, indent=2, sort_keys=True, default=str).encode("utf-8"),
        )
        zf.writestr(f"run_capsule/{capsule_name}", capsule_bytes)
        manifest = {
            "schema": "shams.forge.audit_pack.v1",
            "intent": str(intent),
            "row_idx": int(row_idx),
            "n_archive": len(archive),
            "capsule_file": capsule_name,
            "reviewer_packet_schema": reviewer_summary.get("schema"),
        }
        zf.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        )
        zf.writestr(
            "README.txt",
            (
                "SHAMS Reactor Design Forge — Audit Pack\n"
                "Contains narrative (report + design card), reviewer packet ZIP, and run capsule ZIP.\n"
                "Descriptive only — re-audit promoted candidates in Point Designer.\n"
            ).encode("utf-8"),
        )

    name = f"shams_forge_audit_pack_row{int(row_idx)}.zip"
    return buf.getvalue(), name
