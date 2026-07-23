"""External optimizer / advanced trade study helpers — Phase 17."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.evaluate import ui_evaluate


def repo() -> Path:
    return Path(repo_root())


def load_phase_defaults() -> str:
    try:
        txt = (repo() / "ui" / "phase_envelopes.py").read_text(encoding="utf-8")
        import re

        m = re.search(r"^_DEFAULT_PHASES_JSON\s*=\s*(?P<q>'''|\"\"\"|'|\")(?P<body>.*?)(?P=q)", txt, re.M | re.S)
        if m:
            return m.group("body")
    except Exception:
        pass
    return json.dumps(
        [
            {"name": "Ramp", "input_overrides": {"Paux_MW": 0.0}, "notes": "cold start"},
            {"name": "Flat-top", "input_overrides": {}, "notes": "baseline"},
        ],
        indent=2,
    )


def load_uq_defaults() -> str:
    try:
        txt = (repo() / "ui" / "uncertainty_contracts.py").read_text(encoding="utf-8")
        import re

        m = re.search(r"^_DEFAULT_UQ_JSON\s*=\s*(?P<q>'''|\"\"\"|'|\")(?P<body>.*?)(?P=q)", txt, re.M | re.S)
        if m:
            return m.group("body")
    except Exception:
        pass
    return json.dumps(
        {
            "name": "Default (fallback)",
            "intervals": {"fG": {"lo": 0.75, "hi": 0.85}, "Paux_MW": {"lo": 0.0, "hi": 30.0}},
            "policy_overrides": {},
        },
        indent=2,
    )


def parse_phases(phases_json: str):
    from src.phase_envelopes import PhaseSpec

    raw = json.loads(phases_json)
    if not isinstance(raw, list) or not raw:
        raise ValueError("Phases JSON must be a non-empty list")
    phases = []
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError("Each phase must be an object with at least a 'name'")
        phases.append(
            PhaseSpec(
                name=str(item["name"]),
                input_overrides=dict(item.get("input_overrides") or {}),
                policy_overrides=dict(item.get("policy_overrides") or {})
                if item.get("policy_overrides") is not None
                else None,
                notes=str(item.get("notes", "")),
            )
        )
    return phases


def parse_uq(uq_json: str):
    from src.uq_contracts import UncertaintyContractSpec, Interval

    raw = json.loads(uq_json)
    if not isinstance(raw, dict):
        raise ValueError("UQ JSON must be an object")
    intervals_raw = raw.get("intervals")
    if not isinstance(intervals_raw, dict) or not intervals_raw:
        raise ValueError("UQ JSON must include non-empty 'intervals' dict")
    intervals = {}
    for k, v in intervals_raw.items():
        if not isinstance(v, dict) or "lo" not in v or "hi" not in v:
            raise ValueError(f"Interval for '{k}' must be an object with lo/hi")
        intervals[str(k)] = Interval(lo=float(v["lo"]), hi=float(v["hi"]))
    pol = raw.get("policy_overrides")
    return UncertaintyContractSpec(
        name=str(raw.get("name", "UQ")),
        intervals=intervals,
        policy_overrides=dict(pol or {}) if pol is not None else None,
    )


def _classify_robust(nominal_feasible: bool, env_verdict: str, uq_verdict: str) -> str:
    if not nominal_feasible:
        return "FAIL"
    if str(env_verdict) == "PASS" and str(uq_verdict) == "ROBUST_PASS":
        return "ROBUST"
    if str(env_verdict) == "PASS" and str(uq_verdict) == "FRAGILE":
        return "FRAGILE"
    return "MIRAGE"


def candidate_sources(session) -> List[Tuple[str, dict]]:
    out: List[Tuple[str, dict]] = []
    pl = getattr(session, "pareto_last", None)
    if isinstance(pl, dict) and isinstance(pl.get("pareto"), list) and pl.get("pareto"):
        out.append(("Pareto Lab — last internal Pareto run", pl))
    cap = getattr(session, "active_study_capsule", None)
    if isinstance(cap, dict) and isinstance(cap.get("pareto"), list) and cap.get("pareto"):
        normalized = {
            "pareto": list(cap.get("pareto") or []),
            "bounds": (cap.get("knob_set") or {}).get("bounds"),
            "objectives": {
                k: {"sense": (cap.get("objective_senses") or {}).get(k, "min")}
                for k in (cap.get("objectives") or [])
            },
        }
        out.append(("Trade Study Studio — active study capsule", normalized))
    return out


def _robust_objective_agg(orientation: str, vals: List[float]) -> float:
    v = [float(x) for x in vals if x is not None and float(x) == float(x)]
    if not v:
        return float("nan")
    if str(orientation).lower().startswith("max"):
        return float(min(v))
    return float(max(v))


def run_robust_pareto_frontier(
    session,
    *,
    bundle: dict,
    phases_json: str,
    uq_json: str,
    n_take: int,
    label_prefix: str = "robust",
) -> dict:
    from src.phase_envelopes import run_phase_envelope_for_point
    from src.uq_contracts import run_uncertainty_contract_for_point

    phases = parse_phases(phases_json)
    uq_spec = parse_uq(uq_json)
    base = session.build_point_inputs()
    base_d = asdict(base) if hasattr(base, "__dataclass_fields__") else dict(base)
    pareto_pts = list(bundle.get("pareto") or [])[: int(n_take)]
    bounds = bundle.get("bounds") or {}
    bound_keys = list(bounds.keys()) if isinstance(bounds, dict) else []
    objectives = bundle.get("objectives") or {}
    if isinstance(objectives, dict) and objectives and "sense" in str(next(iter(objectives.values()), "")):
        obj_senses = {k: (v.get("sense") if isinstance(v, dict) else str(v)) for k, v in objectives.items()}
    else:
        obj_senses = {k: str(v) for k, v in objectives.items()} if isinstance(objectives, dict) else {}
    rows: List[dict] = []
    point_arts: List[dict] = []

    for i, row in enumerate(pareto_pts):
        d = dict(base_d)
        if isinstance(row, dict):
            for k in bound_keys:
                if k in row:
                    try:
                        d[k] = float(row[k])
                    except (TypeError, ValueError):
                        pass
        try:
            from src.models.inputs import PointInputs

            inp = PointInputs(**d)
        except Exception:
            inp = base

        out0 = ui_evaluate(inp, origin="NiceGUI:RobustPareto")
        nominal_feasible = bool(row.get("is_feasible", True)) if isinstance(row, dict) else True

        from ui_nicegui.evaluate import ui_evaluator

        ev = ui_evaluator(origin="NiceGUI:RobustPareto", cache_enabled=True)
        env = run_phase_envelope_for_point(
            inp, phases, label_prefix=f"{label_prefix}:p{i:04d}", evaluator=ev
        )
        env_s = (env.get("envelope_summary") or {}) if isinstance(env, dict) else {}
        env_verdict = str(env_s.get("envelope_verdict", "UNKNOWN"))
        env_worst_margin = env_s.get("worst_phase_worst_hard_margin_frac")
        try:
            env_worst_margin_f = float(env_worst_margin) if env_worst_margin is not None else float("nan")
        except (TypeError, ValueError):
            env_worst_margin_f = float("nan")

        uq = run_uncertainty_contract_for_point(
            inp, uq_spec, label_prefix=f"{label_prefix}:u{i:04d}", evaluator=ev
        )
        uq_sum = (uq.get("summary") or {}) if isinstance(uq, dict) else {}
        uq_verdict = str(uq_sum.get("verdict", "UNKNOWN"))
        uq_worst_margin = uq_sum.get("worst_hard_margin_frac")
        try:
            uq_worst_margin_f = float(uq_worst_margin) if uq_worst_margin is not None else float("nan")
        except (TypeError, ValueError):
            uq_worst_margin_f = float("nan")

        tier = _classify_robust(nominal_feasible, env_verdict, uq_verdict)

        def _val_from_out(o: dict, k: str) -> float:
            try:
                v = o.get(k)
                return float(v) if v is not None else float("nan")
            except (TypeError, ValueError):
                return float("nan")

        worst_phase_idx = int(env.get("worst_phase_index", 0) or 0) if isinstance(env, dict) else 0
        worst_phase_out: dict = {}
        try:
            phs = env.get("phases_ordered") if isinstance(env, dict) else None
            if isinstance(phs, list) and 0 <= worst_phase_idx < len(phs):
                wp = phs[worst_phase_idx]
                worst_phase_out = (wp.get("outputs") if isinstance(wp, dict) else None) or {}
        except Exception:
            pass
        worst_corner_out: dict = {}
        try:
            ci = uq_sum.get("worst_corner_index")
            corners = uq.get("corners") if isinstance(uq, dict) else None
            if ci is not None and isinstance(corners, list):
                cidx = int(ci)
                if 0 <= cidx < len(corners):
                    wc = corners[cidx]
                    worst_corner_out = (wc.get("outputs") if isinstance(wc, dict) else None) or {}
        except Exception:
            pass

        rec: dict = {
            "i": i,
            "tier": tier,
            "env_verdict": env_verdict,
            "uq_verdict": uq_verdict,
            "env_worst_margin": env_worst_margin_f,
            "uq_worst_margin": uq_worst_margin_f,
            "nominal_feasible": nominal_feasible,
            "dominant_constraint": row.get("dominant_constraint") if isinstance(row, dict) else None,
        }
        if isinstance(row, dict):
            for k in bound_keys:
                if k in row:
                    rec[k] = row.get(k)
        for ok, sense in obj_senses.items():
            nom = _val_from_out(out0, ok)
            wph = _val_from_out(worst_phase_out, ok)
            wco = _val_from_out(worst_corner_out, ok)
            rob = _robust_objective_agg(str(sense), [nom, wph, wco])
            rec[f"robust_{ok}"] = rob
            if nom == nom and nom != 0 and rob == rob:
                rec[f"degrade_{ok}"] = float((rob - nom) / abs(nom))
            else:
                rec[f"degrade_{ok}"] = float("nan")
        rows.append(rec)
        point_arts.append(
            {
                "index": i,
                "inputs": dict(inp.__dict__) if hasattr(inp, "__dict__") else d,
                "nominal_outputs": dict(out0),
                "phase_envelope": env,
                "uncertainty_contract": uq,
            }
        )

    counts: Dict[str, int] = {}
    for r in rows:
        counts[str(r.get("tier", "?"))] = counts.get(str(r.get("tier", "?")), 0) + 1
    root = repo()
    ver = "unknown"
    try:
        vp = root / "VERSION"
        if vp.is_file():
            ver = vp.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return {
        "schema": "robust_pareto.v1",
        "shams_version": ver,
        "rows": rows,
        "points": point_arts,
        "counts": counts,
        "n": len(rows),
        "objectives": obj_senses,
        "phase_spec_json": phases_json,
        "uq_spec_json": uq_json,
    }


def load_records_from_upload(name: str, data: bytes) -> List[dict]:
    name_l = str(name or "").lower()
    if name_l.endswith(".jsonl"):
        out = []
        for ln in data.splitlines():
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln.decode("utf-8"))
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
        return out
    if name_l.endswith(".json"):
        obj = json.loads(data.decode("utf-8"))
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict) and isinstance(obj.get("records"), list):
            return [x for x in obj["records"] if isinstance(x, dict)]
    if name_l.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            for cand in ("results.jsonl", "results.json", "candidates_eval.jsonl"):
                if cand in zf.namelist():
                    return load_records_from_upload(cand, zf.read(cand))
    return []


def build_regime_atlas(records: List[dict], cfg: dict) -> dict:
    from analysis.regime_conditioned_atlas_v365 import AtlasConfig, MetricSpec, build_regime_conditioned_atlas

    metrics = tuple(MetricSpec(m["key"], m["dir"]) for m in cfg.get("metrics") or [])
    atlas_cfg = AtlasConfig(
        conditioning_axes=tuple(cfg.get("axes") or ("dominance_label",)),
        min_bucket_size=int(cfg.get("min_bucket_size", 8)),
        feasibility_gate=str(cfg.get("feasibility_gate", "robust_only")),
        metrics=metrics,
    )
    return build_regime_conditioned_atlas(records, atlas_cfg)


def atlas_evidence_zip(atlas: dict) -> bytes:
    import hashlib
    import time

    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_regime_atlas_export

    payload = watermark_regime_atlas_export(atlas if isinstance(atlas, dict) else {})
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"atlas_v365_{ts}"
    files: Dict[str, bytes] = {}
    files[f"{base}/atlas.json"] = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)
            zf.writestr(f"{base}/MANIFEST_SHA256.txt", f"{hashlib.sha256(content).hexdigest()}  {path}\n")
    return bio.getvalue()


def _row_claim_infeasible(row: Mapping[str, Any]) -> bool:
    """True when a candidate/row should have claim FoMs watermarked (PHYS-KPI-001)."""
    if not isinstance(row, Mapping):
        return False
    if "feasible_hard" in row:
        return not bool(row.get("feasible_hard"))
    if "nominal_feasible" in row:
        return not bool(row.get("nominal_feasible"))
    if "feasible" in row:
        return not bool(row.get("feasible"))
    if "is_feasible" in row:
        return not bool(row.get("is_feasible"))
    verdict = str(row.get("verdict") or row.get("intent_verdict") or row.get("tier") or "").upper()
    if verdict in ("INFEASIBLE", "FAIL", "REJECTED", "NO-SOLUTION", "NO_SOLUTION"):
        return True
    if verdict.startswith("FAIL") or verdict.startswith("INFEAS"):
        return True
    return False


def watermark_extopt_json_obj(obj: Any) -> Any:
    """PHYS-KPI-001: watermark claim FoMs inside ExtOpt JSON payloads (best-effort)."""
    from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        format_claim_kpi_for_table,
        is_claim_kpi_key,
        watermark_claim_kpi_map,
        watermark_regime_atlas_export,
        watermark_robust_pareto_export,
    )

    if isinstance(obj, list):
        return [watermark_extopt_json_obj(x) for x in obj]
    if not isinstance(obj, dict):
        return obj

    # Known high-level schemas first.
    schema = str(obj.get("schema") or "")
    if "regime" in schema.lower() or "pareto_sets" in obj:
        return watermark_regime_atlas_export(obj)
    if "robust" in schema.lower() or (
        isinstance(obj.get("rows"), list) and any(
            isinstance(r, dict) and ("nominal_feasible" in r or str(r.get("tier") or "").upper() == "FAIL")
            for r in (obj.get("rows") or [])[:8]
        )
    ):
        return watermark_robust_pareto_export(obj)
    if isinstance(obj.get("outputs"), dict) or (
        isinstance(obj.get("verdict"), str) and isinstance(obj.get("kpis"), dict)
    ):
        return watermark_run_artifact_export(obj)

    out: Dict[str, Any] = {}
    for k, v in obj.items():
        key = str(k)
        if key in ("results", "candidates", "records", "points", "rows") and isinstance(v, list):
            rows_out = []
            for r in v:
                if not isinstance(r, dict):
                    rows_out.append(watermark_extopt_json_obj(r))
                    continue
                rr = dict(r)
                if _row_claim_infeasible(rr):
                    for rk, rv in list(rr.items()):
                        if is_claim_kpi_key(str(rk)):
                            rr[rk] = format_claim_kpi_for_table(str(rk), rv, feasible=False)
                        elif str(rk) in ("outputs", "kpis", "metrics", "headline", "nominal_outputs") and isinstance(
                            rv, dict
                        ):
                            rr[rk] = watermark_claim_kpi_map(rv, feasible=False, point_out=rv)
                        elif str(rk) == "artifact" and isinstance(rv, dict):
                            rr[rk] = watermark_run_artifact_export(rv)
                        else:
                            rr[rk] = watermark_extopt_json_obj(rv)
                else:
                    rr = {rk: watermark_extopt_json_obj(rv) for rk, rv in rr.items()}
                rows_out.append(rr)
            out[key] = rows_out
        elif key in ("outputs", "kpis", "metrics", "headline") and isinstance(v, dict):
            # Only watermark if parent looks infeasible.
            if _row_claim_infeasible(obj):
                out[key] = watermark_claim_kpi_map(v, feasible=False, point_out=v)
            else:
                out[key] = watermark_extopt_json_obj(v)
        elif key == "artifact" and isinstance(v, dict):
            out[key] = watermark_run_artifact_export(v) if _row_claim_infeasible(obj) or _row_claim_infeasible(v) else watermark_extopt_json_obj(v)
        else:
            out[key] = watermark_extopt_json_obj(v)
    if any(
        isinstance(obj.get(k), list) and any(_row_claim_infeasible(r) for r in (obj.get(k) or []) if isinstance(r, dict))
        for k in ("results", "candidates", "records", "points", "rows")
    ):
        out.setdefault(
            "phys_kpi_note",
            "PHYS-KPI-001: claim FoMs on INFEASIBLE / FAIL ExtOpt candidates are "
            "— (diagnostic) — not design claims.",
        )
    return out


def watermark_concept_cockpit_export(rep: Mapping[str, Any]) -> Dict[str, Any]:
    """PHYS-KPI-001: download copy of concept-cockpit batch results."""
    out = watermark_extopt_json_obj(dict(rep) if isinstance(rep, Mapping) else {})
    if isinstance(out, dict):
        out.setdefault(
            "phys_kpi_note",
            "PHYS-KPI-001: claim FoMs on hard-infeasible concept-cockpit rows are "
            "— (diagnostic) — not design claims.",
        )
        return out
    return dict(rep) if isinstance(rep, Mapping) else {}


def watermark_extopt_zip_bytes(data: bytes) -> bytes:
    """PHYS-KPI-001: rewrite ExtOpt/optimizer ZIP JSON members with claim FoMs watermarked.

    Nested ZIPs (evidence packs) are processed recursively. Non-JSON members are
    copied unchanged. On parse failure, original member bytes are kept.
    """
    if not data:
        return data
    try:
        zin = zipfile.ZipFile(io.BytesIO(data), "r")
    except zipfile.BadZipFile:
        return data

    out_buf = io.BytesIO()
    with zin, zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info in sorted(zin.infolist(), key=lambda z: z.filename):
            name = info.filename
            raw = zin.read(info)
            lower = name.lower()
            try:
                if lower.endswith(".zip"):
                    zout.writestr(name, watermark_extopt_zip_bytes(raw))
                elif lower.endswith(".jsonl"):
                    from ui_nicegui.lib.suite_extended_helpers import watermark_campaign_jsonl_bytes

                    # Reuse JSONL line watermark (feasible_hard / feasible).
                    zout.writestr(name, watermark_campaign_jsonl_bytes(raw))
                elif lower.endswith(".json"):
                    obj = json.loads(raw.decode("utf-8"))
                    wm = watermark_extopt_json_obj(obj)
                    zout.writestr(
                        name,
                        json.dumps(wm, indent=2, sort_keys=True, default=str).encode("utf-8"),
                    )
                else:
                    zout.writestr(name, raw)
            except Exception:
                zout.writestr(name, raw)
    return out_buf.getvalue()


def build_design_families(session, *, source: str = "pareto") -> dict:
    from src.narratives.design_families import FamilyConfig, build_design_families as _build

    pl = getattr(session, "pareto_last", None)
    if not isinstance(pl, dict):
        raise RuntimeError("Run Internal Pareto Frontier first")
    recs = pl.get("pareto") if source == "pareto" else pl.get("feasible")
    if not isinstance(recs, list) or not recs:
        raise RuntimeError("No records for selected source")
    fams = _build(recs, cfg=FamilyConfig())
    return {"families": fams, "n_records": len(recs), "source": source}


def list_concept_family_yamls() -> List[Path]:
    ex = repo() / "examples" / "concept_families"
    if not ex.is_dir():
        return []
    return sorted(ex.glob("*.y*ml"))


def run_extopt_workbench(*, family_yaml: Path, seed: int, n_proposals: int, robust: bool, evaluator_label: str) -> str:
    from clients.reference_optimizer import run_reference_optimizer
    from ui_nicegui.evaluate import ui_evaluator

    out_dir = repo() / "ui_runs" / "extopt_workbench"
    out_dir.mkdir(parents=True, exist_ok=True)
    ev = ui_evaluator(origin=f"NiceGUI:ExtOptWorkbench:{evaluator_label}", cache_enabled=True)
    bundle = run_reference_optimizer(
        family_yaml=Path(family_yaml),
        out_dir=out_dir,
        seed=int(seed),
        n_proposals=int(n_proposals),
        evaluator_label=str(evaluator_label),
        evaluator=ev,
        robust=bool(robust),
    )
    return str(bundle)


def run_orchestrator_v385(*, yaml_bytes: bytes, yaml_name: str, evaluator_label: str, intent: str, include_ep: bool) -> dict:
    from src.extopt.orchestrator_v385 import OrchestratorRunSpec, run_orchestrator_v385_from_concept_family
    from ui_nicegui.evaluate import ui_evaluator

    tdir = repo() / "ui_runs" / "uploads"
    tdir.mkdir(parents=True, exist_ok=True)
    p = tdir / yaml_name
    p.write_bytes(yaml_bytes)
    out_dir = repo() / "ui_runs" / "extopt_orchestrator_v385"
    out_dir.mkdir(parents=True, exist_ok=True)
    rs = OrchestratorRunSpec(
        evaluator_label=str(evaluator_label),
        intent=str(intent),
        include_evidence_packs=bool(include_ep),
        cache_enabled=True,
    )
    ev = ui_evaluator(origin=f"NiceGUI:ExtOptOrchestrator:{evaluator_label}", cache_enabled=True)
    res = run_orchestrator_v385_from_concept_family(
        concept_family_yaml=p,
        repo_root=repo(),
        out_dir=out_dir,
        runspec=rs,
        evaluator=ev,
    )
    return {
        "n_total": res.n_total,
        "n_feasible": res.n_feasible,
        "pass_rate": res.pass_rate,
        "run_dir": str(res.run_dir),
        "bundle_zip": str(res.bundle_zip),
    }


def interpret_optimizer_trace(trace: dict, repo_root_path: Optional[Path] = None) -> dict:
    from src.extopt.interpretation import interpret_optimizer_trace

    return interpret_optimizer_trace(trace, repo_root=repo_root_path or repo())


def list_optimizer_run_dirs() -> List[Path]:
    root = repo() / "runs" / "optimizer"
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return sorted(dirs, key=lambda p: p.name, reverse=True)


def read_run_json(run_dir: Path, name: str) -> Optional[dict]:
    p = run_dir / name
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_optimizer_job(*, kit: str, seed: int, n: int, objectives: List[str], senses: dict, bounds: dict, base) -> dict:
    from src.extopt.orchestrator import OptimizerJob, run_optimizer_job as _run_job
    from src.optimization.extopt_contract_bridge import (
        EXTOPT_LEGACY_HONESTY,
        build_bridged_extopt_job_contract,
    )
    from ui_nicegui.evaluate import ui_evaluator

    objs = list(objectives)
    sense_map = {str(o): str(senses.get(o, "min")) for o in objs}
    # Phase 3.3: ExtOpt wire stays objective_contract.v3 for OptimizerJob, but
    # always attaches Opt Lab objective_contract.v1 / multi_objective_contract.v1
    # so Pareto / Opt Lab never see a silent dual-truth FoM schema.
    objective_contract = build_bridged_extopt_job_contract(
        objectives=objs,
        senses=sense_map,
        seed=int(seed),
    )
    assert objective_contract.get("schema") == "objective_contract.v3"
    assert "opt_lab_contract" in objective_contract
    _ = EXTOPT_LEGACY_HONESTY  # honesty embedded on wire payload
    # Bounds values may be tuples from knob sets — normalize to [lo, hi] lists.
    norm_bounds: Dict[str, List[float]] = {}
    for k, v in (bounds or {}).items():
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            norm_bounds[str(k)] = [float(v[0]), float(v[1])]
    job = OptimizerJob(
        schema_version="optimizer_job.v2",
        kit=str(kit),
        seed=int(seed),
        n=int(n),
        objective_contract=objective_contract,
        objectives=objs,
        objective_senses=sense_map,
        bounds=norm_bounds,
        base_inputs=asdict(base) if hasattr(base, "__dataclass_fields__") else dict(base),
        verify_request={"phase_envelope": False, "uq_contracts": False},
    )
    ev = ui_evaluator(origin="NiceGUI:CCFS:OptimizerJob", cache_enabled=True)
    run_dir = _run_job(repo(), job, evaluator=ev)
    dossier_path = Path(run_dir) / "optimizer_dossier.json"
    if dossier_path.is_file():
        try:
            out = json.loads(dossier_path.read_text(encoding="utf-8"))
            if isinstance(out, dict):
                out = dict(out)
                out["run_dir"] = str(run_dir)
                return out
        except Exception:
            pass
    return {"run_dir": str(run_dir), "schema_version": "optimizer_dossier.v1"}


def evaluate_concept_family_yaml(path: Path, *, label: str = "NiceGUI:Cockpit") -> dict:
    from extopt import BatchEvalConfig, evaluate_concept_family
    from extopt.family import load_concept_family
    from ui_nicegui.evaluate import ui_evaluator

    fam = load_concept_family(path)
    cfg = BatchEvalConfig(evaluator_label="hot_ion_point", cache_enabled=False, cache_dir=None)
    ev = ui_evaluator(origin=str(label or "NiceGUI:Cockpit"), cache_enabled=True)
    ber = evaluate_concept_family(fam, config=cfg, evaluator=ev)
    return {
        "summary": dict(ber.summary),
        "n_total": int(ber.n_total),
        "n_feasible": int(ber.n_feasible),
        "pass_rate": float(ber.pass_rate),
        "family_name": str(ber.family_name),
        "intent": str(ber.intent),
        "results": [
            {
                "cid": r.cid,
                "feasible_hard": bool(r.feasible_hard),
                "intent_verdict": (r.artifact or {}).get("intent_verdict"),
                "verdict": (r.artifact or {}).get("verdict"),
                "dominant_constraint": (r.artifact or {}).get("dominant_constraint"),
                "cache_hit": bool(r.cache_hit),
            }
            for r in ber.results
        ],
    }


def launch_optimizer_kit(*, kit: str, seed: int, n: int, objectives: List[str], senses: dict, bounds: dict, base) -> dict:
    pending = repo() / "runs" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    cfg_path = pending / f"optimizer_kit_{seed}_{n}.json"
    cfg = {
        "schema": "optimizer_kit.v1",
        "kit": str(kit),
        "seed": int(seed),
        "n": int(n),
        "objectives": list(objectives),
        "objective_senses": dict(senses),
        "bounds": {k: [float(v[0]), float(v[1])] for k, v in bounds.items()},
        "base_inputs": asdict(base) if hasattr(base, "__dataclass_fields__") else dict(base),
    }
    cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    script = repo() / "clients" / "optimizer_kits" / "run_kit.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo()), "--config", str(cfg_path)],
        capture_output=True,
        text=True,
        cwd=str(repo()),
    )
    return {
        "returncode": int(proc.returncode),
        "config_path": str(cfg_path),
        "stdout": (proc.stdout or "")[:8000],
        "stderr": (proc.stderr or "")[:8000],
    }


def run_two_lane_uq(base) -> dict:
    from src.uq_contracts.runner import run_uncertainty_contract_for_point
    from src.uq_contracts.spec import optimistic_uncertainty_contract, robust_uncertainty_contract
    from ui_nicegui.evaluate import ui_evaluator

    ev = ui_evaluator(origin="NiceGUI:TwoLaneUQ", cache_enabled=True)
    uqO = run_uncertainty_contract_for_point(
        base, optimistic_uncertainty_contract(base), label_prefix="laneO", evaluator=ev
    )
    uqR = run_uncertainty_contract_for_point(
        base, robust_uncertainty_contract(base), label_prefix="laneR", evaluator=ev
    )
    sO = dict((uqO.get("summary") or {}))
    sR = dict((uqR.get("summary") or {}))
    vO, vR = str(sO.get("verdict", "")), str(sR.get("verdict", ""))
    cls = "ROBUST" if vR == "ROBUST_PASS" else ("MIRAGE" if vO == "ROBUST_PASS" else "FAIL")
    return {"O": uqO, "R": uqR, "class": cls, "verdict_O": vO, "verdict_R": vR}


def run_mirage_path_scan(base, knob: str, lo: float, hi: float, n: int) -> dict:
    from ui_nicegui.evaluate import ui_evaluator
    from src.trade_studies.pathfinding import one_knob_path_scan

    ev = ui_evaluator(origin="NiceGUI:MiragePath", cache_enabled=True)
    return one_knob_path_scan(ev, base, knob, lo=lo, hi=hi, n=int(n))


def default_pathfinding_levers(base) -> List[Tuple[str, float, float]]:
    from src.trade_studies.pathfinding import default_pathfinding_levers

    return list(default_pathfinding_levers(base))


def build_v351_atlas(session, *, objectives: List[str], senses: dict) -> dict:
    from src.atlas.frontier_atlas_v351 import bin_counts, pareto_front

    rep = getattr(session, "trade_last", None) or {}
    cap = getattr(session, "active_study_capsule", None)
    records = (cap or rep).get("records") or rep.get("records") or []
    feas = [r for r in records if isinstance(r, dict) and bool(r.get("is_feasible"))]
    all_infeasible = bool(records) and not feas
    pareto_rows = pareto_front(feas, objectives=list(objectives), senses=senses) if feas else []
    return {
        "schema": "shams.frontier_atlas.v351",
        "objectives": list(objectives),
        "n_total": len(records),
        "n_feasible": len(feas),
        "n_pareto": len(pareto_rows),
        "pareto": pareto_rows,
        "all_infeasible": all_infeasible,
    }


def build_v324_regime_maps(records: List[dict], *, features: List[str], min_cluster: int, max_bins: int) -> dict:
    from tools.regime_maps import build_regime_maps_report

    return build_regime_maps_report(
        records=records,
        features=list(features),
        min_cluster_size=int(min_cluster),
        max_bins=int(max_bins),
    )


def family_summary_rows(records: List[dict]) -> dict:
    from src.trade_studies.families import family_summary

    return family_summary(records)
