from __future__ import annotations
"""Reference machine presets for qualitative validation.

Notes
-----
These presets are primarily used to:
  - seed the UI with plausible starting points
  - enable regression tests / deterministic benchmark packs

Some entries are "*-inspired" envelopes rather than exact reproductions.

For publication benchmarking, prefer presets that are explicitly sourced from
tables in public literature (and keep the input JSONs used for the paper under
benchmarks/publication).
"""

from typing import Dict, Any

REFERENCE_MACHINES: Dict[str, Dict[str, Any]] = {
    "SPARC-class (compact HTS)": {
        "R0_m": 1.85,
        "a_m": 0.57,
        "kappa": 1.8,
        "Bt_T": 12.2,
        "Ip_MA": 8.0,
        "Ti_keV": 15.0,
        "fG": 0.8,
        "Paux_MW": 20.0,
        "t_shield_m": 0.25,
    },
    "HH170 (Energy Singularity, public slide values)": {
        "R0_m": 1.5,
        "a_m": 0.47,
        "kappa": 1.85,
        "Bt_T": 9.0,
        "Ip_MA": 6.3,
        "Ti_keV": 12.0,
        "fG": 0.8,
        "Paux_MW": 20.0,
        "t_shield_m": 0.35,
    },
    "ARC-class (reactor HTS)": {
        "R0_m": 3.3,
        "a_m": 1.1,
        "kappa": 1.9,
        "Bt_T": 9.2,
        "Ip_MA": 12.0,
        "Ti_keV": 18.0,
        "fG": 0.85,
        "Paux_MW": 30.0,
        "t_shield_m": 0.7,
    },
    "ITER-inspired (large LTS)": {
        "R0_m": 6.2,
        "a_m": 2.0,
        "kappa": 1.7,
        "Bt_T": 5.3,
        "Ip_MA": 15.0,
        "Ti_keV": 10.0,
        "fG": 0.85,
        "Paux_MW": 50.0,
        "t_shield_m": 1.0,
    },
    "JET-inspired (EU legacy research)": {
        "R0_m": 2.96,
        "a_m": 1.0,
        "kappa": 1.7,
        "Bt_T": 3.45,
        "Ip_MA": 4.0,
        "Ti_keV": 8.0,
        "fG": 0.8,
        "Paux_MW": 30.0,
        "t_shield_m": 0.4,
    },
    "DIII-D-inspired (US research)": {
        "R0_m": 1.67,
        "a_m": 0.67,
        "kappa": 1.9,
        "Bt_T": 2.1,
        "Ip_MA": 2.0,
        "Ti_keV": 5.0,
        "fG": 0.85,
        "Paux_MW": 20.0,
        "t_shield_m": 0.3,
    },
    "EAST-inspired (China long-pulse)": {
        "R0_m": 1.85,
        "a_m": 0.45,
        "kappa": 1.9,
        "Bt_T": 2.5,
        "Ip_MA": 1.0,
        "Ti_keV": 5.0,
        "fG": 0.8,
        "Paux_MW": 15.0,
        "t_shield_m": 0.3,
    },
    "KSTAR-inspired (Korea superconducting)": {
        "R0_m": 1.8,
        "a_m": 0.5,
        "kappa": 1.8,
        "Bt_T": 3.5,
        "Ip_MA": 2.0,
        "Ti_keV": 8.0,
        "fG": 0.8,
        "Paux_MW": 15.0,
        "t_shield_m": 0.3,
    },
    "JT-60SA-inspired (superconducting)": {
        "R0_m": 2.96,
        "a_m": 1.18,
        "kappa": 1.95,
        "Bt_T": 2.25,
        "Ip_MA": 5.5,
        "Ti_keV": 8.0,
        "fG": 0.8,
        "Paux_MW": 40.0,
        "t_shield_m": 0.6,
    },
    "MAST-U-inspired (UK spherical tokamak)": {
        "R0_m": 0.86,
        "a_m": 0.65,
        "kappa": 2.4,
        "Bt_T": 0.8,
        "Ip_MA": 2.0,
        "Ti_keV": 2.5,
        "fG": 0.7,
        "Paux_MW": 10.0,
        "t_shield_m": 0.05,
    },
    "NSTX-U-inspired (US spherical tokamak)": {
        "R0_m": 0.93,
        "a_m": 0.65,
        "kappa": 2.2,
        "Bt_T": 1.0,
        "Ip_MA": 2.0,
        "Ti_keV": 3.0,
        "fG": 0.7,
        "Paux_MW": 15.0,
        "t_shield_m": 0.05,
    },
    "ASDEX Upgrade-inspired (EU research tokamak)": {
        "R0_m": 1.65,
        "a_m": 0.5,
        "kappa": 1.75,
        "Bt_T": 2.5,
        "Ip_MA": 1.2,
        "Ti_keV": 4.0,
        "fG": 0.9,
        "Paux_MW": 20.0,
        "t_shield_m": 0.2,
    },
    "TCV-inspired (EU shaping research tokamak)": {
        "R0_m": 0.88,
        "a_m": 0.25,
        "kappa": 1.7,
        "Bt_T": 1.5,
        "Ip_MA": 1.0,
        "Ti_keV": 2.0,
        "fG": 0.6,
        "Paux_MW": 5.0,
        "t_shield_m": 0.15,
    },
    "Alcator C-Mod-inspired (high-field compact tokamak)": {
        "R0_m": 0.68,
        "a_m": 0.22,
        "kappa": 1.6,
        "Bt_T": 5.4,
        "Ip_MA": 1.0,
        "Ti_keV": 3.5,
        "fG": 0.9,
        "Paux_MW": 6.0,
        "t_shield_m": 0.15,
    },
    # --- Publication-oriented presets (values taken directly from literature tables)
    # STEP Prototype Plant baseline scenario (Hudoba et al., FED 191 (2023) 113704)
    # Table 1 provides: Ip=19.9 MA, R0=4.21 m, a=2.0 m (from Rout-Rin)/2, Bt=2.65 T,
    # kappa=3.0, delta=0.56, q95=9.35, betaN=3.90.
    # We only ingest geometric and machine-control inputs here; remaining physics
    # inputs (e.g., Ti, fG, Paux) are conservative placeholders for SHAMS 0-D.
    "STEP SPP baseline (UKAEA, 2023)": {
        "R0_m": 4.21,
        "a_m": 2.0,
        "kappa": 3.0,
        "delta": 0.56,
        "Bt_T": 2.65,
        "Ip_MA": 19.9,
        "Ti_keV": 15.0,
        "fG": 0.85,
        "Paux_MW": 50.0,
        "t_shield_m": 0.8,
    },
    # EU DEMO low-A redesign size points (Bachmann et al., FED 204 (2024) 114518)
    # Table 8 provides (R, B0) for minimum-size points at given aspect ratio.
    # Other fields are placeholders and should be replaced by cited values when
    # the paper benchmark tables are assembled.
    "EU DEMO (low-A) size point A=2.6 (2024)": {
        "R0_m": 7.5,
        "a_m": 7.5 / 2.6,
        "kappa": 1.7,
        "delta": 0.33,
        "Bt_T": 4.0,
        "Ip_MA": 15.0,
        "Ti_keV": 14.0,
        "fG": 0.85,
        "Paux_MW": 80.0,
        "t_shield_m": 1.0,
    },
    "EU DEMO (low-A) size point A=3.1 (2024)": {
        "R0_m": 8.9,
        "a_m": 8.9 / 3.1,
        "kappa": 1.7,
        "delta": 0.33,
        "Bt_T": 5.8,
        "Ip_MA": 15.0,
        "Ti_keV": 14.0,
        "fG": 0.85,
        "Paux_MW": 80.0,
        "t_shield_m": 1.0,
    },
    "EU DEMO (low-A) size point A=3.3 (2024)": {
        "R0_m": 6.5,
        "a_m": 6.5 / 3.3,
        "kappa": 1.7,
        "delta": 0.33,
        "Bt_T": 6.5,
        "Ip_MA": 15.0,
        "Ti_keV": 14.0,
        "fG": 0.85,
        "Paux_MW": 80.0,
        "t_shield_m": 1.0,
    },
}

def reference_presets():
    """Return reference presets as PointInputs objects.

    Naming logic (freeze-grade, consistent):
      REF|<INTENT>|<FAMILY>

    Backward-compatible aliases are also returned for legacy keys.
    """
    from models.inputs import PointInputs

    def _canon(intent: str, family: str) -> str:
        return f"REF|{intent.strip().upper()}|{family.strip().upper()}"

    # Canonical keys (REF|<INTENT>|<FAMILY> -> source name in REFERENCE_MACHINES)
    mapping = {
        _canon("Reactor", "SPARC"): "SPARC-class (compact HTS)",
        _canon("Reactor", "ARC"): "ARC-class (reactor HTS)",
        _canon("Reactor", "ITER"): "ITER-inspired (large LTS)",
        _canon("Reactor", "HH170"): "HH170 (Energy Singularity, public slide values)",
        _canon("Research", "JET"): "JET-inspired (EU legacy research)",
        _canon("Research", "DIII-D"): "DIII-D-inspired (US research)",
        _canon("Research", "EAST"): "EAST-inspired (China long-pulse)",
        _canon("Research", "KSTAR"): "KSTAR-inspired (Korea superconducting)",
        _canon("Research", "JT-60SA"): "JT-60SA-inspired (superconducting)",
        _canon("Research", "MAST-U"): "MAST-U-inspired (UK spherical tokamak)",
        _canon("Research", "NSTX-U"): "NSTX-U-inspired (US spherical tokamak)",
        _canon("Research", "ASDEX-U"): "ASDEX Upgrade-inspired (EU research tokamak)",
        _canon("Research", "TCV"): "TCV-inspired (EU shaping research tokamak)",
        _canon("Research", "C-MOD"): "Alcator C-Mod-inspired (high-field compact tokamak)",
        _canon("Reactor", "STEP"): "STEP SPP baseline (UKAEA, 2023)",
        _canon("Reactor", "EUDEMO_A26"): "EU DEMO (low-A) size point A=2.6 (2024)",
        _canon("Reactor", "EUDEMO_A31"): "EU DEMO (low-A) size point A=3.1 (2024)",
        _canon("Reactor", "EUDEMO_A33"): "EU DEMO (low-A) size point A=3.3 (2024)",
    }

    def _infer_magnet_tech(src_name: str, intent_key: str) -> str:
        s = str(src_name or "").lower()
        # Explicit tags first
        if "hts" in s or "rebco" in s or "compact" in s:
            return "HTS_REBCO"
        if "iter" in s:
            return "LTS_NB3SN"  # ITER TF uses Nb3Sn; kept as tech-axis flag only
        if "kstar" in s:
            return "LTS_NB3SN"
        if "east" in s or "jt-60sa" in s:
            return "LTS_NBTI"
        if "demo" in s:
            return "LTS_NB3SN"
        # Legacy research machines: default to resistive copper
        if any(k in s for k in ["jet", "diii", "asdex", "tcv", "c-mod", "mast", "nstx"]):
            return "COPPER"
        # Fallbacks by intent
        return "HTS_REBCO" if intent_key.lower().startswith("reactor") else "COPPER"

    def _default_Tcoil_K(tech: str) -> float:
        t = str(tech or "").upper()
        if t == "COPPER":
            return 300.0
        if t in ("LTS_NB3SN", "LTS_NBTI"):
            return 4.5
        return 20.0

    presets = {}
    for k, src_name in mapping.items():
        d = dict(REFERENCE_MACHINES.get(src_name) or {})
        # Tech-axis defaults (freeze-grade): make magnet technology explicit in inputs.
        if "magnet_technology" not in d:
            intent_key = "reactor" if "|REACTOR|" in k else "research"
            d["magnet_technology"] = _infer_magnet_tech(src_name, intent_key)
        if "Tcoil_K" not in d:
            d["Tcoil_K"] = _default_Tcoil_K(str(d.get("magnet_technology")))
        presets[k] = PointInputs(**d)

    # Legacy aliases
    legacy_aliases = {
        "SPARC-class": _canon("Reactor", "SPARC"),
        "ARC-class": _canon("Reactor", "ARC"),
        "ITER-inspired": _canon("Reactor", "ITER"),
        "ITER-like": _canon("Reactor", "ITER"),
        "HH170": _canon("Reactor", "HH170"),
    }
    for legacy, canon in legacy_aliases.items():
        if canon in presets:
            presets[legacy] = presets[canon]

    return presets



def reference_catalog() -> Dict[str, Dict[str, Any]]:
    """Return a UI-friendly catalog of reference presets.

    Each entry contains:
      - key (canonical)
      - label (human)
      - intent, family
      - inputs (PointInputs)

    Legacy aliases are intentionally not included here.
    """
    from models.inputs import PointInputs

    presets = reference_presets()

    # UI label tuning (expert-facing). Internal canonical keys remain stable.
    COOL_INTENT = {"REACTOR": "Power Reactor", "RESEARCH": "Experimental Device"}
    COOL_FAMILY_LABELS = {
        "SPARC": "SPARC-class (HTS compact)",
        "ARC": "ARC-class (HTS reactor)",
        "ITER": "ITER (large LTS baseline)",
        "HH170": "HH170 (Energy Singularity)",
        "JET": "JET (EU legacy)",
        "DIII-D": "DIII-D (US workhorse)",
        "EAST": "EAST (CN long-pulse)",
        "KSTAR": "KSTAR (KR superconducting)",
        "JT-60SA": "JT-60SA (Japan/Europe)",
        "MAST-U": "MAST Upgrade — MAST-U (UK spherical tokamak)",
        "NSTX-U": "NSTX-U (US spherical tokamak)",
        "ASDEX-U": "ASDEX Upgrade (EU H-mode workhorse)",
        "TCV": "TCV (Swiss shaping laboratory)",
        "C-MOD": "Alcator C-Mod (high-field compact)",
        "STEP": "STEP Prototype Plant (UKAEA)",
        "EUDEMO_A26": "EU DEMO (A=2.6 size point)",
        "EUDEMO_A31": "EU DEMO (A=3.1 size point)",
        "EUDEMO_A33": "EU DEMO (A=3.3 size point)",
    }

    out: Dict[str, Dict[str, Any]] = {}
    for k, inp in presets.items():
        if not isinstance(k, str) or not k.startswith("REF|"):
            continue
        parts = k.split("|")
        intent = parts[1] if len(parts) > 1 else ""
        family = parts[2] if len(parts) > 2 else ""
        cool_family = COOL_FAMILY_LABELS.get(family, family.replace('_',' ').title())
        cool_intent = COOL_INTENT.get(intent.upper(), intent.title())
        label = f"{cool_family}  ·  {cool_intent}"
        out[k] = {
            "key": k,
            "label": label,
            "intent": intent,
            "family": family,
            # UI-friendly metadata (used by Benchmark Vault)
            "suite": str(intent).upper() if intent else "n/a",
            "class": str(family) if family else "n/a",
            "inputs": inp if isinstance(inp, PointInputs) else inp,
        }
    return out
