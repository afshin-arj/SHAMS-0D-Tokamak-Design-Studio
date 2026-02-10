"""SHAMS v332.0 — Design Family Narratives (deterministic, audit-ready).

This module builds *interpretable* design families from evaluated design records.

Key design laws enforced:
  - Frozen truth is not modified.
  - No stochastic/ML clustering.
  - No hidden iteration; all algorithms are single-pass reductions.
  - Output is stable and replayable.

The clustering is rule-based and uses a small set of *semantic labels* already
produced by SHAMS authorities (e.g., magnet regime, exhaust regime, dominance).

If a label is absent in a record, it is treated as "(unknown)" rather than inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import math


def _safe_str(x: Any, default: str = "(unknown)") -> str:
    if x is None:
        return default
    try:
        s = str(x).strip()
        return s if s else default
    except Exception:
        return default


def _bucket(x: Any, *, edges: Sequence[float], labels: Sequence[str]) -> str:
    """Deterministically bucket a numeric value.

    edges: monotonically increasing; bucket i is (-inf, edges[0]] ... (edges[-1], inf)
    labels: must have len(edges)+1
    """
    try:
        v = float(x)
    except Exception:
        return "(unknown)"
    if len(labels) != len(edges) + 1:
        return "(unknown)"
    for i, e in enumerate(edges):
        if v <= e:
            return labels[i]
    return labels[-1]


def _finite(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
        return None
    except Exception:
        return None


@dataclass(frozen=True)
class FamilyConfig:
    """Configuration for deterministic family construction."""

    # Semantic keys used directly (no inference)
    intent_key: str = "intent"
    magnet_regime_key: str = "magnet_regime"
    exhaust_regime_key: str = "exhaust_regime"
    dominant_authority_key: str = "dominant_authority"
    dominant_constraint_key: str = "dominant_constraint_id"

    # Numeric keys for coarse bucketing (interpretable)
    R0_key: str = "R0_m"
    B0_key: str = "B0_T"
    A_key: str = "A"

    # Bucketing for interpretability (conservative defaults)
    R0_edges_m: Tuple[float, ...] = (2.5, 4.0, 6.0, 8.5)
    R0_labels: Tuple[str, ...] = ("compact", "mid", "large", "very_large", "gigantic")

    B0_edges_T: Tuple[float, ...] = (4.0, 6.0, 8.0, 10.0)
    B0_labels: Tuple[str, ...] = ("lowB", "midB", "highB", "very_highB", "extremeB")

    A_edges: Tuple[float, ...] = (1.8, 2.5, 3.2, 4.0)
    A_labels: Tuple[str, ...] = ("lowA", "midA", "highA", "very_highA", "ultraA")

    # Archetype selection
    min_margin_key: str = "margin_min"  # fall back to dominant margin if present
    eval_hash_key: str = "eval_hash"

    # Maximum number of families displayed by default (UI convenience)
    max_families_default: int = 30


@dataclass
class DesignFamily:
    family_id: str
    key: Dict[str, str]
    n: int
    archetype: Dict[str, Any]
    summaries: Dict[str, Any]
    members: List[Dict[str, Any]]


def _family_key(rec: Mapping[str, Any], cfg: FamilyConfig) -> Dict[str, str]:
    intent = _safe_str(rec.get(cfg.intent_key), default="(no-intent)")
    mag = _safe_str(rec.get(cfg.magnet_regime_key))
    exh = _safe_str(rec.get(cfg.exhaust_regime_key))
    domA = _safe_str(rec.get(cfg.dominant_authority_key))
    domC = _safe_str(rec.get(cfg.dominant_constraint_key))

    R0b = _bucket(rec.get(cfg.R0_key), edges=cfg.R0_edges_m, labels=cfg.R0_labels)
    B0b = _bucket(rec.get(cfg.B0_key), edges=cfg.B0_edges_T, labels=cfg.B0_labels)
    Ab = _bucket(rec.get(cfg.A_key), edges=cfg.A_edges, labels=cfg.A_labels)

    return {
        "intent": intent,
        "magnet_regime": mag,
        "exhaust_regime": exh,
        "dominant_authority": domA,
        "dominant_constraint": domC,
        "R0_class": R0b,
        "B0_class": B0b,
        "A_class": Ab,
    }


def _family_id_from_key(k: Mapping[str, str]) -> str:
    # Deterministic stable ID (human-readable, not a hash)
    parts = [
        f"{k.get('intent','(no)')}",
        f"MAG={k.get('magnet_regime','?')}",
        f"EXH={k.get('exhaust_regime','?')}",
        f"DOM={k.get('dominant_authority','?')}",
        f"R0={k.get('R0_class','?')}",
        f"B0={k.get('B0_class','?')}",
        f"A={k.get('A_class','?')}",
    ]
    return " | ".join(parts)


def _choose_archetype(members: Sequence[Mapping[str, Any]], cfg: FamilyConfig) -> Dict[str, Any]:
    """Choose a deterministic representative record.

    Primary: maximize min-margin (if present)
    Tie-break: lexicographic eval_hash (if present)
    Final tie-break: stable index order
    """
    best_i = 0
    best_margin = -float("inf")
    best_hash = ""

    for i, r in enumerate(members):
        m = _finite(r.get(cfg.min_margin_key))
        if m is None:
            # try dominant margin key variants
            m = _finite(r.get("dominant_margin_min"))
        if m is None:
            m = -float("inf")
        h = _safe_str(r.get(cfg.eval_hash_key), default="")
        if (m > best_margin) or (m == best_margin and h and (not best_hash or h < best_hash)):
            best_i = i
            best_margin = m
            best_hash = h

    return dict(members[best_i])


def build_design_families(
    records: Iterable[Mapping[str, Any]],
    cfg: Optional[FamilyConfig] = None,
) -> List[DesignFamily]:
    """Build deterministic design families.

    Parameters
    ----------
    records:
        Iterable of evaluated design records (dict-like). Typically from Pareto Lab
        (`st.session_state.pareto_last['feasible'/'pareto']`).
    cfg:
        Optional FamilyConfig.

    Returns
    -------
    List[DesignFamily]
        Sorted deterministically by descending family size, then family_id.
    """
    cfg = cfg or FamilyConfig()
    groups: Dict[str, List[Dict[str, Any]]] = {}
    keys: Dict[str, Dict[str, str]] = {}

    for r in records:
        if not isinstance(r, Mapping):
            continue
        k = _family_key(r, cfg)
        fid = _family_id_from_key(k)
        groups.setdefault(fid, []).append(dict(r))
        keys[fid] = k

    families: List[DesignFamily] = []
    for fid, mem in groups.items():
        archetype = _choose_archetype(mem, cfg)
        # summaries
        margins = [
            _finite(m.get(cfg.min_margin_key))
            if _finite(m.get(cfg.min_margin_key)) is not None
            else _finite(m.get("dominant_margin_min"))
            for m in mem
        ]
        margins2 = [x for x in margins if x is not None]
        summaries: Dict[str, Any] = {
            "min_margin_min": min(margins2) if margins2 else None,
            "min_margin_p50": (sorted(margins2)[len(margins2)//2] if margins2 else None),
            "min_margin_max": max(margins2) if margins2 else None,
        }
        families.append(
            DesignFamily(
                family_id=fid,
                key=keys.get(fid, {}),
                n=len(mem),
                archetype=archetype,
                summaries=summaries,
                members=mem,
            )
        )

    families.sort(key=lambda f: (-f.n, f.family_id))
    return families
