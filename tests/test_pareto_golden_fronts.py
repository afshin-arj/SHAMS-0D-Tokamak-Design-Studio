import json
import hashlib

import pandas as pd

from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from solvers.optimize import pareto_optimize


def test_pareto_golden_sampling_is_deterministic():
    # Golden: under current frozen physics+constraints, this reference machine is infeasible in the sampled neighborhood.
    base = PointInputs.from_dict(REFERENCE_MACHINES["SPARC-class (compact HTS)"])
    bounds = {
        "R0_m": (1.4, 2.4),
        "a_m": (0.4, 0.9),
        "kappa": (1.5, 2.2),
        "Bt_T": (8.0, 15.0),
        "Ip_MA": (5.0, 12.0),
        "Ti_keV": (8.0, 22.0),
        "fG": (0.5, 1.2),
        "Paux_MW": (5.0, 120.0),
        "t_shield_m": (0.4, 1.0),
    }
    objectives = {"R0_m": "min", "Q_DT_eqv": "max"}
    res = pareto_optimize(base, bounds=bounds, objectives=objectives, n_samples=80, seed=7, intent_key="Research", parallel=False)

    assert res["perf"]["n_samples"] == 80
    assert len(res.get("all", [])) == 80

    # Stable golden behavior: no feasible points found in this neighborhood (as of frozen v195.x physics).
    assert len(res.get("feasible", [])) == 0
    assert len(res.get("pareto", [])) == 0

    # But we still expect all-sample diagnostics to exist (failure atlas support).
    dfA = pd.DataFrame(res["all"])
    assert "is_feasible" in dfA.columns
    assert dfA["is_feasible"].sum() == 0
    assert "first_failure" in dfA.columns
    assert dfA["first_failure"].astype(str).str.len().mean() > 0

    # Deterministic fingerprint for audit (counts by first_failure).
    counts = dfA["first_failure"].value_counts().to_dict()
    blob = json.dumps(counts, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == "bac8c46f39ef82582eae568979099ec33df6689e8bcf1a270f44237ec3f80f69"
