from __future__ import annotations

from constraints.authority_registry import (
    evaluate_registry_governance,
    evaluate_registry_ledger,
    load_authority_specs,
    registry_spec_names,
)


def test_authority_registry_loads_specs() -> None:
    specs = load_authority_specs()
    assert len(specs) >= 10
    names = registry_spec_names()
    assert "Transport spread (v396)" in names
    assert "ELM transient heat flux (v409)" in names


def test_registry_builds_governance_and_ledger() -> None:
    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
        "include_elm_transient_heat_v409": 1.0,
        "elm_transient_q_parallel_MW_m2_v409": 100.0,
        "elm_transient_q_parallel_max_MW_m2_v409": 200.0,
    }
    gov = evaluate_registry_governance(out)
    led = evaluate_registry_ledger(out)
    gov_names = {c.name for c in gov}
    led_names = {c.name for c in led}
    assert "Transport spread (v396)" in gov_names
    assert "Transport spread (v396)" in led_names
    assert "ELM transient heat flux (v409)" in gov_names


def test_unified_uses_registry_merge() -> None:
    from constraints.unified import build_all_constraints

    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    bundle = build_all_constraints(out)
    assert bundle.parity.get("registry_n_specs", 0) >= 10
    assert bundle.parity.get("registry_n_governance", 0) >= 1
