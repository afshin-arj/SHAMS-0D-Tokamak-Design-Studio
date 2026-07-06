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

    # Research intent: only q95 blocks; engineering limits are diagnostic (governance+intent).
    assert len(res.get("feasible", [])) == 54
    assert len(res.get("pareto", [])) == 6

    dfA = pd.DataFrame(res["all"])
    assert "is_feasible" in dfA.columns
    assert dfA["is_feasible"].sum() == 54
    assert "governance_feasible" in dfA.columns
    assert "first_failure" in dfA.columns
    assert (dfA.loc[~dfA["is_feasible"], "first_failure"].astype(str).str.len() > 0).all()

    # Deterministic fingerprint for audit (counts by first_failure).
    counts = dfA["first_failure"].value_counts().to_dict()
    blob = json.dumps(counts, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == "fe9204f4d2d699d2513e4bb718df30f44bb54223cf76752acbf26db31412efff"

    # Reactor intent on the same LHS draw remains fully infeasible in this neighborhood.
    res_r = pareto_optimize(
        base, bounds=bounds, objectives=objectives, n_samples=80, seed=7, intent_key="Reactor", parallel=False
    )
    assert len(res_r.get("feasible", [])) == 0
    dfR = pd.DataFrame(res_r["all"])
    counts_r = dfR["first_failure"].value_counts().to_dict()
    digest_r = hashlib.sha256(json.dumps(counts_r, sort_keys=True).encode("utf-8")).hexdigest()
    assert digest_r == "1ed41222e6595e885c5027bc2ef45e75de04cc9c03e39151f946bb2db69cac80"
