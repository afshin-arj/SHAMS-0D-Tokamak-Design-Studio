from __future__ import annotations
"""Demo artifact seed + panel hydration (v172)

Purpose:
- Allow every UI panel to show real content immediately, even offline, without requiring the user to run solvers.
- Injects a small set of demo artifacts into st.session_state (run artifact, sensitivity, protocol, lock, replay, pack manifest, citation).
- Does NOT change solver/physics; the demo objects are clearly marked and non-authoritative.

API:
- build_demo_bundle() -> dict of artifacts
- install_demo_bundle(session_state) -> None (mutates dict-like session_state)
"""

from typing import Any, Dict
import time, json, hashlib

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(s: str) -> str:
    h=hashlib.sha256(); h.update(s.encode("utf-8")); return h.hexdigest()

def build_demo_bundle() -> Dict[str, Any]:
    issued=_utc()
    # Minimal demo run artifact (structure aligned with SHAMS expectations)
    run_art={
        "kind":"shams_run_artifact",
        "version":"demo_v172",
        "issued_utc": issued,
        "inputs": {"R0": 3.0, "a": 1.0, "B0": 12.0, "Ip": 10.0, "kappa": 1.8, "delta": 0.35},
        "assumptions": {"demo": True, "note":"Synthetic demo; not a real design."},
        "solver_meta": {"mode":"demo", "backend":"none"},
        "metrics": {"P_fus": 500.0, "Q": 10.0, "q95": 3.2},
        "constraints": [
            {"name":"beta_limit", "margin": 0.10, "value": 0.030, "limit": 0.033, "sense":"<="},
            {"name":"coil_stress", "margin": -0.05, "value": 1050, "limit": 1000, "sense":"<="},
        ],
        "min_margin": -0.05,
        "dominant_constraint":"coil_stress",
        "tags":["DEMO","NON-AUTHORITATIVE"],
    }

    # Demo sensitivity report v164-like
    sens={
        "kind":"shams_sensitivity_report",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{
            "witness": {"inputs": run_art["inputs"], "min_margin": run_art["min_margin"], "dominant_constraint": run_art["dominant_constraint"]},
            "variables":[
                {"name":"B0", 'd_min_margin_dx': 0.012, "min_margin_base": -0.05, "min_margin_plus": -0.04, "min_margin_minus": -0.06},
                {"name":"R0", 'd_min_margin_dx': 0.008, "min_margin_base": -0.05, "min_margin_plus": -0.045, "min_margin_minus": -0.055},
                {"name":"Ip", 'd_min_margin_dx': -0.006, "min_margin_base": -0.05, "min_margin_plus": -0.053, "min_margin_minus": -0.047},
            ],
        },
    }

    # Demo study protocol v165
    prot={
        "kind":"shams_study_protocol",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{
            "study":{"title":"Demo SHAMS Study (Non-authoritative)"},
            "integrity":{"protocol_sha256": _sha("demo_protocol_v172")},
        },
    }

    # Demo lock + replay (v166-ish)
    lock={
        "kind":"shams_repro_lock",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{"integrity":{"lock_sha256": _sha("demo_lock_v172")}},
    }
    replay={
        "kind":"shams_replay_report",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{"ok": True, "note":"Synthetic demo replay; ok."},
    }

    # Demo authority pack manifest (v167-ish)
    manifest={
        "kind":"shams_authority_pack_manifest",
        "version":"demo_v172",
        "issued_utc": issued,
        "files":[{"name":"run_artifact.json","sha256": _sha("demo_run"), "bytes": 1234}],
    }

    # Demo citation bundle (v168-ish)
    sid="SHAMS-" + _sha("demo_protocol_v172|demo_lock_v172|demo_pack_v172")[:16].upper()
    cite={
        "kind":"shams_citation_bundle",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{
            "study_id": sid,
            "citation_cff_text": "cff-version: 1.2.0\nmessage: \"Demo citation.\"\n",
            "bibtex_text": "@misc{DEMO, title={Demo}}\n",
            "reference_markdown": f"# Demo\n\nStudy ID: `{sid}`\n",
        },
    }

    # Demo completion pack v163-ish
    comp={
        "kind":"shams_completion_pack",
        "version":"demo_v172",
        "issued_utc": issued,
        "payload":{"note":"Synthetic completion recipe; not a real feasibility completion."},
    }

    return {
        "run_artifact": run_art,
        "sensitivity": sens,
        "study_protocol": prot,
        "repro_lock": lock,
        "replay_report": replay,
        "authority_manifest": manifest,
        "citation_bundle": cite,
        "completion_pack": comp,
    }

def install_demo_bundle(session_state: Any) -> None:
    b=build_demo_bundle()
    # Place into the keys that UI panels already use
    session_state["v164_sensitivity"]=b["sensitivity"]
    session_state["v165_protocol"]=b["study_protocol"]
    session_state["v166_lock"]=b["repro_lock"]
    session_state["v166_replay"]=b["replay_report"]
    session_state["v167_manifest"]=b["authority_manifest"]
    session_state["v168_citation"]=b["citation_bundle"]
    session_state["v163_pack"]=b["completion_pack"]

    # Point Designer cached outputs/artifacts so Results panes populate
    session_state["pd_last_outputs"]={"metrics": b["run_artifact"].get("metrics"), "constraints": b["run_artifact"].get("constraints")}
    session_state["pd_last_artifact"]=b["run_artifact"]

    # Also add to run history if the state object exists (UI will merge)
    session_state["demo_run_artifact"]=b["run_artifact"]
