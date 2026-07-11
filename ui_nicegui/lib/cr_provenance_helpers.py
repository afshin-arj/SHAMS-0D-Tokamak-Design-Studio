"""Control Room Provenance helpers — studies, protocol, repro, regression."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ui_nicegui.bootstrap import repo_root


def list_session_run_artifacts(session) -> List[Dict[str, Any]]:
    """Collect shams_run_artifact dicts available on the NiceGUI session."""
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _append(art: Any, *, label: str, rid: str) -> None:
        if not isinstance(art, dict):
            return
        if not (art.get("outputs") or art.get("kind") == "shams_run_artifact"):
            return
        key = str(rid)
        if key in seen:
            return
        seen.add(key)
        out.append({"id": key, "label": label, "artifact": art})

    art = getattr(session, "pd_last_artifact", None)
    if isinstance(art, dict):
        rid = str(art.get("run_id") or art.get("id") or "point_designer_last")
        _append(art, label=f"Point Designer ({rid})", rid=rid)

    sys_art = getattr(session, "systems_last_solve_artifact", None)
    if isinstance(sys_art, dict):
        rid = str(sys_art.get("run_id") or sys_art.get("id") or "systems_last")
        _append(sys_art, label=f"Systems Mode ({rid})", rid=rid)

    for key, deck_label in (
        ("scan_cartography_report", "Scan Lab cartography"),
        ("pareto_last", "Pareto Lab"),
        ("trade_last", "Trade Study Studio"),
        ("pub_atlas_last", "Publication Benchmarks"),
    ):
        payload = getattr(session, key, None)
        if isinstance(payload, dict):
            rid = str(payload.get("run_id") or payload.get("id") or key)
            _append(payload, label=f"{deck_label} ({rid})", rid=rid)

    for slot, label in (("cmp_slot_a", "Compare slot A"), ("cmp_slot_b", "Compare slot B")):
        slot_art = getattr(session, slot, None)
        if isinstance(slot_art, dict):
            rid = str(slot_art.get("run_id") or slot_art.get("id") or slot)
            _append(slot_art, label=f"{label} ({rid})", rid=rid)

    if isinstance(getattr(session, "cr_selected_artifact", None), dict):
        art_sel = session.cr_selected_artifact
        rid = str(art_sel.get("run_id") or art_sel.get("id") or "cr_selected")
        _append(art_sel, label=f"Selected artifact ({rid})", rid=rid)

    return out


def ensure_run_artifact(art: dict) -> dict:
    if art.get("kind") == "shams_run_artifact":
        return art
    wrapped = dict(art)
    wrapped.setdefault("kind", "shams_run_artifact")
    return wrapped


def build_study_protocol(run_artifact: dict, overrides: dict) -> dict:
    from tools.study_protocol_v165 import build_study_protocol as _build

    return _build(run_artifact=ensure_run_artifact(run_artifact), protocol_overrides=overrides)


def study_protocol_markdown(protocol: dict) -> str:
    from tools.study_protocol_v165 import render_study_protocol_markdown

    return render_study_protocol_markdown(protocol)


def build_repro_lock(run_artifact: dict, overrides: dict) -> dict:
    from tools.repro_lock_v166 import build_repro_lock as _build

    return _build(run_artifact=ensure_run_artifact(run_artifact), lock_overrides=overrides)


def replay_check(lock: dict, assumption_override: Optional[dict] = None) -> dict:
    from tools.repro_lock_v166 import replay_check as _check

    return _check(
        lock=lock,
        assumption_set_override=assumption_override if isinstance(assumption_override, dict) else None,
        policy={"generator": "NiceGUI"},
    )


def build_authority_pack_zip(
    *,
    run_artifact: dict,
    protocol: Optional[dict] = None,
    lock: Optional[dict] = None,
    replay: Optional[dict] = None,
) -> bytes:
    from tools.authority_pack_v167 import build_authority_pack

    pack = build_authority_pack(
        run_artifact=ensure_run_artifact(run_artifact),
        study_protocol_v165=protocol if isinstance(protocol, dict) else None,
        repro_lock_v166=lock if isinstance(lock, dict) else None,
        replay_report_v166=replay if isinstance(replay, dict) else None,
        completion_pack_v163=None,
        sensitivity_v164=None,
        certificate_v160=None,
        policy={"generator": "NiceGUI"},
    )
    zbytes = pack.get("zip_bytes")
    if isinstance(zbytes, (bytes, bytearray)) and len(zbytes) > 0:
        return bytes(zbytes)
    raise RuntimeError("Authority pack ZIP bytes missing")


def build_citation_bundle(protocol: dict, *, lock: Optional[dict] = None, metadata: Optional[dict] = None) -> dict:
    from tools.citation_v168 import build_citation_bundle as _build

    return _build(
        study_protocol_v165=protocol,
        repro_lock_v166=lock if isinstance(lock, dict) else None,
        authority_pack_manifest_v167=None,
        metadata=metadata or {},
    )


def save_point_study(session, *, notes: str = "") -> dict:
    entry = {
        "type": "point",
        "created": datetime.now(timezone.utc).isoformat(),
        "inputs": dict(session.inputs),
        "notes": notes,
    }
    studies = list(getattr(session, "cr_studies", []) or [])
    studies.append(entry)
    session.cr_studies = studies
    return entry


def regression_artifact_diff(art_a: dict, art_b: dict) -> dict:
    def _kpi_map(art: dict) -> dict:
        k = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
        if k:
            return dict(k)
        out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
        keys = ("Q", "Pfus_total_MW", "P_e_net_MW", "beta_N", "q95", "TBR")
        return {kk: out.get(kk) for kk in keys if kk in out}

    def _cons_map(cons: list) -> dict:
        m: dict = {}
        for c in cons or []:
            if not isinstance(c, dict):
                continue
            name = c.get("name") or c.get("id")
            if name:
                m[str(name)] = c
        return m

    kA, kB = _kpi_map(art_a), _kpi_map(art_b)
    kpi_rows = []
    for name in sorted(set(kA.keys()) | set(kB.keys())):
        a, b = kA.get(name), kB.get(name)
        delta = None
        try:
            if a is not None and b is not None:
                delta = float(b) - float(a)
        except (TypeError, ValueError):
            pass
        kpi_rows.append({"kpi": name, "value_A": a, "value_B": b, "delta": delta})

    consA = art_a.get("constraints") if isinstance(art_a.get("constraints"), list) else []
    consB = art_b.get("constraints") if isinstance(art_b.get("constraints"), list) else []
    mA, mB = _cons_map(consA), _cons_map(consB)
    cons_rows = []
    for name in sorted(set(mA.keys()) | set(mB.keys())):
        a, b = mA.get(name, {}), mB.get(name, {})
        fa = bool(a.get("failed")) if isinstance(a, dict) else False
        fb = bool(b.get("failed")) if isinstance(b, dict) else False
        ma = a.get("margin") if isinstance(a, dict) else None
        mb = b.get("margin") if isinstance(b, dict) else None
        md = None
        try:
            if isinstance(ma, (int, float)) and isinstance(mb, (int, float)):
                md = float(mb) - float(ma)
        except (TypeError, ValueError):
            pass
        cons_rows.append(
            {
                "name": name,
                "failed_A": fa,
                "failed_B": fb,
                "margin_A": ma,
                "margin_B": mb,
                "margin_delta": md,
            }
        )
    new_failures = [r for r in cons_rows if r["failed_B"] and not r["failed_A"]]
    return {
        "kpi_rows": kpi_rows,
        "constraint_rows": cons_rows,
        "new_failures": new_failures,
        "model_set_A": art_a.get("model_set"),
        "model_set_B": art_b.get("model_set"),
    }


def run_repo_regression(*, rtol: float = 0.01, atol: float = 1e-6) -> dict:
    from tools.sandbox.tier7 import run_regression_suite

    return run_regression_suite(Path(repo_root()), rtol=float(rtol), atol=float(atol))
