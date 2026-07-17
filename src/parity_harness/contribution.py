"""Independence Phase 4.3 — PROCESS parity contribution intake.

External labs holding licensed PROCESS IN.DAT / MFILE extracts can submit a
structured contribution package. SHAMS validates honesty (NUMERIC only when
real PROCESS KPIs + provenance are attached; otherwise METHOD-ONLY) and builds
a hashed delta dossier via the existing corpus / delta_dossier pipeline.

L0 risk: none — evaluate() is called only as in process_corpus (propose inputs;
frozen Evaluator). Never invents MFILE numbers.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .delta_dossier import has_numeric_process_kpis
from .process_corpus import (
    ALLOWED_STATUS,
    build_case_delta_dossier,
    dossier_hash_payload,
    sha256_hex,
)

SUBMISSION_SCHEMA = "shams.parity_contribution.v1"
RECEIPT_SCHEMA = "shams.parity_contribution_receipt.v1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_PATH = (
    _REPO_ROOT / "benchmarks" / "parity" / "contributions" / "submission_template.json"
)
DEFAULT_OUTBOX = _REPO_ROOT / "benchmarks" / "parity" / "contributions" / "outbox"

_REQUIRED_FIELDS = (
    "schema",
    "case_id",
    "label",
    "requested_status",
    "inputs",
    "process_reference",
    "provenance",
    "license_attestation",
)

_CASE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def _canon_for_hash(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _canon_for_hash(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canon_for_hash(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    return obj


def canonical_dumps(obj: Any) -> str:
    return json.dumps(_canon_for_hash(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_submission(path: Path) -> Dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("parity contribution submission must be a JSON object")
    return raw


def example_method_only_submission() -> Dict[str, Any]:
    """Deterministic example — METHOD-ONLY, no invented PROCESS KPIs."""
    return {
        "schema": SUBMISSION_SCHEMA,
        "case_id": "lab_example_method_only_001",
        "label": "Example lab contribution (METHOD-ONLY)",
        "requested_status": "METHOD-ONLY",
        "intent": "reactor",
        "inputs": {
            "R0_m": 2.6,
            "a_m": 0.9,
            "Bt_T": 12.0,
            "Ip_MA": 10.0,
            "kappa": 2.0,
            "delta": 0.35,
            "Ti_keV": 18.0,
            "Paux_MW": 50.0,
            "fG": 0.28,
            "include_profile_family_v358": True,
        },
        "process_reference": {
            "Q_plasma": None,
            "P_fus_MW": None,
            "Pe_net_MW": None,
            "P_aux_MW": None,
        },
        "provenance": {
            "submitter": "example_lab",
            "process_reference_source": None,
            "process_reference_reason": (
                "No licensed MFILE attached; METHOD-ONLY contribution for mapping review."
            ),
            "shams_inputs_source": "lab-supplied PointInputs (example)",
            "notes": "Replace with real lab metadata before submitting.",
        },
        "license_attestation": {
            "holds_process_license_or_permission": False,
            "may_share_extracts_with_shams_maintainers": False,
            "statement": (
                "METHOD-ONLY submission: no PROCESS numeric extracts attached. "
                "Submitter asserts SHAMS inputs are theirs to share."
            ),
        },
        "honesty": {
            "no_invented_mfile": True,
            "statement": (
                "NUMERIC status is refused unless real PROCESS KPIs and provenance are attached."
            ),
        },
    }


def validate_submission(submission: Dict[str, Any]) -> List[str]:
    """Return honesty / schema violations (empty = OK).

    NUMERIC is allowed only when:
    * requested_status == NUMERIC
    * process_reference has at least one real KPI
    * provenance.process_reference_source is set
    * license attestation affirms permission to share extracts
    """
    issues: List[str] = []
    if not isinstance(submission, dict):
        return ["submission must be a JSON object"]

    schema = str(submission.get("schema") or "")
    if schema != SUBMISSION_SCHEMA:
        issues.append(f"schema must be {SUBMISSION_SCHEMA!r} (got {schema!r})")

    for key in _REQUIRED_FIELDS:
        if key not in submission:
            issues.append(f"missing required field: {key}")

    cid = str(submission.get("case_id") or "")
    if not cid or not _CASE_ID_RE.match(cid):
        issues.append(
            "case_id must match ^[a-z][a-z0-9_]{2,63}$ "
            f"(got {cid!r})"
        )

    status = str(submission.get("requested_status") or "").strip()
    if status not in ALLOWED_STATUS:
        issues.append(f"requested_status must be METHOD-ONLY or NUMERIC (got {status!r})")

    inputs = submission.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        issues.append("inputs must be a non-empty PointInputs-compatible object")

    pref = submission.get("process_reference")
    if pref is None:
        pref = {}
    if not isinstance(pref, dict):
        issues.append("process_reference must be an object")
        pref = {}

    prov = submission.get("provenance") if isinstance(submission.get("provenance"), dict) else {}
    lic = (
        submission.get("license_attestation")
        if isinstance(submission.get("license_attestation"), dict)
        else {}
    )

    if status == "METHOD-ONLY":
        if has_numeric_process_kpis(pref):
            issues.append(
                "METHOD-ONLY forbids non-null PROCESS KPIs "
                "(do not invent MFILE numbers; use NUMERIC with provenance)"
            )
        # Soft check: license may be false for METHOD-ONLY
    elif status == "NUMERIC":
        if not has_numeric_process_kpis(pref):
            issues.append(
                "NUMERIC requires at least one non-null PROCESS KPI from a real MFILE/OUT.DAT extract"
            )
        src = prov.get("process_reference_source")
        if not src:
            issues.append("NUMERIC requires provenance.process_reference_source")
        if lic.get("holds_process_license_or_permission") is not True:
            issues.append(
                "NUMERIC requires license_attestation.holds_process_license_or_permission=true"
            )
        if lic.get("may_share_extracts_with_shams_maintainers") is not True:
            issues.append(
                "NUMERIC requires license_attestation.may_share_extracts_with_shams_maintainers=true"
            )

    honesty = submission.get("honesty") if isinstance(submission.get("honesty"), dict) else {}
    if honesty.get("no_invented_mfile") is False:
        issues.append("honesty.no_invented_mfile must not be false")

    # Refuse fabricated NUMERIC upgrade without evidence
    if status == "NUMERIC" and honesty.get("no_invented_mfile") is not True:
        issues.append("NUMERIC submissions must set honesty.no_invented_mfile=true")

    return issues


def submission_to_corpus_case(submission: Dict[str, Any]) -> Dict[str, Any]:
    """Map a validated contribution onto the process.parity_cases.v2 case shape."""
    status = str(submission.get("requested_status") or "METHOD-ONLY").strip()
    cid = str(submission["case_id"])
    pref = submission.get("process_reference") if isinstance(submission.get("process_reference"), dict) else {}
    prov = submission.get("provenance") if isinstance(submission.get("provenance"), dict) else {}
    return {
        "case_id": cid,
        "label": str(submission.get("label") or cid),
        "intent": str(submission.get("intent") or "reactor"),
        "dossier_status": status,
        "inputs": dict(submission.get("inputs") or {}),
        "process_reference": dict(pref),
        "provenance": dict(prov),
        "delta_dossier": {
            "path": f"benchmarks/parity/dossiers/{cid}_delta_dossier.json",
            "sha256": "",  # filled after build
        },
        "contribution": {
            "schema": SUBMISSION_SCHEMA,
            "license_attestation": submission.get("license_attestation"),
        },
    }


def process_contribution(
    submission: Dict[str, Any],
    *,
    repo_root: Optional[Path] = None,
    out_dir: Optional[Path] = None,
    write: bool = True,
    evaluate: bool = True,
) -> Dict[str, Any]:
    """Validate submission, build delta dossier, optionally write receipt + dossier.

    Returns a receipt dict (``shams.parity_contribution_receipt.v1``).
    """
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    issues = validate_submission(submission)
    if issues:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "accepted": False,
            "case_id": str(submission.get("case_id") or ""),
            "requested_status": str(submission.get("requested_status") or ""),
            "issues": issues,
            "dossier_status": None,
            "dossier_sha256": None,
            "dossier_path": None,
            "honesty": {
                "no_invented_mfile": True,
                "numeric_requires_real_kpis": True,
                "process_retired_claimed": False,
            },
        }
        receipt["receipt_sha256"] = sha256_hex(
            {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        )
        return receipt

    case = submission_to_corpus_case(submission)
    # build_case_delta_dossier always classifies from actual KPIs
    if evaluate:
        dossier = build_case_delta_dossier(case, evaluate=True)
    else:
        # Skip Evaluator — still classify honesty from process_reference
        from .delta_dossier import build_delta_dossier, classify_dossier_status, render_delta_dossier_markdown

        pref = case.get("process_reference") if isinstance(case.get("process_reference"), dict) else {}
        status = str(case.get("dossier_status") or "METHOD-ONLY")
        process_payload = dict(pref) if status == "NUMERIC" and has_numeric_process_kpis(pref) else None
        art = {
            "schema_version": "shams_run_artifact.v1",
            "kind": "shams_run_artifact",
            "inputs": case.get("inputs") or {},
            "outputs": {},
            "constraints": [],
            "kpis": {},
            "verdict": "UNEVALUATED",
        }
        dossier = build_delta_dossier(
            case_id=str(case["case_id"]),
            shams_artifact=art,
            process_payload=process_payload,
            mapping_payload=None,
        )
        dossier["dossier_status"] = classify_dossier_status(process_payload)
        if dossier["dossier_status"] == "METHOD-ONLY":
            dossier["has_process_reference"] = False
            dossier.setdefault(
                "honesty",
                {
                    "label": "METHOD-ONLY",
                    "statement": (
                        "No numeric PROCESS reference KPIs were supplied. "
                        "This dossier records SHAMS diagnostics and mapping assumptions only; "
                        "it does not invent MFILE / OUT.DAT values."
                    ),
                },
            )
        dossier["markdown"] = render_delta_dossier_markdown(dossier)

    # Enforce: declared NUMERIC but classifier says METHOD-ONLY → reject
    declared = str(submission.get("requested_status") or "")
    actual = str(dossier.get("dossier_status") or "METHOD-ONLY")
    if declared == "NUMERIC" and actual != "NUMERIC":
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "accepted": False,
            "case_id": case["case_id"],
            "requested_status": declared,
            "issues": [
                "requested NUMERIC but dossier classified METHOD-ONLY "
                "(missing real PROCESS KPIs — no fabricated NUMERIC)"
            ],
            "dossier_status": actual,
            "dossier_sha256": None,
            "dossier_path": None,
            "honesty": {
                "no_invented_mfile": True,
                "numeric_requires_real_kpis": True,
                "process_retired_claimed": False,
            },
        }
        receipt["receipt_sha256"] = sha256_hex(
            {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        )
        return receipt

    digest = sha256_hex(dossier_hash_payload(dossier))
    outbox = Path(out_dir) if out_dir is not None else (root / "benchmarks" / "parity" / "contributions" / "outbox")
    rel_dossier = f"benchmarks/parity/contributions/outbox/{case['case_id']}_delta_dossier.json"
    dossier_path = outbox / f"{case['case_id']}_delta_dossier.json"
    receipt_path = outbox / f"{case['case_id']}_receipt.json"

    if write:
        outbox.mkdir(parents=True, exist_ok=True)
        payload = dict(dossier_hash_payload(dossier))
        payload["sha256"] = digest
        dossier_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        md_path = dossier_path.with_suffix(".md")
        md_path.write_text(str(dossier.get("markdown") or ""), encoding="utf-8")

    receipt: Dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "accepted": True,
        "case_id": case["case_id"],
        "requested_status": declared,
        "dossier_status": actual,
        "dossier_sha256": digest,
        "dossier_path": rel_dossier.replace("\\", "/"),
        "issues": [],
        "shams_version": _read_version(root),
        "honesty": {
            "no_invented_mfile": True,
            "numeric_requires_real_kpis": True,
            "process_retired_claimed": False,
            "statement": (
                "Accepted contribution yields a hashed SHAMS delta dossier. "
                "METHOD-ONLY is valid science. NUMERIC requires lab-supplied KPIs + provenance. "
                "This receipt does not claim PROCESS retired."
            ),
        },
        "next_steps": [
            "Review the delta dossier markdown for SHAMS verdict / blockers.",
            "If NUMERIC: maintainers may promote into benchmarks/parity/process_reference_cases.json after license review.",
            "Cite SHAMS VERSION + dossier SHA-256; do not invent MFILE numbers.",
        ],
    }
    receipt["receipt_sha256"] = sha256_hex(
        {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    )

    if write:
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return receipt


def _read_version(root: Path) -> str:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def write_submission_template(*, path: Optional[Path] = None) -> Path:
    """Write the METHOD-ONLY example template to disk."""
    p = Path(path) if path is not None else DEFAULT_TEMPLATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    body = example_method_only_submission()
    p.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
