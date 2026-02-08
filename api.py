
"""
FastAPI service wrapper for Phase-1 physics.

This is optional for the Streamlit UI (which imports src directly),
but it is included to support future web UIs and job execution.
"""
from __future__ import annotations

import os, sys
from typing import Any, Dict, Optional, List

from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from phase1_core import PointInputs, hot_ion_point

app = FastAPI(title="Phase-1 Clean Point Design API", version="0.1.0")

class PointSpec(BaseModel):
    # Mirror PointInputs fields. Keep it permissive: extra knobs are allowed.
    R0_m: float = 1.81
    a_m: float = 0.62
    kappa: float = 1.8
    Bt_T: float = 10.0
    Ip_MA: float = 40.0
    Ti_keV: float = 12.0
    fG: float = 0.8
    t_shield_m: float = 0.8
    Paux_MW: float = 48.0
    Ti_over_Te: float = 2.0

    zeff: float = 1.8
    dilution_fuel: float = 0.85
    extra_rad_factor: float = 0.2
    alpha_loss_frac: float = 0.05

    C_bs: float = 0.15

    require_Hmode: bool = False
    PLH_margin: float = 0.0
    A_eff: float = 2.0

    use_lambda_q: bool = False
    lambda_q_factor: float = 1.0

    # Allow arbitrary clean-design knobs from phase1_systems (radial build, HTS, etc.)
    model_config = {"extra": "allow"}

class PointResponse(BaseModel):
    outputs: Dict[str, Any]

@app.post("/point/evaluate", response_model=PointResponse)
def point_evaluate(spec: PointSpec):
    inp = PointInputs(**spec.model_dump())
    out = hot_ion_point(inp)
    return {"outputs": out}
