from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Dict, Any, List

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact

from .spec import ScenarioSpec


def run_scenarios_for_point(
    base_inputs: PointInputs,
    scenarios: List[ScenarioSpec],
    *,
    label_prefix: str = "scenario",
) -> List[Dict[str, Any]]:
    """Run the same design point across multiple scenarios.

    Scenarios may override:
    - selected PointInputs fields (input_overrides)
    - lifecycle economics assumptions via economics_overrides (merged into the _economics dict)
    """
    results: List[Dict[str, Any]] = []
    base_out = hot_ion_point(base_inputs)
    base_cons = evaluate_constraints(base_out)
    base_econ = dict((base_out or {}).get("_economics", {}))

    for i, sc in enumerate(scenarios):
        inp = copy.deepcopy(base_inputs)
        for k, v in (sc.input_overrides or {}).items():
            if hasattr(inp, k):
                setattr(inp, k, v)

        out = hot_ion_point(inp)
        cons = evaluate_constraints(out)

        econ = dict((out or {}).get("_economics", {}))
        # apply economics overrides (assumptions only)
        if econ and (sc.economics_overrides or {}):
            econ = copy.deepcopy(econ)
            econ.setdefault("assumptions", {})
            econ["assumptions"].update(sc.economics_overrides)

        art = build_run_artifact(
            inputs=dict(inp.__dict__),
            outputs=dict(out),
            constraints=cons,
            meta={"mode": "scenario", "label": f"{label_prefix}:{sc.name}"},
            solver={"message": "scenario_replay"},
            economics=econ,
        )
        art["scenario"] = sc.to_dict()

        # Scenario delta: explicit assumption changes relative to baseline.
        try:
            base_in = dict(base_inputs.__dict__)
            cur_in = dict(inp.__dict__)
            changed_inputs = {k: {"base": base_in.get(k), "scenario": cur_in.get(k)}
                              for k in cur_in.keys() if base_in.get(k) != cur_in.get(k)}

            # Small, stable KPI subset for fast comparison
            kpi_keys = ["Q_DT_eqv", "H98", "Pfus_DT_adj_MW", "P_net_e_MW", "TBR", "q_div_MW_m2"]
            base_out_d = dict(base_out or {})
            cur_out_d = dict(out or {})
            changed_kpis = {k: {"base": base_out_d.get(k), "scenario": cur_out_d.get(k)}
                            for k in kpi_keys if base_out_d.get(k) != cur_out_d.get(k)}

            art["scenario_delta"] = {
                "schema_version": "scenario_delta.v1",
                "changed_inputs": changed_inputs,
                "changed_kpis": changed_kpis,
            }
        except Exception:
            art["scenario_delta"] = {"schema_version": "scenario_delta.v1", "changed_inputs": {}, "changed_kpis": {}}
        results.append(art)

    return results
