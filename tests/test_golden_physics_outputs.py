"""Golden-output regression safety net (Tier-3 refactor Batch B0).

Purpose
-------
Pin the *scientific output* of the main 0-D evaluator (`physics.hot_ion.hot_ion_point`)
for a set of representative `PointInputs` so that the upcoming architectural
refactor (splitting hot_ion.py, moving governance overlays, etc.) can be proven
to NOT change any computed result.

How it works
------------
For each named case we:
  1. build a fixed `PointInputs`,
  2. run `hot_ion_point`,
  3. canonicalize the output dict (drop provenance/identity metadata; encode
     nan/inf as sentinels so they round-trip and compare cleanly),
  4. compare against a stored golden JSON under tests/golden/.

Floats compare with tolerance 1e-10 (abs+rel). Strings/bools/ints/None compare
exactly. nan stays nan, inf stays inf (a value flipping to/from nan is a failure).

Provenance / identity fields are ignored (SHA256 fingerprints, dataset/structure
ids, db ids, timestamps), because those may legitimately change when files move
during the refactor without any physics change.

Regenerating the baseline
--------------------------
Only do this when the physics *intentionally* changes (and you have reviewed the
diff). From the repo root:

    python tests/test_golden_physics_outputs.py --regen

This rewrites every tests/golden/<case>.json. Commit the regenerated files in the
same change as the physics edit, with an explanation. Never regenerate to "make
the test pass" during a refactor that is supposed to preserve behavior.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest

# Ensure the domain packages import both under pytest (conftest already sets this)
# and when this file is run standalone for baseline regeneration.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.models.inputs import PointInputs  # noqa: E402  # app/evaluator context (src.* package)
from src.physics.hot_ion import hot_ion_point  # noqa: E402
# NOTE: import as `src.physics.hot_ion` (not top-level `physics.hot_ion`) to match
# the L0 evaluator choke point (`src.evaluator.core` -> `src.physics.hot_ion`).
# hot_ion.py's authority overlays use `from ..contracts.*` / `from ..analysis.*`
# relative imports that only resolve when `hot_ion` is imported as
# `src.physics.hot_ion` (src as a package). Under the top-level `physics.hot_ion`
# layout those relative imports raise "attempted relative import beyond
# top-level package" and the overlays (magnet-tech contract, v389 structural
# stress, impurity radiation, neutronics-materials) silently no-op, dropping
# ~32 output keys vs the golden. The application runtime always uses the
# `src.*` package context, so the golden must pin THAT path.


GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Absolute + relative tolerance for float comparison.
ABS_TOL = 1e-10
REL_TOL = 1e-10


# ---------------------------------------------------------------------------
# Representative input cases (kept here so the test and the regenerator share
# exactly one source of truth).
# ---------------------------------------------------------------------------
CASES: Dict[str, Dict[str, Any]] = {
    # Typical compact, high-field DT reactor regime (SPARC-like).
    "dt_typical": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
    ),
    # DD regime with secondary DT burn from DD-produced tritium.
    "dd_regime": dict(
        R0_m=3.0, a_m=1.0, kappa=1.8, Bt_T=5.3, Ip_MA=12.0,
        Ti_keV=20.0, fG=0.7, Paux_MW=40.0,
        fuel_mode="DD", include_secondary_DT=True,
    ),
    # Low-density edge of the operating space.
    "low_density_edge": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.30, Paux_MW=25.0,
    ),
    # High-beta case (hot, dense, strongly shaped, modest field).
    "high_beta": dict(
        R0_m=2.0, a_m=0.65, kappa=2.0, Bt_T=6.0, Ip_MA=11.0,
        Ti_keV=25.0, fG=1.0, Paux_MW=35.0,
    ),
    # Transport-constrained: envelope authority + H-factor + spread caps.
    "transport_constrained": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
        include_transport_envelope_v396=True, transport_spread_max_v396=1.5,
        H98_allow=1.2, confinement_scaling="ITER89P",
    ),
    # High radiation fraction via the legacy fractional model.
    "high_radiation_fractional": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
        include_radiation=True, radiation_model="fractional", f_rad_core=0.6,
    ),
    # Impurity/line radiation physics path (Lz tables + Zeff from impurity).
    "radiation_physics_impurity": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
        include_radiation=True, radiation_model="physics",
        impurity_species="Ne", impurity_frac=0.02, zeff_mode="from_impurity",
    ),
    # HTS critical-surface margin enabled.
    "hts_enabled": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
        magnet_technology="HTS_REBCO", include_hts_critical_surface=True, Tcoil_K=20.0,
    ),
    # Resistive copper TF (HTS margin path disabled, ohmic-power path active).
    "copper_magnet": dict(
        R0_m=2.2, a_m=0.7, kappa=1.7, Bt_T=6.0, Ip_MA=9.0,
        Ti_keV=12.0, fG=0.8, Paux_MW=30.0, magnet_technology="COPPER",
    ),
    # Governance-heavy: many vNNN overlays enabled at once.
    "governance_heavy": dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
        include_transport_contracts_v371=True, include_profile_proxy_v397=True,
        include_control_stability_authority_v398=True,
        include_neutronics_materials_coupling_v372=True,
        include_profile_family_v358=True,
        include_radiation=True, radiation_model="physics", impurity_frac=0.01,
    ),
}


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------
# Substrings that mark a key as provenance/identity metadata (ignored in the
# comparison). These can change when files move during the refactor without any
# change to the physics.
_EXCLUDE_SUBSTRINGS = (
    "sha256", "_sha", "timestamp", "uuid", "provenance",
    "dataset_id", "structure_id", "db_id", "_id_used", "contract_id",
    # UI-injected metadata (defensive; not produced by hot_ion itself):
    "software", "author", "copyright",
)

# nan/inf sentinels so the golden JSON is portable and comparisons are explicit.
_NAN = "__nan__"
_POS_INF = "__inf__"
_NEG_INF = "__-inf__"


def _is_excluded(key: str) -> bool:
    kl = str(key).lower()
    return any(s in kl for s in _EXCLUDE_SUBSTRINGS)


def canonicalize(value: Any) -> Any:
    """Return a JSON-serializable, comparison-ready view of an output value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return _NAN
        if value == math.inf:
            return _POS_INF
        if value == -math.inf:
            return _NEG_INF
        return value
    if isinstance(value, (int, str)) or value is None:
        return value
    if isinstance(value, dict):
        return {k: canonicalize(v) for k, v in sorted(value.items()) if not _is_excluded(k)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(v) for v in value]
    # Fallback: stable string form (no such values observed in current outputs).
    return repr(value)


def evaluate_case(name: str) -> Any:
    inp = PointInputs(**CASES[name])
    out = hot_ion_point(inp)
    return canonicalize(out)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def _floats_close(a: float, b: float) -> bool:
    return abs(a - b) <= (ABS_TOL + REL_TOL * abs(b))


def diff(golden: Any, current: Any, path: str = "") -> Tuple[bool, str]:
    """Return (equal, message). message describes the first mismatch found."""
    # Numbers (int/float), but not bool.
    if isinstance(golden, (int, float)) and not isinstance(golden, bool) \
            and isinstance(current, (int, float)) and not isinstance(current, bool):
        if _floats_close(float(golden), float(current)):
            return True, ""
        return False, f"{path}: {golden!r} != {current!r} (|delta|={abs(float(golden)-float(current)):.3e})"

    if isinstance(golden, dict) and isinstance(current, dict):
        gk, ck = set(golden), set(current)
        if gk != ck:
            missing = sorted(gk - ck)
            added = sorted(ck - gk)
            return False, f"{path}: key set changed (missing={missing[:5]}, added={added[:5]})"
        for k in sorted(golden):
            eq, msg = diff(golden[k], current[k], f"{path}.{k}" if path else str(k))
            if not eq:
                return False, msg
        return True, ""

    if isinstance(golden, list) and isinstance(current, list):
        if len(golden) != len(current):
            return False, f"{path}: list length {len(golden)} != {len(current)}"
        for i, (g, c) in enumerate(zip(golden, current)):
            eq, msg = diff(g, c, f"{path}[{i}]")
            if not eq:
                return False, msg
        return True, ""

    if golden == current:
        return True, ""
    return False, f"{path}: {golden!r} != {current!r}"


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(CASES))
def test_golden_physics_output(name: str) -> None:
    golden_path = GOLDEN_DIR / f"{name}.json"
    assert golden_path.exists(), (
        f"Missing golden file {golden_path}. Regenerate with:\n"
        f"    python tests/test_golden_physics_outputs.py --regen"
    )
    with golden_path.open("r", encoding="utf-8") as fh:
        golden = json.load(fh)["outputs"]

    current = evaluate_case(name)
    equal, message = diff(golden, current)
    assert equal, (
        f"Golden output drift in case '{name}':\n    {message}\n"
        f"If this change is an INTENTIONAL physics change, review it and "
        f"regenerate with: python tests/test_golden_physics_outputs.py --regen"
    )


# ---------------------------------------------------------------------------
# Baseline regenerator (run as a script, not under pytest)
# ---------------------------------------------------------------------------
def _regenerate() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name in sorted(CASES):
        payload = {
            "case": name,
            "inputs": CASES[name],
            "outputs": evaluate_case(name),
        }
        path = GOLDEN_DIR / f"{name}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True, indent=2)
            fh.write("\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    if "--regen" in sys.argv:
        _regenerate()
    else:
        print("Pass --regen to (re)write golden baselines. No action taken.")
