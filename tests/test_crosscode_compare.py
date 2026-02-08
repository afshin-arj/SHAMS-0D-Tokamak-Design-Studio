from __future__ import annotations

from pathlib import Path

from benchmarks.crosscode.crosscode_compare import list_crosscode_constitutions, load_crosscode_constitution, compare_to_shams_intent

def test_crosscode_records_load_and_compare():
    items = list_crosscode_constitutions()
    assert items, "Expected at least one cross-code constitution record"
    key, path = items[0]
    assert Path(path).exists()
    cc = load_crosscode_constitution(Path(path))
    comp = compare_to_shams_intent("research", cc)
    assert comp["schema"] == "crosscode_comparison.v1"
    assert "diff" in comp
    assert isinstance(comp["unknown_clause_count"], int)
