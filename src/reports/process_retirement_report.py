"""Independence Phase 4.1 — scoped PROCESS retirement evidence report.

Assembles **evidence-backed, domain-scoped** coverage statements for which
study domains SHAMS can serve today without depending on UKAEA PROCESS as
feasibility authority — and which domains remain NOT covered.

Honesty (non-negotiable)
------------------------
* Never emits a blanket "PROCESS retired" claim.
* METHOD-ONLY parity ≠ numeric parity.
* Scientific release status is stated as CONDITIONAL until APPROVED evidence exists.
* Domains without champion / dossier / overlay / gate evidence are listed as NOT covered.

L0 risk: none (reads VERSION, docs, benchmarks, and optional champion pack;
does not call or modify frozen physics equations).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPORT_SCHEMA = "shams.process_retirement_report.v1"
# Frozen epoch so checked-in artifacts stay deterministic across regenerations.
_REPORT_EPOCH_UNIX = 0.0

_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_JSON_OUT = (
    _REPO_ROOT / "docs" / "validation" / "reports" / "process_retirement_report.json"
)
DEFAULT_MD_OUT = _REPO_ROOT / "docs" / "PROCESS_RETIREMENT_REPORT.md"

RELEASE_GATE_PATH = (
    _REPO_ROOT / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
)
PARITY_CORPUS_PATH = _REPO_ROOT / "benchmarks" / "parity" / "process_reference_cases.json"
CHAMPION_CASES_PATH = _REPO_ROOT / "benchmarks" / "champions" / "cases.json"
MIGRATION_GUIDE_PATH = _REPO_ROOT / "docs" / "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"
LIMITATIONS_PATH = _REPO_ROOT / "docs" / "LIMITATIONS.md"

# DEMO MATCH overlays shipped in Phase 2 (proxy; OFF by default).
DEMO_MATCH_OVERLAYS: Tuple[Tuple[str, str, str], ...] = (
    ("v410", "magnet_sc_system_authority_v410", "TF/PF/CS superconducting system margins"),
    ("v412", "machine_build_authority_v412", "Radial / machine-build closure"),
    ("v419", "plant_sankey_ledger_authority_v419", "Plant Sankey-grade power ledger"),
    ("v420", "availability_opex_lcoe_authority_v420", "Availability → OPEX / LCOE coupling"),
    ("v421", "bottom_up_costing_authority_v421", "Bottom-up modular CAPEX costing"),
)

# Domains with in-repo evidence that SHAMS can serve as feasibility authority.
# Coverage is SCOPED — never a blanket PROCESS-retirement claim.
_COVERED_DOMAIN_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "domain_id": "tokamak_0d_feasibility",
        "title": "Tokamak 0-D feasibility certification",
        "coverage": "SCOPED_COVERED",
        "process_role": "optional_proposer",
        "summary": (
            "SHAMS frozen L0 evaluator + Design Intent hard set certify whether a "
            "tokamak point design is admissible; champion cases provide citeable packs."
        ),
        "evidence_kinds": ("champion", "version", "ccfs"),
    },
    {
        "domain_id": "no_solution_attribution",
        "title": "NO-SOLUTION mechanism attribution",
        "coverage": "SCOPED_COVERED",
        "process_role": "optional_proposer",
        "summary": (
            "Hard-infeasible runs stamp no_solution_atlas.v1 with dominant mechanism; "
            "infeasible champion cases exercise this path."
        ),
        "evidence_kinds": ("champion", "atlas"),
    },
    {
        "domain_id": "ccfs_propose_only",
        "title": "External optimization propose-only (CCFS)",
        "coverage": "SCOPED_COVERED",
        "process_role": "optional_proposer",
        "summary": (
            "Optimizers (including PROCESS) may propose inputs only; SHAMS re-evaluates "
            "and refuses VERIFIED claims when hard constraints fail."
        ),
        "evidence_kinds": ("ccfs",),
    },
    {
        "domain_id": "process_method_only_parity",
        "title": "PROCESS parity honesty (METHOD-ONLY)",
        "coverage": "SCOPED_COVERED",
        "process_role": "legacy_reproduce_when_mfile_available",
        "summary": (
            "Hashed METHOD-ONLY delta dossiers record SHAMS side + mapping assumptions; "
            "PROCESS numeric KPIs remain null until a lab lands a licensed MFILE."
        ),
        "evidence_kinds": ("parity",),
        "limitations": (
            "METHOD-ONLY is not numeric parity. Do not claim PROCESS KPI agreement.",
        ),
    },
    {
        "domain_id": "plant_kpi_honesty",
        "title": "Plant KPI honesty watermark",
        "coverage": "SCOPED_COVERED",
        "process_role": "optional_proposer",
        "summary": (
            "Healthy Pe_net / COE / LCOE are watermarked when hard-infeasible "
            "(plant_kpi_honesty.v1)."
        ),
        "evidence_kinds": ("plant_kpi",),
    },
    {
        "domain_id": "demo_match_overlays_proxy",
        "title": "DEMO MATCH engineering overlays (proxy)",
        "coverage": "PROXY_OVERLAY",
        "process_role": "optional_proposer",
        "summary": (
            "Versioned MATCH overlays v410/v412/v419/v420/v421 provide magnet, build, "
            "Sankey, availability–OPEX–LCOE, and bottom-up costing narratives (OFF by default)."
        ),
        "evidence_kinds": ("overlay",),
        "limitations": (
            "Overlays are PROXY-labeled engineering coverage — not bankable cost models "
            "and not PROCESS MFILE clones.",
        ),
    },
    {
        "domain_id": "process_migration_path",
        "title": "PROCESS → SHAMS migration path",
        "coverage": "SCOPED_COVERED",
        "process_role": "handoff_documented",
        "summary": (
            "Community migration guide maps IN.DAT→PointInputs, MFILE→artifacts, "
            "and CCFS propose-only citation practice."
        ),
        "evidence_kinds": ("migration",),
    },
    {
        "domain_id": "scientific_release_conditional",
        "title": "Scientific release readiness (CONDITIONAL)",
        "coverage": "SCOPED_COVERED",
        "process_role": "n_a",
        "summary": (
            "Phase 1.4 release gate verdict is CONDITIONAL with documented limitations; "
            "APPROVED / Zenodo DOI path is documented but not claimed."
        ),
        "evidence_kinds": ("release_gate", "limitations"),
        "limitations": (
            "Release status is CONDITIONAL — not APPROVED.",
        ),
    },
)

# Explicit NOT-covered domains (must appear in every report).
_NOT_COVERED_DOMAIN_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "domain_id": "process_numeric_parity",
        "title": "PROCESS numeric KPI parity (MFILE-backed)",
        "coverage": "NOT_COVERED",
        "process_role": "still_needed_for_numeric_compare",
        "summary": (
            "No licensed PROCESS MFILE / OUT.DAT extract is in-repo. Corpus stays "
            "METHOD-ONLY until a lab contributes provenance-tagged numerics."
        ),
        "why_not": "Missing licensed PROCESS reference KPIs.",
    },
    {
        "domain_id": "stellarator_ife",
        "title": "Stellarator / IFE systems studies",
        "coverage": "NOT_COVERED",
        "process_role": "out_of_scope",
        "summary": "Outside SHAMS tokamak 0-D mission (IGNORE unless explicitly requested).",
        "why_not": "Mission scope — not a tokamak 0-D feasibility domain.",
    },
    {
        "domain_id": "bankable_cost_coe",
        "title": "Bankable / institutional cost & COE authority",
        "coverage": "NOT_COVERED",
        "process_role": "still_needed_or_specialist_tools",
        "summary": (
            "v421 is a transparent modular CAPEX proxy, not a bankable cost model; "
            "do not treat it as Generomak/PROCESS cost truth."
        ),
        "why_not": "Economics overlays remain PROXY; no institutional cost validation pack.",
    },
    {
        "domain_id": "neutrals_edge_physics",
        "title": "Neutrals / edge / scrape-off detailed physics",
        "coverage": "NOT_COVERED",
        "process_role": "specialist_codes",
        "summary": "Not present as a SHAMS frozen-truth domain.",
        "why_not": "Missing physics coverage in SHAMS L0 / authorities.",
    },
    {
        "domain_id": "approved_zenodo_doi",
        "title": "APPROVED scientific release + Zenodo DOI",
        "coverage": "NOT_COVERED",
        "process_role": "n_a",
        "summary": (
            "Archival checklist and packaging exist; DOI is not minted and APPROVED "
            "verdict is not claimed while CONDITIONAL waivers remain."
        ),
        "why_not": "Release verdict remains CONDITIONAL; no DOI minted.",
    },
    {
        "domain_id": "full_process_cli_breadth",
        "title": "Full PROCESS-class coupled plant CLI breadth",
        "coverage": "NOT_COVERED",
        "process_role": "still_leads_for_breadth",
        "summary": (
            "SHAMS serves feasibility authority + selective MATCH overlays; it does not "
            "clone PROCESS's full mutable megamodel / VaryRun operational lore."
        ),
        "why_not": "Independence ≠ feature-count clone; breadth remains selective MATCH.",
    },
)

_FORBIDDEN_BLANKET_PATTERNS = (
    re.compile(r"\bprocess\s+is\s+retired\b", re.I),
    re.compile(r"\bprocess\s+has\s+been\s+retired\b", re.I),
    re.compile(r"\bprocess\s+retired\b(?!\s+claim)", re.I),
)


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


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_shams_version(repo_root: Optional[Path] = None) -> str:
    root = repo_root or _REPO_ROOT
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def _file_anchor(path: Path, *, label: str, repo_root: Path) -> Dict[str, Any]:
    rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    exists = path.is_file()
    row: Dict[str, Any] = {
        "label": label,
        "path": rel,
        "exists": exists,
    }
    if exists:
        row["sha256"] = sha256_file(path)
        row["bytes"] = path.stat().st_size
    else:
        row["sha256"] = None
        row["bytes"] = 0
    return row


def _parse_release_verdict(text: str) -> str:
    m = re.search(r"Release verdict:\*\*\s*\*\*([A-Z]+)\*\*", text)
    if m:
        return m.group(1)
    if re.search(r"\bCONDITIONAL\b", text):
        return "CONDITIONAL"
    if re.search(r"\bAPPROVED\b", text) and "CONDITIONAL" not in text:
        return "APPROVED"
    return "UNKNOWN"


def _load_parity_evidence(repo_root: Path) -> Dict[str, Any]:
    corpus_path = repo_root / "benchmarks" / "parity" / "process_reference_cases.json"
    anchor = _file_anchor(corpus_path, label="parity_corpus", repo_root=repo_root)
    dossiers: List[Dict[str, Any]] = []
    corpus_status = "MISSING"
    cases_meta: List[Dict[str, Any]] = []
    hash_verify_ok = False
    if corpus_path.is_file():
        try:
            from parity_harness.process_corpus import (  # type: ignore
                load_process_reference_corpus,
                verify_corpus_dossier_hashes,
            )
        except ImportError:  # pragma: no cover
            from src.parity_harness.process_corpus import (
                load_process_reference_corpus,
                verify_corpus_dossier_hashes,
            )

        raw = load_process_reference_corpus(corpus_path)
        corpus_status = str(raw.get("corpus_status") or "UNKNOWN")
        verify = verify_corpus_dossier_hashes(raw)
        hash_verify_ok = bool(verify.get("ok"))
        verify_by_id = {
            str(row.get("case_id") or ""): row for row in (verify.get("cases") or [])
        }
        for case in raw.get("cases") or []:
            if not isinstance(case, dict):
                continue
            cid = str(case.get("case_id") or "")
            dd = case.get("delta_dossier") or {}
            rel = str(dd.get("path") or "").replace("\\", "/")
            declared = str(dd.get("sha256") or "")
            vrow = verify_by_id.get(cid) or {}
            dossiers.append(
                {
                    "case_id": cid,
                    "dossier_status": str(case.get("dossier_status") or ""),
                    "path": rel,
                    "declared_sha256": declared,
                    "file_sha256": str(vrow.get("actual") or declared or "") or None,
                    "hash_match": bool(vrow.get("match")),
                }
            )
            cases_meta.append(
                {
                    "case_id": cid,
                    "dossier_status": str(case.get("dossier_status") or ""),
                    "label": str(case.get("label") or ""),
                }
            )
    return {
        "corpus": anchor,
        "corpus_status": corpus_status,
        "cases": cases_meta,
        "dossiers": dossiers,
        "dossier_hashes_ok": hash_verify_ok,
        "numeric_parity_available": corpus_status == "NUMERIC",
    }


def _load_champion_evidence(repo_root: Path, *, evaluate: bool) -> Dict[str, Any]:
    cases_path = repo_root / "benchmarks" / "champions" / "cases.json"
    cases_anchor = _file_anchor(cases_path, label="champion_cases_json", repo_root=repo_root)
    case_rows: List[Dict[str, Any]] = []
    pack_sha: Optional[str] = None
    n_cases = 0
    n_feasible = 0
    n_infeasible = 0

    if evaluate and cases_path.is_file():
        try:
            from studies.champion_cases import run_all_champions  # type: ignore
        except ImportError:  # pragma: no cover
            from src.studies.champion_cases import run_all_champions

        pack = run_all_champions(cases_path=cases_path, created_unix=_REPORT_EPOCH_UNIX)
        pack_sha = str(pack.get("pack_sha256") or "")
        n_cases = int(pack.get("n_cases") or 0)
        n_feasible = int(pack.get("n_hard_feasible") or 0)
        n_infeasible = int(pack.get("n_infeasible") or 0)
        for s in pack.get("cases") or []:
            case_rows.append(
                {
                    "case_id": str(s.get("case_id") or ""),
                    "title": str(s.get("title") or ""),
                    "hard_feasible": bool(s.get("hard_feasible")),
                    "citation_sha256": str(s.get("citation_sha256") or ""),
                    "dominant_mechanism": s.get("dominant_mechanism"),
                    "dominant_constraint": s.get("dominant_constraint"),
                    "has_no_solution_atlas": bool(
                        isinstance(s.get("no_solution_atlas"), dict)
                        and s["no_solution_atlas"].get("schema") == "no_solution_atlas.v1"
                    ),
                }
            )
    elif cases_path.is_file():
        raw = json.loads(cases_path.read_text(encoding="utf-8"))
        for cid, body in sorted(raw.items(), key=lambda kv: str(kv[0])):
            if cid in ("README", "schema", "_meta") or not isinstance(body, dict):
                continue
            if body.get("enabled") is False:
                continue
            case_rows.append(
                {
                    "case_id": str(cid),
                    "title": str(body.get("title") or ""),
                    "hard_feasible": None,
                    "citation_sha256": None,
                    "expect_hard_feasible": body.get("expect_hard_feasible"),
                    "has_no_solution_atlas": None,
                }
            )
        n_cases = len(case_rows)

    return {
        "cases_file": cases_anchor,
        "evaluated": bool(evaluate and pack_sha),
        "pack_sha256": pack_sha,
        "n_cases": n_cases,
        "n_hard_feasible": n_feasible,
        "n_infeasible": n_infeasible,
        "cases": case_rows,
    }


def _overlay_evidence(repo_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    analysis_dirs = [repo_root / "analysis", repo_root / "src" / "analysis"]
    for tag, mod_name, title in DEMO_MATCH_OVERLAYS:
        found: Optional[Path] = None
        for d in analysis_dirs:
            cand = d / f"{mod_name}.py"
            if cand.is_file():
                found = cand
                break
        if found is None:
            # Also search recursively once
            for d in analysis_dirs:
                if d.is_dir():
                    hits = list(d.rglob(f"{mod_name}.py"))
                    if hits:
                        found = hits[0]
                        break
        if found is not None:
            rows.append(
                {
                    "overlay_id": tag,
                    "module": mod_name,
                    "title": title,
                    **_file_anchor(found, label=mod_name, repo_root=repo_root),
                    "default": "OFF",
                    "maturity": "PROXY",
                }
            )
        else:
            rows.append(
                {
                    "overlay_id": tag,
                    "module": mod_name,
                    "title": title,
                    "path": None,
                    "exists": False,
                    "sha256": None,
                    "default": "OFF",
                    "maturity": "PROXY",
                }
            )
    return rows


def _assert_no_blanket_retirement(text: str) -> None:
    """Raise if text contains an unqualified PROCESS-retired assertion."""
    plain = re.sub(r"[*_`]", "", text)
    lower = plain.lower()
    # Allowed: explicit negations near "retired"
    for pat in _FORBIDDEN_BLANKET_PATTERNS:
        for m in pat.finditer(plain):
            start = max(0, m.start() - 64)
            end = min(len(lower), m.end() + 48)
            window_before = lower[start : m.start()]
            window_after = lower[m.end() : end]
            if any(
                neg in window_before
                for neg in (
                    "does not claim",
                    "do not claim",
                    "never claim",
                    "not claim",
                    "no blanket",
                    "without scoped",
                    "not retired",
                    "never emits",
                    "refuses",
                    "anti-overclaim",
                    "forbidden",
                    "blanket",  # "Blanket PROCESS retired? NO" question form
                )
            ):
                continue
            # Question / denial forms: "... retired? NO" or "... retired: false"
            if window_after.lstrip().startswith("?") or re.match(
                r"\s*[:?]?\s*(no|false|never)\b", window_after
            ):
                continue
            # Also allow "process_retired_claimed": false style JSON keys in prose
            if "process_retired_claimed" in window_before or "process-retired claim" in window_before:
                continue
            raise ValueError(
                f"Unqualified PROCESS-retirement language near: {plain[m.start() - 20 : m.end() + 20]!r}"
            )


def validate_report_honesty(report: Dict[str, Any]) -> List[str]:
    """Return honesty violations (empty = OK)."""
    issues: List[str] = []
    honesty = report.get("honesty") if isinstance(report.get("honesty"), dict) else {}
    verdict = report.get("verdict") if isinstance(report.get("verdict"), dict) else {}

    if honesty.get("process_retired_claimed") is not False:
        issues.append("honesty.process_retired_claimed must be false")
    if honesty.get("numeric_parity_claimed") is not False:
        issues.append("honesty.numeric_parity_claimed must be false")
    if honesty.get("invented_mfile") is not False:
        issues.append("honesty.invented_mfile must be false")
    if verdict.get("blanket_process_retired") is not False:
        issues.append("verdict.blanket_process_retired must be false")

    release = str(verdict.get("release_status") or "")
    if release != "CONDITIONAL":
        # Allow APPROVED only if evidence explicitly says so — currently must be CONDITIONAL
        if release == "APPROVED":
            issues.append("release_status APPROVED is not evidenced; keep CONDITIONAL")
        elif release != "CONDITIONAL":
            issues.append(f"release_status must be CONDITIONAL (got {release!r})")

    parity = str(verdict.get("parity_corpus_status") or "")
    if parity == "METHOD-ONLY" and honesty.get("numeric_parity_claimed"):
        issues.append("METHOD-ONLY corpus cannot claim numeric parity")

    domains = report.get("domains") if isinstance(report.get("domains"), list) else []
    not_covered = [
        d for d in domains if isinstance(d, dict) and d.get("coverage") == "NOT_COVERED"
    ]
    if len(not_covered) < 3:
        issues.append("report must list multiple NOT_COVERED domains explicitly")

    required_not = {s["domain_id"] for s in _NOT_COVERED_DOMAIN_SPECS}
    present_not = {str(d.get("domain_id")) for d in not_covered}
    missing = sorted(required_not - present_not)
    if missing:
        issues.append(f"missing required NOT_COVERED domains: {missing}")

    # Overclaim scan on embedded summary strings
    blob = canonical_dumps(report)
    try:
        _assert_no_blanket_retirement(blob)
    except ValueError as exc:
        issues.append(str(exc))

    return issues


def build_process_retirement_report(
    *,
    repo_root: Optional[Path] = None,
    evaluate_champions: bool = True,
    created_unix: float = _REPORT_EPOCH_UNIX,
) -> Dict[str, Any]:
    """Build a deterministic scoped retirement evidence report.

    Parameters
    ----------
    evaluate_champions:
        When True (default), run champion pack to attach citation SHA-256 hashes.
    """
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    version = read_shams_version(root)
    version_path = root / "VERSION"

    release_path = (
        root / "docs" / "validation" / "reports" / "scientific_release_readiness_20260716.md"
    )
    release_anchor = _file_anchor(release_path, label="scientific_release_gate", repo_root=root)
    release_status = "UNKNOWN"
    if release_path.is_file():
        release_status = _parse_release_verdict(release_path.read_text(encoding="utf-8"))

    parity = _load_parity_evidence(root)
    champions = _load_champion_evidence(root, evaluate=evaluate_champions)
    overlays = _overlay_evidence(root)
    migration = _file_anchor(
        root / "docs" / "PROCESS_TO_SHAMS_MIGRATION_GUIDE.md",
        label="migration_guide",
        repo_root=root,
    )
    limitations = _file_anchor(
        root / "docs" / "LIMITATIONS.md",
        label="limitations",
        repo_root=root,
    )
    ccfs_test = _file_anchor(
        root / "tests" / "test_ccfs_verified_hard_gate.py",
        label="ccfs_hard_gate_test",
        repo_root=root,
    )
    atlas_test = _file_anchor(
        root / "tests" / "test_no_solution_atlas.py",
        label="no_solution_atlas_test",
        repo_root=root,
    )
    plant_kpi_test = _file_anchor(
        root / "tests" / "test_plant_kpi_honesty.py",
        label="plant_kpi_honesty_test",
        repo_root=root,
    )

    evidence_index: Dict[str, Any] = {
        "version": {
            "value": version,
            **_file_anchor(version_path, label="VERSION", repo_root=root),
        },
        "parity": parity,
        "champions": champions,
        "overlays": overlays,
        "release_gate": {**release_anchor, "verdict": release_status},
        "migration_guide": migration,
        "limitations": limitations,
        "ccfs_hard_gate_test": ccfs_test,
        "no_solution_atlas_test": atlas_test,
        "plant_kpi_honesty_test": plant_kpi_test,
    }

    def _evidence_refs(kinds: Sequence[str]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for kind in kinds:
            if kind == "champion":
                refs.append(
                    {
                        "kind": "champion",
                        "pack_sha256": champions.get("pack_sha256"),
                        "n_cases": champions.get("n_cases"),
                        "cases_path": (champions.get("cases_file") or {}).get("path"),
                        "case_citation_sha256": [
                            {
                                "case_id": c.get("case_id"),
                                "citation_sha256": c.get("citation_sha256"),
                            }
                            for c in champions.get("cases") or []
                            if c.get("citation_sha256")
                        ],
                    }
                )
            elif kind == "parity":
                refs.append(
                    {
                        "kind": "parity",
                        "corpus_status": parity.get("corpus_status"),
                        "corpus_sha256": (parity.get("corpus") or {}).get("sha256"),
                        "dossiers": parity.get("dossiers"),
                    }
                )
            elif kind == "overlay":
                refs.append(
                    {
                        "kind": "overlay",
                        "overlays": [
                            {
                                "overlay_id": o.get("overlay_id"),
                                "module": o.get("module"),
                                "sha256": o.get("sha256"),
                                "exists": o.get("exists"),
                            }
                            for o in overlays
                        ],
                    }
                )
            elif kind == "release_gate":
                refs.append(
                    {
                        "kind": "release_gate",
                        "verdict": release_status,
                        "path": release_anchor.get("path"),
                        "sha256": release_anchor.get("sha256"),
                    }
                )
            elif kind == "migration":
                refs.append(
                    {
                        "kind": "migration",
                        "path": migration.get("path"),
                        "sha256": migration.get("sha256"),
                    }
                )
            elif kind == "limitations":
                refs.append(
                    {
                        "kind": "limitations",
                        "path": limitations.get("path"),
                        "sha256": limitations.get("sha256"),
                    }
                )
            elif kind == "ccfs":
                refs.append(
                    {
                        "kind": "ccfs",
                        "path": ccfs_test.get("path"),
                        "sha256": ccfs_test.get("sha256"),
                    }
                )
            elif kind == "atlas":
                refs.append(
                    {
                        "kind": "atlas",
                        "path": atlas_test.get("path"),
                        "sha256": atlas_test.get("sha256"),
                        "champion_infeasible_with_atlas": [
                            c.get("case_id")
                            for c in champions.get("cases") or []
                            if c.get("has_no_solution_atlas")
                        ],
                    }
                )
            elif kind == "plant_kpi":
                refs.append(
                    {
                        "kind": "plant_kpi",
                        "path": plant_kpi_test.get("path"),
                        "sha256": plant_kpi_test.get("sha256"),
                    }
                )
            elif kind == "version":
                refs.append({"kind": "version", "value": version})
        return refs

    domains: List[Dict[str, Any]] = []
    for spec in _COVERED_DOMAIN_SPECS:
        domains.append(
            {
                "domain_id": spec["domain_id"],
                "title": spec["title"],
                "coverage": spec["coverage"],
                "process_role": spec["process_role"],
                "summary": spec["summary"],
                "evidence": _evidence_refs(spec.get("evidence_kinds") or ()),
                "limitations": list(spec.get("limitations") or ()),
            }
        )
    for spec in _NOT_COVERED_DOMAIN_SPECS:
        domains.append(
            {
                "domain_id": spec["domain_id"],
                "title": spec["title"],
                "coverage": "NOT_COVERED",
                "process_role": spec["process_role"],
                "summary": spec["summary"],
                "why_not_covered": spec["why_not"],
                "evidence": [],
                "limitations": [],
            }
        )

    domains.sort(key=lambda d: (0 if d["coverage"] != "NOT_COVERED" else 1, str(d["domain_id"])))

    covered_ids = [
        d["domain_id"]
        for d in domains
        if d["coverage"] in ("SCOPED_COVERED", "PROXY_OVERLAY")
    ]
    not_covered_ids = [d["domain_id"] for d in domains if d["coverage"] == "NOT_COVERED"]

    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "shams_version": version,
        "generated_at_unix": float(created_unix),
        "ticket": "4.1",
        "independence_phase": 4,
        "verdict": {
            "blanket_process_retired": False,
            "release_status": release_status if release_status != "UNKNOWN" else "CONDITIONAL",
            "parity_corpus_status": parity.get("corpus_status") or "METHOD-ONLY",
            "summary": (
                "SHAMS can serve the SCOPED_COVERED / PROXY_OVERLAY domains listed below "
                "as a feasibility authority with citeable VERSION + SHA-256 evidence. "
                "PROCESS is not retired. Domains under NOT_COVERED still need PROCESS, "
                "specialist codes, or are out of scope."
            ),
        },
        "honesty": {
            "process_retired_claimed": False,
            "numeric_parity_claimed": False,
            "invented_mfile": False,
            "method_only_means_no_numeric_parity": True,
            "conditional_release_stated": True,
            "statements": [
                "Do not claim PROCESS is retired.",
                "METHOD-ONLY parity does not authorize numeric PROCESS KPI claims.",
                "Scientific release status is CONDITIONAL — not APPROVED.",
                "Domains without evidence are listed as NOT_COVERED.",
                "Optimizers (including PROCESS) propose inputs only; SHAMS certifies.",
            ],
        },
        "coverage_summary": {
            "scoped_covered_or_proxy": covered_ids,
            "not_covered": not_covered_ids,
            "n_scoped_covered_or_proxy": len(covered_ids),
            "n_not_covered": len(not_covered_ids),
        },
        "domains": domains,
        "evidence_index": evidence_index,
    }

    # Hash excludes report_sha256 itself
    report["report_sha256"] = sha256_hex(report)

    issues = validate_report_honesty(report)
    if issues:
        raise ValueError("process_retirement_report honesty gate failed: " + "; ".join(issues))

    return report


def render_process_retirement_markdown(report: Dict[str, Any]) -> str:
    """Render a human-readable markdown document from a report dict."""
    v = report.get("verdict") or {}
    h = report.get("honesty") or {}
    cov = report.get("coverage_summary") or {}
    lines: List[str] = [
        "# SHAMS Scoped PROCESS Retirement Evidence Report",
        "",
        f"**Schema:** `{report.get('schema')}`  ",
        f"**SHAMS VERSION:** `{report.get('shams_version')}`  ",
        f"**Report SHA-256:** `{report.get('report_sha256')}`  ",
        f"**Independence ticket:** {report.get('ticket')} (Phase {report.get('independence_phase')})",
        "",
        "## Verdict (scoped — not a blanket claim)",
        "",
        f"- **Blanket PROCESS-retirement claim?** **{'YES — INVALID' if v.get('blanket_process_retired') else 'NO'}**",
        f"- **Scientific release status:** **{v.get('release_status')}**",
        f"- **PROCESS parity corpus:** **{v.get('parity_corpus_status')}**",
        f"- **Summary:** {v.get('summary')}",
        "",
        "## Honesty constraints",
        "",
    ]
    for stmt in h.get("statements") or []:
        lines.append(f"- {stmt}")
    lines.extend(
        [
            "",
            f"- `process_retired_claimed`: `{h.get('process_retired_claimed')}`",
            f"- `numeric_parity_claimed`: `{h.get('numeric_parity_claimed')}`",
            f"- `invented_mfile`: `{h.get('invented_mfile')}`",
            "",
            "## Domain coverage table",
            "",
            "| Domain ID | Title | Coverage | PROCESS role |",
            "|-----------|-------|----------|--------------|",
        ]
    )
    for d in report.get("domains") or []:
        lines.append(
            f"| `{d.get('domain_id')}` | {d.get('title')} | **{d.get('coverage')}** | {d.get('process_role')} |"
        )

    lines.extend(
        [
            "",
            f"**Scoped covered / proxy count:** {cov.get('n_scoped_covered_or_proxy')}  ",
            f"**Explicitly NOT covered count:** {cov.get('n_not_covered')}",
            "",
            "## Covered / proxy domains (evidence-backed)",
            "",
        ]
    )
    for d in report.get("domains") or []:
        if d.get("coverage") == "NOT_COVERED":
            continue
        lines.append(f"### `{d.get('domain_id')}` — {d.get('title')}")
        lines.append("")
        lines.append(str(d.get("summary") or ""))
        lines.append("")
        lines.append(f"- Coverage: **{d.get('coverage')}**")
        lines.append(f"- PROCESS role: `{d.get('process_role')}`")
        for lim in d.get("limitations") or []:
            lines.append(f"- Limitation: {lim}")
        ev_kinds = [str((e or {}).get("kind") or "") for e in (d.get("evidence") or [])]
        if ev_kinds:
            lines.append(f"- Evidence kinds: {', '.join(ev_kinds)}")
        lines.append("")

    lines.extend(["## NOT covered domains (explicit)", ""])
    for d in report.get("domains") or []:
        if d.get("coverage") != "NOT_COVERED":
            continue
        lines.append(f"### `{d.get('domain_id')}` — {d.get('title')}")
        lines.append("")
        lines.append(str(d.get("summary") or ""))
        lines.append("")
        lines.append(f"- Why not covered: {d.get('why_not_covered')}")
        lines.append(f"- PROCESS role: `{d.get('process_role')}`")
        lines.append("")

    # Evidence index highlights
    ei = report.get("evidence_index") or {}
    champs = ei.get("champions") or {}
    parity = ei.get("parity") or {}
    lines.extend(
        [
            "## Evidence index highlights",
            "",
            f"- VERSION file SHA-256: `{(ei.get('version') or {}).get('sha256')}`",
            f"- Champion pack SHA-256: `{champs.get('pack_sha256')}` "
            f"({champs.get('n_cases')} cases; "
            f"{champs.get('n_hard_feasible')} feasible / {champs.get('n_infeasible')} infeasible)",
            f"- Parity corpus status: **{parity.get('corpus_status')}** "
            f"(corpus SHA-256: `{(parity.get('corpus') or {}).get('sha256')}`)",
            "",
        ]
    )
    if champs.get("cases"):
        lines.append("| Champion case | Hard feasible | Citation SHA-256 |")
        lines.append("|---------------|---------------|------------------|")
        for c in champs["cases"]:
            lines.append(
                f"| `{c.get('case_id')}` | {c.get('hard_feasible')} | `{c.get('citation_sha256')}` |"
            )
        lines.append("")

    if parity.get("dossiers"):
        lines.append("| Parity dossier | Status | File SHA-256 | Hash match |")
        lines.append("|----------------|--------|--------------|------------|")
        for d in parity["dossiers"]:
            lines.append(
                f"| `{d.get('case_id')}` | {d.get('dossier_status')} | "
                f"`{d.get('file_sha256')}` | {d.get('hash_match')} |"
            )
        lines.append("")

    overlays = ei.get("overlays") or []
    if overlays:
        lines.append("| Overlay | Module | Exists | SHA-256 |")
        lines.append("|---------|--------|--------|---------|")
        for o in overlays:
            lines.append(
                f"| {o.get('overlay_id')} | `{o.get('module')}` | {o.get('exists')} | `{o.get('sha256')}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## How to cite",
            "",
            "1. Cite SHAMS `VERSION` exactly.",
            "2. Attach this report's `report_sha256` plus relevant champion `citation_sha256` "
            "and/or parity dossier hashes.",
            "3. State release status **CONDITIONAL** and parity status **METHOD-ONLY** unless "
            "newer evidence flips them.",
            "4. **Do not claim PROCESS is retired.** Scope claims to the domain IDs above.",
            "",
            "---",
            "",
            "*Generated by `src/reports/process_retirement_report.py` (Independence Phase 4.1). "
            "L0 frozen truth untouched.*",
            "",
        ]
    )

    md = "\n".join(lines)
    _assert_no_blanket_retirement(md)
    return md


def write_process_retirement_report(
    *,
    repo_root: Optional[Path] = None,
    json_out: Optional[Path] = None,
    md_out: Optional[Path] = None,
    evaluate_champions: bool = True,
) -> Dict[str, Any]:
    """Build report and write JSON + markdown artifacts; return the report dict."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    report = build_process_retirement_report(
        repo_root=root,
        evaluate_champions=evaluate_champions,
    )
    jpath = Path(json_out) if json_out is not None else (
        root / "docs" / "validation" / "reports" / "process_retirement_report.json"
    )
    mpath = Path(md_out) if md_out is not None else (root / "docs" / "PROCESS_RETIREMENT_REPORT.md")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    mpath.write_text(render_process_retirement_markdown(report), encoding="utf-8")
    report["_written"] = {
        "json": str(jpath.relative_to(root)).replace("\\", "/"),
        "markdown": str(mpath.relative_to(root)).replace("\\", "/"),
    }
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Generate scoped PROCESS retirement evidence report")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--json-out", type=Path, default=None)
    p.add_argument("--md-out", type=Path, default=None)
    p.add_argument(
        "--skip-champions",
        action="store_true",
        help="Do not evaluate champion pack (citations omitted)",
    )
    args = p.parse_args(list(argv) if argv is not None else None)
    report = write_process_retirement_report(
        repo_root=args.repo_root,
        json_out=args.json_out,
        md_out=args.md_out,
        evaluate_champions=not args.skip_champions,
    )
    print(f"schema={report['schema']}")
    print(f"shams_version={report['shams_version']}")
    print(f"report_sha256={report['report_sha256']}")
    print(f"blanket_process_retired={report['verdict']['blanket_process_retired']}")
    print(f"release_status={report['verdict']['release_status']}")
    print(f"written_json={report.get('_written', {}).get('json')}")
    print(f"written_md={report.get('_written', {}).get('markdown')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
