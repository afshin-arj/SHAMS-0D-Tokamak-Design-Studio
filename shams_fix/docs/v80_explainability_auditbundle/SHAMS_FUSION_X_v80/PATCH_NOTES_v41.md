# PATCH NOTES v41 — Point Designer no-bracket clamp fix

## Problem
Point Designer point targeting would hard-fail with `reason=no_bracket` when the requested confinement target `H98`
(or Q target during the inner fG solve) was outside the achievable range **within the user-specified bounds**.

This caused `Ip=nan, fG=nan` even though a physically valid point exists at the nearest bound.

## Fix (non-breaking, feasibility-first)
- When `H98(Ip)` does not bracket the requested `target_H98` inside `[Ip_min, Ip_max]`, the solver now **clamps**
  to the nearest bound (smallest |residual|) and returns a valid point.
- When `Q(fG)` does not bracket the requested `target_Q` inside `[fG_min, fG_max]`, the inner solver now **clamps**
  to the nearest bound and returns a valid point.

## Auditability
The returned output dict includes explicit flags:
- `_solver_clamped`, `_solver_clamped_on`, `_H98_target`, `_H98_at_bound`, `_H98_residual`
- `_solver_clamped_Q`, `_solver_clamped_Q_on`, `_Q_target`, `_Q_at_bound`, `_Q_residual`

The UI displays a warning when clamping occurs.
