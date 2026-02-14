from __future__ import annotations


def test_fidelity_tiers_snapshot_smoke() -> None:
    # Deterministic: should build with empty outputs and empty ledger.
    try:
        from src.provenance.authority import authority_snapshot_from_outputs
        from src.provenance.fidelity_tiers import build_fidelity_tiers_snapshot
    except Exception:
        from provenance.authority import authority_snapshot_from_outputs  # type: ignore
        from provenance.fidelity_tiers import build_fidelity_tiers_snapshot  # type: ignore

    auth = authority_snapshot_from_outputs({})
    snap = build_fidelity_tiers_snapshot(authority_contracts=auth, constraint_ledger={})
    assert isinstance(snap, dict)
    assert str(snap.get("schema_version", "")).startswith("fidelity_tiers")
    design = snap.get("design")
    assert isinstance(design, dict)
    assert "design_fidelity_label" in design
