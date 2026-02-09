"""SHAMS — One-Click Reviewer Packet Builder (v322)

Builds a deterministic ZIP bundle intended for reviewer rooms / publication
appendices.

Key properties (hard-locked by SHAMS law):
- Descriptive only (no ranking, no recommendation).
- Deterministic and replayable: inputs fully captured.
- Audit safe: per-packet manifest with SHA256 for each file.

This builder is intentionally UI-agnostic and can be called from Streamlit
or from CLI-style tooling.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import io
import json
import hashlib
import zipfile

from tools.sandbox.report_pack import build_report_pack
from tools.sandbox.review_room import build_review_trinity, build_attack_simulation
from tools.ui_wiring_index import build_ui_wiring_index_markdown


@dataclass(frozen=True)
class ReviewerPacketOptions:
    include_core_docs: bool = True
    include_candidate_snapshot: bool = True
    include_report_pack: bool = True
    include_review_trinity: bool = True
    include_attack_simulation: bool = True
    include_scan_grounding: bool = True
    include_run_capsule: bool = True
    include_ui_wiring_index: bool = True
    include_design_state_graph_snapshot: bool = True
    include_do_not_build_brief: bool = True
    include_repo_manifests: bool = True


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _read_text_if_exists(p: Path) -> Optional[str]:
    try:
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def _canonical_json_bytes(obj: Any) -> bytes:
    """Stable JSON encoding for deterministic artifacts.

    The SHAMS artifact layer sometimes carries dataclass objects (e.g. typed
    input structs) inside candidate snapshots or report packs. For reviewer
    packets we must serialize these deterministically without introducing any
    solver-like behavior.
    """

    def _coerce(x: Any) -> Any:
        if is_dataclass(x):
            return asdict(x)
        if isinstance(x, Path):
            return str(x)
        if isinstance(x, set):
            return sorted(list(x))
        if isinstance(x, tuple):
            return list(x)
        return x

    return json.dumps(obj, indent=2, sort_keys=True, default=_coerce).encode("utf-8")


def build_reviewer_packet_zip(
    *,
    candidate: Dict[str, Any],
    repo_root: Optional[Path] = None,
    run_capsule: Optional[Dict[str, Any]] = None,
    scan_grounding: Optional[Dict[str, Any]] = None,
    do_not_build_brief: Optional[Dict[str, Any]] = None,
    options: ReviewerPacketOptions = ReviewerPacketOptions(),
) -> Tuple[bytes, Dict[str, Any]]:
    """Build the reviewer packet ZIP bytes plus a summary dict.

    Parameters
    ----------
    candidate:
        Candidate dict as stored in the archive (should include inputs/outputs/constraints
        if available).
    repo_root:
        SHAMS repo root. If not provided, inferred relative to this file.
    run_capsule:
        Optional run capsule (replay capsule) dict.
    scan_grounding:
        Optional scan grounding dict (e.g., cartography context for the candidate).
    do_not_build_brief:
        Optional diagnostic brief dict.
    options:
        Bundle composition.
    """
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dict")

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    docs_root = repo_root / "docs"

    # Collect file payloads first (path_in_zip -> bytes) so we can hash them and
    # ensure deterministic ordering.
    payloads: List[Tuple[str, bytes]] = []

    def add_text(path_in_zip: str, text: str) -> None:
        payloads.append((path_in_zip, (text or "").encode("utf-8")))

    def add_bytes(path_in_zip: str, b: bytes) -> None:
        payloads.append((path_in_zip, b))

    # --- Core docs ---
    if options.include_core_docs:
        for name in [
            "MODEL_SCOPE_CARD.md",
            "VOCABULARY_LEDGER.md",
            "EXTERNAL_EXPOSURE_GUARDRAILS.md",
            "PROCESS_CROSSWALK.md",
            "EXTERNAL_EXPOSURE_CHECKLIST.md",
            "REVIEWER_PACKET.md",
        ]:
            t = _read_text_if_exists(docs_root / name)
            if t is not None:
                add_text(f"docs/{name}", t)

    # --- Candidate snapshot ---
    if options.include_candidate_snapshot:
        add_bytes("candidate.json", _canonical_json_bytes(candidate))

    # --- Report pack ---
    if options.include_report_pack:
        rp = build_report_pack(candidate=candidate)
        add_bytes("report_pack/report_pack.json", _canonical_json_bytes(rp.get("json") or {}))
        add_text("report_pack/report_pack.md", str(rp.get("markdown") or ""))
        add_text("report_pack/report_pack.csv", str(rp.get("csv") or ""))

    # --- Review Trinity ---
    if options.include_review_trinity:
        tri = build_review_trinity(candidate=candidate, scan_grounding=scan_grounding or {})
        add_text("review_trinity/review_trinity.md", str(tri.get("markdown") or ""))
        add_bytes("review_trinity/review_trinity.json", _canonical_json_bytes(tri))

    # --- Attack Simulation ---
    if options.include_attack_simulation:
        atk = build_attack_simulation(candidate=candidate, run_capsule=run_capsule or {})
        add_text("attack_simulation/attack_simulation.md", str(atk.get("markdown") or ""))
        add_bytes("attack_simulation/attack_simulation.json", _canonical_json_bytes(atk))

    # --- Optional scan grounding / run capsule ---
    if options.include_scan_grounding and isinstance(scan_grounding, dict) and scan_grounding:
        add_bytes("scan_grounding.json", _canonical_json_bytes(scan_grounding))
    if options.include_run_capsule and isinstance(run_capsule, dict) and run_capsule:
        add_bytes("run_capsule.json", _canonical_json_bytes(run_capsule))

    # --- Optional do-not-build ---
    if options.include_do_not_build_brief and isinstance(do_not_build_brief, dict) and do_not_build_brief:
        add_bytes("do_not_build_brief.json", _canonical_json_bytes(do_not_build_brief))

    
    # --- UI wiring index (static, reviewer-safe) ---
    if options.include_ui_wiring_index:
        try:
            md = build_ui_wiring_index_markdown(repo_root=repo_root)
            add_text("ui/UI_WIRING_INDEX.md", md)
        except Exception as e:
            # Never fail packet build on auxiliary artifact; include diagnostic note.
            add_text("ui/UI_WIRING_INDEX_ERROR.txt", f"{type(e).__name__}: {e}")

    # --- Design State Graph snapshot (inter-panel continuity artifact) ---
    if options.include_design_state_graph_snapshot and repo_root is not None:
        try:
            p = repo_root / "artifacts" / "dsg" / "current_dsg.json"
            t = _read_text_if_exists(p)
            if t is not None:
                add_text("dsg/CURRENT_DSG.json", t)
                # Add a small active-node summary for reviewers
                try:
                    import json as _json
                    data = _json.loads(t)
                    active = str(data.get("active_node_id") or "")
                    if active:
                        # find node record
                        nodes = list(data.get("nodes", []) or [])
                        rec = next((r for r in nodes if str(r.get("node_id")) == active), None)
                        if rec is not None:
                            ok = "OK" if bool(rec.get("ok", True)) else "FAIL"
                            md = [
                                "# Active Design Node",
                                "",
                                f"- node_id: `{active}`",
                                f"- seq: `{rec.get('seq', '')}`",
                                f"- status: **{ok}**",
                                f"- origin: `{rec.get('origin','')}`",
                                f"- inputs_sha256: `{rec.get('inputs_sha256','')}`",
                                f"- outputs_sha256: `{rec.get('outputs_sha256','')}`",
                            ]
                            msg = str(rec.get("message", "") or "").strip()
                            if msg:
                                md += ["", "## Message", "", msg]
                            add_text("dsg/ACTIVE_NODE.md", "\n".join(md) + "\n")
                except Exception:
                    pass
        except Exception:
            pass

# --- Repo manifests (audit context) ---
    if options.include_repo_manifests:
        for name in ["MANIFEST_SHA256.txt", "MANIFEST_UPGRADE_SHA256.txt", "RELEASE_NOTES.md", "GOVERNANCE.md"]:
            t = _read_text_if_exists(repo_root / name)
            if t is not None:
                add_text(f"repo/{name}", t)

    # Build per-file manifest (hashes)
    manifest_rows: List[Dict[str, str]] = []
    for path_in_zip, b in sorted(payloads, key=lambda x: x[0]):
        manifest_rows.append(
            {
                "path": path_in_zip,
                "sha256": _sha256_bytes(b),
                "bytes": str(len(b)),
            }
        )
    packet_manifest = {
        "schema": "shams.reviewer_packet.manifest.v1",
        "author": "© 2026 Afshin Arjhangmehr",
        "files": manifest_rows,
    }
    add_bytes("MANIFEST_PACKET_SHA256.json", _canonical_json_bytes(packet_manifest))

    # Create zip with deterministic metadata
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path_in_zip, b in sorted(payloads, key=lambda x: x[0]):
            info = zipfile.ZipInfo(filename=path_in_zip)
            # fixed timestamp for determinism: 1980-01-01
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, b)
    buf.seek(0)

    summary = {
        "schema": "shams.reviewer_packet.summary.v1",
        "n_files": len(manifest_rows),
        "manifest": packet_manifest,
    }
    return buf.getvalue(), summary
