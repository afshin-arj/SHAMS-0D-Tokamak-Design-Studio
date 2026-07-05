"""One-shot cleanup: replace user-facing version tags with plain-language labels.

Run: python tools/clean_user_version_tags.py [--write]
Default is dry-run (counts only). Pass --write to apply.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_DIRS = [ROOT / "ui" / "decks", ROOT / "ui_nicegui", ROOT / "ui"]

# Exact string replacements (longest first when sorted by -len)
EXACT: dict[str, str] = {
    "Multi-Objective Feasible Frontier Atlas (v351)": "Multi-Objective Feasible Frontier Atlas",
    "Robust Design Envelope Certification (v352)": "Robust Design Envelope Certification",
    "Regime Maps & Narratives (v324)": "Regime Maps & Narratives",
    "Regulatory Evidence Pack Builder (v387)": "Regulatory Evidence Pack Builder",
    "Global Dominance & Regime (v402)": "Global Dominance & Regime",
    "Regulatory & Reviewer Evidence Packs (v334)": "Regulatory & Reviewer Evidence Packs",
    "Licensing Evidence Tier 2 (v355)": "Licensing Evidence Tier 2",
    "Interoperability contract validator (v326)": "Interoperability contract validator",
    "Magnet Authority — Technology Regime (v328.0)": "Magnet Authority — Technology Regime",
    "Design family governance (v394.0.0)": "Design family governance",
    " Current drive library (v395) — multi-channel mix bookkeeping (certified)": " Current drive library — multi-channel mix bookkeeping (certified)",
    "Maintenance event table (v368)": "Maintenance event table",
    "Deterministic maintenance scheduling closure (v368.0): outage calendar proxy and schedule-dominated availability.": (
        "Deterministic maintenance scheduling closure: outage calendar proxy and schedule-dominated availability."
    ),
    "Availability (v368)": "Schedule-dominated availability",
    "Outage total (v368)": "Outage fraction",
    "Net MWh/y (v368)": "Net electric MWh/y",
    "Single objective (v340 compat)": "Single objective (legacy compat)",
    "Pareto frontier (v405)": "Multi-objective Pareto frontier",
    "Frontier candidates (v405)": "Frontier candidates",
    "Build capsule zip (v2)": "Build run capsule zip",
    "Advanced instruments (Tier 1–4)": "Core advanced instruments",
    "Tier 5–6 instruments (optional)": "Trajectory & counterfactual instruments (optional)",
    "Tier 5–6 instruments": "Trajectory & counterfactual instruments",
    "Download scan artifact (JSON, schema v1)": "Download scan artifact (JSON, replay schema)",
    "Upload a previously exported Scan Lab artifact. SHAMS will auto-upgrade it to schema v1 and restore the Scan Lab state.": (
        "Upload a previously exported Scan Lab artifact. SHAMS will auto-upgrade it to the standard replay schema and restore Scan Lab state."
    ),
    "Visual semantics frozen (Scan Lab v1.0)": "Visual semantics frozen for this Scan Lab release.",
    "Pareto Mode v1.0 - Frozen. Descriptive trade-off cartography only.": (
        "Frozen descriptive trade-off cartography only — no optimization."
    ),
    "Feasibility Boundary Atlas v2": "Feasibility Boundary Atlas (extended)",
    "Build Boundary Atlas v2": "Build extended boundary atlas",
    "Load a SHAMS run artifact and inspect new v50+ artifact sections (constraint ledger, model set, standardized tables).": (
        "Load a SHAMS run artifact and inspect extended artifact sections (constraint ledger, model set, standardized tables)."
    ),
    "Export **schema v1 artifact** for replay. Enable **Include compact outputs** ": (
        "Export **replay-format artifact** for restore. Enable **Include compact outputs** "
    ),
    "Primary UI after migration Phase 18.": "Primary UI after NiceGUI migration.",
    "Frontier Intake (v406) — External Candidate Sets": "Frontier Intake — External Candidate Sets",
    "Feasible-First Surrogate Accelerator (v386)": "Feasible-First Surrogate Accelerator",
    "Regulatory & Reviewer Evidence Packs (v334.0)": "Regulatory & Reviewer Evidence Packs",
    "What this pack contains (v334.0 schema v2)": "What this pack contains (standard pack schema)",
    "Licensing Evidence Tier 2 (v355.0)": "Licensing Evidence Tier 2",
    "Objective contract (v2)": "Objective contract (version 2)",
    "🗺️ Multi-Objective Feasible Frontier Atlas (v351)": "🗺️ Multi-Objective Feasible Frontier Atlas",
    "🧾 Robust Design Envelope Certification (v352)": "🧾 Robust Design Envelope Certification",
    "🧾 Regulatory & Reviewer Evidence Packs (v334.0)": "🧾 Regulatory & Reviewer Evidence Packs",
    "🏛️ Licensing Evidence Tier 2 (v355.0)": "🏛️ Licensing Evidence Tier 2",
    "### 🧭 Frontier Intake (v406) — External Candidate Sets": "### 🧭 Frontier Intake — External Candidate Sets",
    "### ⚡ Feasible-First Surrogate Accelerator (v386)": "### ⚡ Feasible-First Surrogate Accelerator",
    "v402 dominance reference thresholds": "Dominance reference thresholds",
    "v397 profile proxy disabled — τE peaking factor not computed.": "Profile transport proxy disabled — τE peaking factor not computed.",
    "v351 atlas deck is descriptive-only and does not push points back into truth. Promote designs via the Study Setup deck.": (
        "Frontier atlas is descriptive-only and does not push points back into truth. Promote designs via the Study Setup deck."
    ),
    "No candidate set available yet. Run a Trade Study (or v351 lane classification) first.": (
        "No candidate set available yet. Run a Trade Study (or lane classification) first."
    ),
    "Run v406 intake + deterministic verification": "Run frontier intake + deterministic verification",

# Prefix captions like "v204: Timeline strip..."
_PREFIX_CAPTION_RE = re.compile(
    r"^(v\d+(?:\.\d+)?(?:\.\d+)?)\s*:\s*",
    re.IGNORECASE,
)

# Parenthetical version tags
_PAREN_TAG_RE = re.compile(
    r"\s*\((?:v\d+(?:\.\d+)?(?:\.\d+)?|Batch\s+\d+|Phase\s+\d+)\)",
    re.IGNORECASE,
)

# Inline authority refs: "authority (v389)" -> "authority"
_AUTHORITY_PAREN_RE = re.compile(r"\s*\(v\d+(?:\.\d+)?(?:\.\d+)?\)", re.IGNORECASE)

# Markdown headers ### v399 Multi-species
_MD_VTAG_RE = re.compile(r"^(\s*#+\s*)v\d+(?:\.\d+)?(?:\.\d+)?\s+", re.IGNORECASE | re.MULTILINE)

# Expander titles v399 Per-species
_EXPANDER_VTAG_RE = re.compile(r"^(v\d+(?:\.\d+)?(?:\.\d+)?)\s+", re.IGNORECASE)

# schema vN in user strings
_SCHEMA_RE = re.compile(r"\bschema v\d+\b", re.IGNORECASE)

# Tier N–M in user-facing strings (keep word Tier when it's licensing tier)
_TIER_RANGE_RE = re.compile(r"Tier\s+[\d–\-]+\s*instruments?", re.IGNORECASE)

TIER_REPLACEMENTS = {
    "Tier 5–6 instruments": "Trajectory & counterfactual instruments",
    "Tier 5–6 controls": "Trajectory & counterfactual controls",
    "Tier-5:": "Trajectory instrument:",
    "Tier-6:": "Counterfactual instrument:",
    "Tier-7:": "Collaboration & standards:",
    "Tier-7 standards:": "Collaboration & export standards:",
    "Tier-8:": "Design-space jurisprudence:",
    "Tier-9:": "Genealogy & counter-optimization:",
    "Tier 1–4": "Core tiers 1–4",
    "Tier 5–6": "Trajectory & counterfactual",
    "Tier 8–9:": "Jurisprudence & genealogy:",
}

AUTHORITY_UNAVAILABLE = {
    "Structural stress authority (v389) not enabled or unavailable in this artifact.": (
        "Structural stress authority not enabled or unavailable in this artifact."
    ),
    "Damage → strength coupling (v393) not enabled or unavailable in this artifact.": (
        "Damage → strength coupling not enabled or unavailable in this artifact."
    ),
    "Neutronics & activation authority (v390) not enabled or unavailable in this artifact.": (
        "Neutronics & activation authority not enabled or unavailable in this artifact."
    ),
    "Neutronics shield attenuation (v392) not enabled or unavailable in this artifact.": (
        "Neutronics shield attenuation not enabled or unavailable in this artifact."
    ),
    "Availability reliability envelope (v391) not enabled or unavailable in this artifact.": (
        "Availability reliability envelope not enabled or unavailable in this artifact."
    ),
}

FORGE_CAPTIONS = {
    "v204: Timeline strip of the current run (phases + evaluations).": (
        "Timeline strip of the current run (phases + evaluations)."
    ),
    "v204: Design lineage graph based on recorded parents (audit-clean).": (
        "Design lineage graph based on recorded parents (audit-clean)."
    ),
    "v204: Spend map - where feasibility margin is being spent.": (
        "Spend map — where feasibility margin is being spent."
    ),
    "v205: Robustness envelope (first-order margin perturbation sweep).": (
        "Robustness envelope (first-order margin perturbation sweep)."
    ),
    "v205: Design narrative pack (review-grade, no recommendations).": (
        "Design narrative pack (review-grade, no recommendations)."
    ),
    "v205: One-page design card (printable, reviewer-friendly).": (
        "One-page design card (printable, reviewer-friendly)."
    ),
    "v207: Design Packet - narrative + card + key tables (PDF best-effort).": (
        "Design packet — narrative + card + key tables (PDF best-effort)."
    ),
    "v207: Confidence Sweep - explicit declared perturbations (no hidden penalties, no recommendations).": (
        "Confidence sweep — explicit declared perturbations (no hidden penalties, no recommendations)."
    ),
}

CONTROL_ROOM = {
    "### v399 Multi-species impurity mix (if enabled)": "### Multi-species impurity mix (if enabled)",
    "v399 Per-species radiation (MW)": "Per-species radiation (MW)",
    "v399 Validity flags": "Multi-species validity flags",
    "v320 authority: single-species partitions + detachment inversion. v399: multi-species mix → Zeff + partitions + achieved detachment margin (diagnostic; no truth feedback).": (
        "Exhaust authority: single-species partitions + detachment inversion. "
        "Multi-species mix adds Zeff + partitions + achieved detachment margin (diagnostic; no truth feedback)."
    ),
}

EXACT.update(AUTHORITY_UNAVAILABLE)
EXACT.update(FORGE_CAPTIONS)
EXACT.update(CONTROL_ROOM)


def clean_text(text: str) -> str:
    for old, new in sorted(EXACT.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    for old, new in TIER_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = _PREFIX_CAPTION_RE.sub("", text)
    text = _MD_VTAG_RE.sub(r"\1", text)
    text = _SCHEMA_RE.sub("standard replay schema", text)
    text = _PAREN_TAG_RE.sub("", text)
    # Second pass for nested (v328.0) style after partial
    text = _AUTHORITY_PAREN_RE.sub("", text)
    return text


def process_file(path: Path, write: bool) -> int:
    original = path.read_text(encoding="utf-8")
    updated = clean_text(original)
    if updated == original:
        return 0
    if write:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    changed = 0
    files = 0
    targets = []
    for d in UI_DIRS:
        if d.exists():
            targets.extend(sorted(d.rglob("*.py")))
    # Streamlit app redirect messages and deck headers
    app_py = ROOT / "ui" / "app.py"
    if app_py.exists():
        targets.append(app_py)
    readme = ROOT / "ui_nicegui" / "README.md"
    if readme.exists():
        targets.append(readme)

    skip_names = {
        "display_labels.py",
        "clean_user_version_tags.py",
        "audit_version_tags.py",
        "icons.py",
        "branding.py",
    }
    skip_prefixes = ("ui/decks/_",)

    for p in targets:
        if p.name in skip_names:
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if any(rel.startswith(sp) for sp in skip_prefixes):
            continue
        files += 1
        if process_file(p, args.write):
            changed += 1
            print(("WROTE" if args.write else "WOULD CHANGE"), p.relative_to(ROOT))

    print(f"--- {changed}/{files} files {'updated' if args.write else 'would change'} ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
