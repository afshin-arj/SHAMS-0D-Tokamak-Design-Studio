"""Scan Lab artifact restore, replay audit, and import probes."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]


def probe_scan_imports() -> List[str]:
    """Return import error messages for optional Scan Lab engines."""
    errors: List[str] = []
    try:
        from src.evaluator.core import Evaluator  # noqa: F401
    except ImportError as exc:
        errors.append(f"Evaluator: {exc}")
    try:
        from tools.scan_cartography import build_cartography_report  # noqa: F401
    except ImportError as exc:
        errors.append(f"scan_cartography: {exc}")
    try:
        from tools.scan_artifact_schema import build_scan_artifact  # noqa: F401
    except ImportError as exc:
        errors.append(f"scan_artifact_schema: {exc}")
    try:
        from tools.scan_insights import build_causality_trace  # noqa: F401
    except ImportError as exc:
        errors.append(f"scan_insights: {exc}")
    try:
        from tools.scan_next_tier import local_powerlaw_fit  # noqa: F401
    except ImportError as exc:
        errors.append(f"scan_next_tier: {exc}")
    try:
        from tools.reports.scan_signature_atlas import build_signature_atlas_pdf_bytes  # noqa: F401
    except ImportError as exc:
        errors.append(f"scan_signature_atlas: {exc}")
    return errors


def restore_scan_artifact(payload: dict) -> Dict[str, Any]:
    """Upgrade and unpack a scan artifact into session field updates."""
    if not isinstance(payload, dict):
        raise ValueError("Artifact must be a JSON object")
    try:
        from tools.scan_artifact_schema import upgrade_scan_artifact
    except ImportError as exc:
        raise RuntimeError("Artifact restore unavailable (schema module missing)") from exc

    art = upgrade_scan_artifact(payload)
    rep = art.get("report")
    if not isinstance(rep, dict):
        raise ValueError("Artifact missing 'report'")
    settings = art.get("settings") if isinstance(art.get("settings"), dict) else {}
    updates: Dict[str, Any] = {
        "scan_cartography_report": rep,
        "scan_cartography_artifact": art,
    }
    if settings:
        for key, sess_key in (
            ("x_key", "scan_cart_x_key"),
            ("y_key", "scan_cart_y_key"),
            ("x_lo", "scan_cart_x_lo"),
            ("x_hi", "scan_cart_x_hi"),
            ("y_lo", "scan_cart_y_lo"),
            ("y_hi", "scan_cart_y_hi"),
            ("nx", "scan_cart_nx"),
            ("ny", "scan_cart_ny"),
            ("intents", "scan_cart_intents"),
            ("include_outputs", "scan_cart_include_outputs"),
        ):
            if key in settings and settings[key] is not None:
                updates[sess_key] = settings[key]
    return updates


def freeze_statement_text() -> str:
    path = _REPO_ROOT / "docs" / "SCANLAB_FREEZE.md"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return "(missing docs/SCANLAB_FREEZE.md)"


def compute_repo_fingerprints() -> dict:
    try:
        from tools.scan_expert_features import compute_fingerprints

        return compute_fingerprints(str(_REPO_ROOT))
    except Exception:
        return {}


def run_replay_determinism_audit(
    base,
    *,
    x_key: str,
    y_key: str,
    intents: List[str],
) -> dict:
    """Small neighborhood scan twice; compare stable hashes."""
    import numpy as np

    try:
        from src.evaluator.core import Evaluator
        from tools.scan_cartography import build_cartography_report
        from tools.scan_artifact_schema import stable_hash
    except ImportError as exc:
        raise RuntimeError("Replay audit unavailable (imports missing)") from exc

    bx = float(getattr(base, x_key, 1.0) or 1.0)
    by = float(getattr(base, y_key, 1.0) or 1.0)
    xv = list(np.linspace(0.95 * bx, 1.05 * bx, 11))
    yv = list(np.linspace(0.95 * by, 1.05 * by, 9))
    ev = Evaluator(label="NiceGUI:ScanReplay", cache_enabled=True, cache_max=4096)
    rep_a = build_cartography_report(
        evaluator=ev,
        base_inputs=base,
        x_key=str(x_key),
        y_key=str(y_key),
        x_vals=xv,
        y_vals=yv,
        intents=list(intents or ["Reactor"]),
        include_outputs=False,
    )
    rep_b = build_cartography_report(
        evaluator=ev,
        base_inputs=base,
        x_key=str(x_key),
        y_key=str(y_key),
        x_vals=xv,
        y_vals=yv,
        intents=list(intents or ["Reactor"]),
        include_outputs=False,
    )
    ha = {
        "report": stable_hash(rep_a),
        "dominance": stable_hash(rep_a.get("dominance", {})),
        "intent_stats": stable_hash(rep_a.get("intent_stats", {})),
    }
    hb = {
        "report": stable_hash(rep_b),
        "dominance": stable_hash(rep_b.get("dominance", {})),
        "intent_stats": stable_hash(rep_b.get("intent_stats", {})),
    }
    return {"pass": ha == hb, "runA": ha, "runB": hb}


def boundaries_json_bytes(rep: dict) -> Optional[bytes]:
    bnd = rep.get("boundaries") if isinstance(rep, dict) else None
    if not isinstance(bnd, dict) or not bnd:
        return None
    return json.dumps(bnd, indent=2, default=str).encode("utf-8")


def field_cube_json_bytes(rep: dict) -> Optional[bytes]:
    fc = rep.get("field_cube") if isinstance(rep, dict) else None
    if not isinstance(fc, dict) or not fc:
        return None
    return json.dumps(fc, indent=2, default=str).encode("utf-8")


def artifact_json_bytes(art: dict) -> bytes:
    return json.dumps(art, indent=2, default=str).encode("utf-8")


def append_scan_library_entry(rep: dict, *, tag: str, note: str) -> str:
    """Append scan metadata to docs/scan_library.json; return path."""
    lib_path = _REPO_ROOT / "docs" / "scan_library.json"
    lib: list = []
    if lib_path.is_file():
        try:
            lib = json.loads(lib_path.read_text(encoding="utf-8") or "[]")
        except Exception:
            lib = []
    meta = rep.get("metadata") if isinstance(rep.get("metadata"), dict) else {}
    fps = meta.get("fingerprints") if isinstance(meta.get("fingerprints"), dict) else {}
    lib.append(
        {
            "id": rep.get("id"),
            "tag": str(tag),
            "note": str(note).strip(),
            "x": rep.get("x_key"),
            "y": rep.get("y_key"),
            "intents": rep.get("intents"),
            "shams_version": rep.get("shams_version"),
            "fingerprint": fps.get("fingerprint"),
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    lib_path.write_text(json.dumps(lib, indent=2, default=str), encoding="utf-8")
    return str(lib_path)


def build_signature_atlas(
    rep: dict,
    *,
    title: str,
    map_png_by_intent: dict[str, bytes],
    intent_split_png: Optional[bytes] = None,
    claim: Optional[dict] = None,
) -> bytes:
    try:
        from tools.reports.scan_signature_atlas import build_signature_atlas_pdf_bytes
        from tools.scan_expert_features import SCAN_LAB_CONTRACT
    except ImportError as exc:
        raise RuntimeError("Signature atlas unavailable") from exc

    fps = compute_repo_fingerprints()
    return build_signature_atlas_pdf_bytes(
        report=rep,
        title=str(title),
        contract_md=str(SCAN_LAB_CONTRACT),
        fingerprints=fps,
        map_png_by_intent=map_png_by_intent,
        intent_split_png=intent_split_png,
        claim=claim if isinstance(claim, dict) else None,
    )


def build_summary_pdf(rep: dict, intent: str) -> Optional[bytes]:
    try:
        from tools.reports.scan_summary import build_scan_summary_pdf_bytes
        from ui_nicegui.lib.scan_workbench_helpers import dominance_map_png_bytes
    except ImportError:
        return None
    try:
        png = dominance_map_png_bytes(rep, str(intent))
        return build_scan_summary_pdf_bytes(report=rep, intent=str(intent), map_png=png)
    except Exception:
        return None
