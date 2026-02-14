from __future__ import annotations

import re

from src.models.inputs import PointInputs
from src.evaluator.cache_key import canonical_json, sha256_cache_key


def test_cache_key_is_sha256_hex() -> None:
    inp = PointInputs(R0_m=6.2, a_m=2.0, kappa=1.9, Bt_T=5.3, Ip_MA=15.0, Ti_keV=12.0, fG=0.85, Paux_MW=50.0)
    k = sha256_cache_key(inp)
    assert isinstance(k, str)
    assert re.fullmatch(r"[0-9a-f]{64}", k) is not None


def test_cache_key_stable_repeat_calls() -> None:
    inp = PointInputs(R0_m=6.2, a_m=2.0, kappa=1.9, Bt_T=5.3, Ip_MA=15.0, Ti_keV=12.0, fG=0.85, Paux_MW=50.0)
    k1 = sha256_cache_key(inp)
    k2 = sha256_cache_key(inp)
    assert k1 == k2


def test_cache_key_changes_with_string_fields() -> None:
    base = dict(R0_m=6.2, a_m=2.0, kappa=1.9, Bt_T=5.3, Ip_MA=15.0, Ti_keV=12.0, fG=0.85, Paux_MW=50.0)
    a = PointInputs(**base, q95_enforcement="hard")
    b = PointInputs(**base, q95_enforcement="diagnostic")
    assert sha256_cache_key(a) != sha256_cache_key(b)


def test_canonical_json_is_sorted_and_compact() -> None:
    inp = PointInputs(R0_m=6.2, a_m=2.0, kappa=1.9, Bt_T=5.3, Ip_MA=15.0, Ti_keV=12.0, fG=0.85, Paux_MW=50.0)
    s = canonical_json(inp)
    # compact: no spaces after separators
    assert ": " not in s
    assert ", " not in s
