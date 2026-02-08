from __future__ import annotations

"""PROCESS Parity Layer v1: magnets block.

This block exposes a PROCESS-style magnet summary from evaluator outputs.
SHAMS already computes engineering proxies (stresses, stored energy, etc.).

We treat this as a *reporting and costing* interface, not a new physics model.
"""

from typing import Any, Dict


def parity_magnets(inputs: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
    # Pull common magnet metrics if present
    Bt = float(getattr(inputs, "Bt_T", outputs.get("B0_T", outputs.get("Bt_T", 0.0)) ) or 0.0)
    sigma_vm = outputs.get("sigma_vm_MPa", float("nan"))
    sigma_allow = outputs.get("sigma_allow_MPa", float("nan"))
    E_tf_MJ = outputs.get("E_tf_MJ", float("nan"))
    I_tf_A = outputs.get("I_tf_A", float("nan"))
    N_tf_turns = outputs.get("N_tf_turns", float("nan"))
    R_in = outputs.get("R_coil_inner_m", float("nan"))
    t_noncoil = outputs.get("spent_noncoil_m", float("nan"))
    Tcoil_K = outputs.get("Tcoil_K", float("nan"))

    try:
        sigma_vm_f = float(sigma_vm)
        sigma_allow_f = float(sigma_allow)
        margin = (sigma_allow_f - sigma_vm_f) / max(abs(sigma_allow_f), 1e-9)
    except Exception:
        margin = float("nan")

    derived = {
        "Bt_T": float(Bt),
        "sigma_vm_MPa": float(sigma_vm) if sigma_vm == sigma_vm else float("nan"),
        "sigma_allow_MPa": float(sigma_allow) if sigma_allow == sigma_allow else float("nan"),
        "stress_margin_frac": float(margin) if margin == margin else float("nan"),
        "E_tf_MJ": float(E_tf_MJ) if E_tf_MJ == E_tf_MJ else float("nan"),
        "I_tf_A": float(I_tf_A) if I_tf_A == I_tf_A else float("nan"),
        "N_tf_turns": float(N_tf_turns) if N_tf_turns == N_tf_turns else float("nan"),
        "R_coil_inner_m": float(R_in) if R_in == R_in else float("nan"),
        "spent_noncoil_m": float(t_noncoil) if t_noncoil == t_noncoil else float("nan"),
        "Tcoil_K": float(Tcoil_K) if Tcoil_K == Tcoil_K else float("nan"),
    }

    assumptions = {
        "note": "Reporting-only parity block. Uses evaluator-provided magnet proxies.",
        "stress_margin": "(sigma_allow - sigma_vm)/sigma_allow",
    }
    return {"derived": derived, "assumptions": assumptions}
