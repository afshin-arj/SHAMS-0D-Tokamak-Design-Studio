from __future__ import annotations

from pathlib import Path


def test_contract_validator_runs_and_is_deterministic():
    repo_root = Path(__file__).resolve().parent.parent
    from ui.panel_contracts import get_panel_contracts
    from tools.interoperability.contract_validator import validate_ui_contracts

    contracts = get_panel_contracts()
    r1 = validate_ui_contracts(repo_root, contracts, session_state={})
    r2 = validate_ui_contracts(repo_root, contracts, session_state={})

    assert isinstance(r1, dict)
    assert r1 == r2  # deterministic
    assert "summary" in r1 and "declared_contracts" in r1["summary"]
