from __future__ import annotations

"""Frontier mechanism utilities (v246.0).

Purpose
-------
Provide deterministic, audit-friendly helpers for:
- Filtering frontier points by dominant mechanism (or mechanism group)
- Computing mechanism switch points along a frontier (ordered by file row order)
- Computing transition counts and compressed sequences

These helpers are UI/analysis-layer only. They do not modify physics, constraints, or the frozen evaluator.

© 2026 Afshin Arjhangmehr
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import math


def _as_str(x: Any, default: str = "—") -> str:
    try:
        s = str(x)
        return s if s.strip() else default
    except Exception:
        return default


def discover_mechanism_column(columns: Sequence[str]) -> Optional[str]:
    """Pick the preferred mechanism column name."""
    cols = [str(c) for c in columns]
    for k in ("dominant_mechanism_group", "dominant_mechanism"):
        if k in cols:
            return k
    return None


def filter_by_mechanisms(df: Any, mech_col: str, allowed: Iterable[str]) -> Any:
    """Return df filtered to allowed mechanisms (no-op if allowed empty)."""
    allowed_set = {str(a) for a in allowed if str(a).strip()}
    if not allowed_set:
        return df
    try:
        return df[df[mech_col].astype(str).isin(sorted(allowed_set))].copy()
    except Exception:
        return df


def compressed_sequence(seq: Sequence[Any], *, max_len: int = 200) -> List[str]:
    out: List[str] = []
    for x in seq:
        s = _as_str(x)
        if not out or out[-1] != s:
            out.append(s)
        if len(out) >= max_len:
            break
    return out


def transition_counts(seq: Sequence[Any]) -> List[Dict[str, Any]]:
    """Return transition counts between consecutive entries."""
    s = [_as_str(x) for x in seq]
    counts: Dict[Tuple[str, str], int] = {}
    for a, b in zip(s[:-1], s[1:]):
        counts[(a, b)] = counts.get((a, b), 0) + 1
    rows = [{"from": a, "to": b, "count": int(n)} for (a, b), n in counts.items()]
    rows.sort(key=lambda r: (-int(r["count"]), str(r["from"]), str(r["to"])))
    return rows


def _safe_float(x: Any) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return float("nan")


def compute_switch_points(
    df: Any,
    *,
    mech_col: str,
    xcol: Optional[str] = None,
    ycol: Optional[str] = None,
    extra_cols: Optional[Sequence[str]] = None,
    max_points: int = 500,
) -> List[Dict[str, Any]]:
    """Compute indices where mechanism changes along row order.

    Notes
    -----
    - Frontier ordering is defined by the CSV row order (deterministic).
    - This intentionally avoids re-sorting by any column (objective, margin, etc.)
      to preserve trace provenance.

    Returns a list of dicts containing:
      i (row index), from, to, x, y, and selected extra columns if present.
    """
    extra_cols = list(extra_cols or [])
    # Always try to carry these if present
    for k in ("worst_hard_margin", "objective", "dominant_constraint"):
        if k not in extra_cols:
            extra_cols.append(k)

    try:
        seq = df[mech_col].tolist()
    except Exception:
        return []

    seq_s = [_as_str(v) for v in seq]
    out: List[Dict[str, Any]] = []
    for i in range(1, len(seq_s)):
        if seq_s[i] != seq_s[i - 1]:
            row: Dict[str, Any] = {
                "i": int(i),
                "from": seq_s[i - 1],
                "to": seq_s[i],
            }
            if xcol and xcol in getattr(df, "columns", []):
                row["x"] = _safe_float(df.iloc[i][xcol])
            if ycol and ycol in getattr(df, "columns", []):
                row["y"] = _safe_float(df.iloc[i][ycol])

            # attach extras (best-effort)
            for k in extra_cols:
                try:
                    if k in df.columns:
                        v = df.iloc[i][k]
                        if isinstance(v, (int, float)) and (not math.isfinite(float(v))):
                            continue
                        row[k] = v
                except Exception:
                    continue

            out.append(row)
            if len(out) >= int(max_points):
                break
    return out
