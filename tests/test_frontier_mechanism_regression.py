from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tools.frontier_mechanism import (
    compressed_sequence,
    transition_counts,
    compute_switch_points,
    discover_mechanism_column,
)


def test_frontier_mechanism_regression():
    base = Path(__file__).resolve().parents[1] / "regression" / "baselines"
    df = pd.read_csv(base / "frontier_island_demo.csv")
    exp = json.loads((base / "frontier_mechanism_expected.json").read_text(encoding="utf-8"))

    mech_col = discover_mechanism_column(list(df.columns))
    assert mech_col == exp["mech_col"]

    seq = df[mech_col].tolist()
    comp = compressed_sequence(seq, max_len=50)
    assert comp == exp["compressed"]

    trans = transition_counts(seq)
    # only check the top 2 transitions (deterministic ordering)
    assert trans[:2] == exp["transitions"]

    sp = compute_switch_points(df, mech_col=mech_col, xcol="objective", ycol="worst_hard_margin", max_points=50)
    assert [int(r["i"]) for r in sp] == exp["switch_i"]

    # envelope metric sanity check (used in narrative ranking)
    mx = float(df["worst_hard_margin"].astype(float).max())
    j = int(df["worst_hard_margin"].astype(float).idxmax())
    obj = float(df.loc[j, "objective"])
    assert abs(mx - float(exp["envelope"]["max_worst_hard_margin"])) < 1e-12
    assert abs(obj - float(exp["envelope"]["objective_at_max_margin"])) < 1e-12
