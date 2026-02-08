from __future__ import annotations
from typing import Callable, Dict, Optional, Iterator, Tuple
import math

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore
from physics.hot_ion import hot_ion_point

def solve_Ip_fG_for_H98_Q(
    base: PointInputs,
    target_H98: float,
    target_Q: float,
    Ip0: float,
    fG0: float,
    Ip_bounds: Tuple[float,float],
    fG_bounds: Tuple[float,float],
    max_iter: int = 25,
    tol: float = 1e-3,
    damping: float = 0.6,
) -> Tuple[PointInputs, Dict[str,float]]:
    """Coupled solve for (Ip, fG) to match (H98, Q).

    This is a damped finite-difference Newton method with bounds.
    It is designed to be more robust than nested bisections for scans.
    """
    Ip = float(Ip0)
    fG = float(fG0)

    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    for it in range(max_iter):
        inp = base.__class__(**{**base.__dict__, "Ip_MA": Ip, "fG": fG})
        out = hot_ion_point(inp)
        H = out.get("H98", float("nan"))
        Q = out.get("Q_DT_eqv", float("nan"))

        r1 = H - target_H98
        r2 = Q - target_Q
        if math.isfinite(r1) and math.isfinite(r2) and (abs(r1) < tol) and (abs(r2) < tol):
            return inp, out

        # finite differences
        dIp = max(1e-3, 0.02*abs(Ip))
        dfG = max(1e-4, 0.02*abs(fG) if fG!=0 else 0.02)

        inp_Ip = base.__class__(**{**base.__dict__, "Ip_MA": clamp(Ip+dIp,*Ip_bounds), "fG": fG})
        o_Ip = hot_ion_point(inp_Ip)
        H_Ip = o_Ip.get("H98", H)
        Q_Ip = o_Ip.get("Q_DT_eqv", Q)

        inp_fG = base.__class__(**{**base.__dict__, "Ip_MA": Ip, "fG": clamp(fG+dfG,*fG_bounds)})
        o_fG = hot_ion_point(inp_fG)
        H_fG = o_fG.get("H98", H)
        Q_fG = o_fG.get("Q_DT_eqv", Q)

        J11 = (H_Ip - H)/dIp
        J21 = (Q_Ip - Q)/dIp
        J12 = (H_fG - H)/dfG
        J22 = (Q_fG - Q)/dfG

        det = J11*J22 - J12*J21
        if not math.isfinite(det) or abs(det) < 1e-12:
            # fallback: small damped steps toward reducing residuals
            Ip = clamp(Ip - 0.1*r1, *Ip_bounds)
            fG = clamp(fG - 0.05*r2/max(target_Q,1e-9), *fG_bounds)
            continue

        dIp_new = (-r1*J22 + r2*J12)/det
        dfG_new = (-J11*r2 + J21*r1)/det

        Ip = clamp(Ip + damping*dIp_new, *Ip_bounds)
        fG = clamp(fG + damping*dfG_new, *fG_bounds)

    # final
    inp = base.__class__(**{**base.__dict__, "Ip_MA": Ip, "fG": fG})
    out = hot_ion_point(inp)
    return inp, out

def solve_Ip_fG_for_H98_Q_stream(**kwargs) -> Iterator[Dict[str, float]]:
    """Streaming wrapper for UI progress."""
    base = kwargs["base"]
    target_H98 = kwargs["target_H98"]
    target_Q = kwargs["target_Q"]
    Ip0 = kwargs.get("Ip0", base.Ip_MA)
    fG0 = kwargs.get("fG0", base.fG)
    Ip_bounds = kwargs["Ip_bounds"]
    fG_bounds = kwargs["fG_bounds"]
    max_iter = kwargs.get("max_iter", 25)
    tol = kwargs.get("tol", 1e-3)

    inp = base
    out = {}
    Ip = Ip0
    fG = fG0
    for it in range(max_iter):
        inp = base.__class__(**{**base.__dict__, "Ip_MA": Ip, "fG": fG})
        out = hot_ion_point(inp)
        H = out.get("H98", float("nan"))
        Q = out.get("Q_DT_eqv", float("nan"))
        yield {"event":"iter","it":it,"Ip_MA":Ip,"fG":fG,"H98":H,"Q":Q}

        r1 = H - target_H98
        r2 = Q - target_Q
        if math.isfinite(r1) and math.isfinite(r2) and (abs(r1)<tol) and (abs(r2)<tol):
            yield {"event":"done","it":it}
            return
        # simple relaxation toward targets
        Ip = max(Ip_bounds[0], min(Ip_bounds[1], Ip - 0.2*r1))
        fG = max(fG_bounds[0], min(fG_bounds[1], fG - 0.05*r2/max(target_Q,1e-9)))
    yield {"event":"fail","reason":"max_iter","it": float(it), "max_iter": float(max_iter)}
