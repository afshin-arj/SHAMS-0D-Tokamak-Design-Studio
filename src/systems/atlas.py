from __future__ import annotations

from typing import Dict, Tuple, Any
import math

try:
    from evaluator.core import Evaluator
except Exception:
    from evaluator.core import Evaluator  # type: ignore

try:
    from constraints.constraints import evaluate_constraints
except Exception:
    from constraints.constraints import evaluate_constraints  # type: ignore

try:
    from models.inputs import PointInputs
except Exception:
    from models.inputs import PointInputs  # type: ignore


def _apply_vars(base: PointInputs, var_values: Dict[str, float]) -> PointInputs:
    d = dict(base.__dict__)
    d.update({k: float(v) for k, v in var_values.items()})
    return PointInputs(**d)


def compute_micro_atlas(
    base: PointInputs,
    variables: Dict[str, Tuple[float, float, float]],
    var_x: str,
    var_y: str,
    *,
    nx: int = 15,
    ny: int = 15,
    evaluator: Evaluator | None = None,
) -> Dict[str, Any]:
    """Compute a small feasibility atlas (2D slice) over two variables.

    Returns a dict with grids:
      feasible[nx][ny] bool
      dominant[nx][ny] str (dominant hard constraint name or 'ok')
      min_margin[nx][ny] float
      xs, ys arrays

    Deterministic and suitable for quick UI visualization.
    """
    if var_x not in variables or var_y not in variables:
        return {'ok': False, 'reason': 'var_not_in_variables'}

    ev = evaluator or Evaluator(cache_enabled=True, cache_max=4096)

    _, xlo, xhi = variables[var_x]
    _, ylo, yhi = variables[var_y]
    xlo, xhi = float(xlo), float(xhi)
    ylo, yhi = float(ylo), float(yhi)

    xs = [xlo + (xhi - xlo) * (i / (nx - 1)) for i in range(nx)] if nx > 1 else [0.5*(xlo+xhi)]
    ys = [ylo + (yhi - ylo) * (j / (ny - 1)) for j in range(ny)] if ny > 1 else [0.5*(ylo+yhi)]

    feasible = [[False for _ in range(ny)] for __ in range(nx)]
    dominant = [['' for _ in range(ny)] for __ in range(nx)]
    min_margin = [[float('nan') for _ in range(ny)] for __ in range(nx)]

    # Hold all other variables at midpoint
    mid = {k: 0.5*(float(variables[k][1]) + float(variables[k][2])) for k in variables.keys()}

    for i, xv in enumerate(xs):
        for j, yv in enumerate(ys):
            assign = dict(mid)
            assign[var_x] = float(xv)
            assign[var_y] = float(yv)
            inp = _apply_vars(base, assign)
            try:
                out = ev.evaluate(inp).out
            except Exception:
                out = {}
            try:
                cons = evaluate_constraints(out)
            except Exception:
                cons = []

            hard = [c for c in cons if str(getattr(c,'severity','soft')) == 'hard']
            worst_name = 'ok'
            worst_margin = math.inf
            ok = True
            for c in hard:
                passed = bool(getattr(c,'passed', False))
                m = getattr(c,'margin', None)
                try:
                    mv = float(m) if m is not None else float('nan')
                except Exception:
                    mv = float('nan')
                if not math.isfinite(mv):
                    mv = -1e3
                if mv < worst_margin:
                    worst_margin = mv
                    worst_name = str(getattr(c,'name',''))
                if not passed:
                    ok = False
            feasible[i][j] = bool(ok)
            dominant[i][j] = 'ok' if ok else worst_name
            min_margin[i][j] = float(worst_margin if math.isfinite(worst_margin) else float('nan'))

    return {
        'ok': True,
        'var_x': var_x,
        'var_y': var_y,
        'xs': xs,
        'ys': ys,
        'feasible': feasible,
        'dominant': dominant,
        'min_margin': min_margin,
    }
