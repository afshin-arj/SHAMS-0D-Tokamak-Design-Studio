from __future__ import annotations

from constraints.registry_codegen import generate_registry_module, verify_codegen_sync


def test_registry_codegen_sync() -> None:
    generate_registry_module(write=True)
    assert verify_codegen_sync()


def test_codegen_specs_match_json() -> None:
    from constraints.authority_registry import load_authority_specs
    from src.constraints.data.authority_specs_codegen import REGISTRY_SPECS

    specs = load_authority_specs()
    assert len(specs) == len(REGISTRY_SPECS)
    assert specs[0].name == REGISTRY_SPECS[0]["name"]
