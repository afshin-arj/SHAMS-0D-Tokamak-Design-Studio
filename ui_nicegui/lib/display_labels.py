"""User-facing labels — no internal version tags (v351, Batch 7, etc.)."""
from __future__ import annotations

import re

# Trade Study advanced decks (canonical display names)
DECK_FRONTIER_ATLAS = "Multi-Objective Feasible Frontier Atlas"
DECK_ROBUST_CERT = "Robust Design Envelope Certification"
DECK_REGIME_MAPS = "Regime Maps & Narratives"

# Publication Benchmarks
TAB_EVIDENCE_PACK = "Regulatory Evidence Pack Builder"

# Authority overlay codes → plain names (for captions that reference overlays)
AUTHORITY_OVERLAY_NAMES: dict[str, str] = {
    "v320": "Exhaust & radiation partitions",
    "v324": "Regime maps",
    "v326": "Interoperability contracts",
    "v328": "Magnet technology regime",
    "v334": "Regulatory evidence packs",
    "v340": "Legacy single-objective optimizer",
    "v349": "Profile authority",
    "v351": "Multi-objective frontier atlas",
    "v352": "Robust design envelope",
    "v355": "Licensing evidence tier 2",
    "v358": "Transport profile proxy",
    "v361": "Plant power ledger caps",
    "v368": "Maintenance scheduling",
    "v371": "Confinement scaling",
    "v372": "Transport envelope",
    "v376": "Confinement certification",
    "v377": "Disruption severity proxy",
    "v378": "Control & actuation authority",
    "v381": "Current drive authority",
    "v382": "Transport profile authority",
    "v384": "Materials & lifetime authority",
    "v387": "Regulatory evidence pack builder",
    "v389": "Structural stress authority",
    "v390": "Neutronics & activation",
    "v391": "Availability & reliability envelope",
    "v392": "Neutronics shield attenuation",
    "v393": "Damage → strength coupling",
    "v394": "Design family governance",
    "v395": "Current drive library",
    "v396": "Confinement transport envelope",
    "v397": "Profile transport authority",
    "v398": "Vertical stability & VDE",
    "v399": "Multi-species impurity mix",
    "v400": "Magnet technology margins",
    "v402": "Authority dominance",
    "v405": "Multi-objective Pareto frontier",
    "v408": "Nuclear dataset intake",
    "v410": "Magnet SC system / TF/PF/CS SC",
    "v412": "Machine build closure / Radial machine-build",
    "v419": "Plant Sankey ledger",
    "v420": "Availability–OPEX–LCOE",
    "v421": "Bottom-up modular costing",
}

# Legacy aliases → canonical (session state / old presets)
LEGACY_LABEL_ALIASES: dict[str, str] = {
    "Multi-Objective Feasible Frontier Atlas (v351)": DECK_FRONTIER_ATLAS,
    "Robust Design Envelope Certification (v352)": DECK_ROBUST_CERT,
    "Regime Maps & Narratives (v324)": DECK_REGIME_MAPS,
    "Regulatory Evidence Pack Builder (v387)": TAB_EVIDENCE_PACK,
    "Regime-Conditioned Pareto Atlas 2.0": "Regime-Conditioned Pareto Atlas",
    "Global Dominance & Regime (v402)": "Global Dominance & Regime",
    "4 · Capsules & Export": "5 · Capsules & Export",
    "Compare sources": "1 · Load A & B",
    "Key metrics": "2 · Performance",
    "Constraints (worst margins first)": "3 · Constraints",
    "Single objective (v340 compat)": "Single objective (legacy compat)",
    "Pareto frontier (v405)": "Multi-objective Pareto frontier",
    "Study Matrix Builder v2": "Study Matrix Builder",
}

_VERSION_TAG_RE = re.compile(
    r"\s*\((?:v\d+(?:\.\d+)?(?:\.\d+)?|Batch\s+\d+|Phase\s+\d+|Tier\s+[\d–\-]+)\)",
    re.IGNORECASE,
)
_LEADING_VTAG_RE = re.compile(r"^v\d+(?:\.\d+)?(?:\.\d+)?\s*:\s*", re.IGNORECASE)
_SCHEMA_TAG_RE = re.compile(r"\bschema v\d+\b", re.IGNORECASE)
_STUDY_SCHEMA_RE = re.compile(r"\b(?:case_deck|study_index|tables)\.v\d+\b", re.IGNORECASE)


def strip_version_tags(text: str) -> str:
    """Remove parenthetical version tags from user-visible strings."""
    if not text:
        return text
    s = str(text)
    s = _LEADING_VTAG_RE.sub("", s)
    s = _VERSION_TAG_RE.sub("", s)
    s = _SCHEMA_TAG_RE.sub("standard replay schema", s)
    s = _STUDY_SCHEMA_RE.sub(lambda m: m.group(0).split(".")[0], s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def authority_display(code: str) -> str:
    """Map overlay code like v389 to plain name."""
    key = str(code or "").strip().lower()
    if not key.startswith("v"):
        key = f"v{key.lstrip('v')}"
    return AUTHORITY_OVERLAY_NAMES.get(key, strip_version_tags(key))


def normalize_user_label(text: str) -> str:
    """Map legacy labels to canonical names and strip version tags."""
    s = str(text or "").strip()
    if s in LEGACY_LABEL_ALIASES:
        return LEGACY_LABEL_ALIASES[s]
    return strip_version_tags(s)
