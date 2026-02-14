# Systems Mode (PROCESS-inspired)

SHAMS Systems Mode implements a lightweight, Windows-native analogue of a systems-code workflow:

- Choose **targets** (e.g. `Q_DT_eqv`, `H98`, `P_e_net_MW`)
- Choose **iteration variables** (e.g. `Ip_MA`, `fG`, `Paux_MW`) and bounds
- Solve a small coupled nonlinear system using a damped Newton method with finite-difference Jacobian
- Report **constraint margins** (hard + soft screens) and export a canonical run artifact JSON

## Solver robustness controls (advanced)

Systems Mode uses a bounded damped-Newton solve. In addition to tolerance and damping, SHAMS supports an optional **trust-region step cap**:

- **Trust-region Δ (scaled)** (`trust_delta`): caps `max(|dx_scaled|)` per iteration in scaled variable space.
  - Lower Δ → safer, smaller steps (helpful for brittle / near-infeasible solves)
  - Higher Δ → more aggressive steps (faster when well-conditioned)

When enabled, the solver trace includes explicit `trust_region` events (Δ and whether the step was clipped), plus `linesearch` events indicating progress or `no_descent` termination.



This is conceptually similar to PROCESS's constraint-driven closure, but does **not** call PROCESS or Fortran.

Outputs are written into the **run artifact** (SHAMS-native analogue of PROCESS's MFILE) and can be used for:
- summary reports
- radial build plots
- power-balance Sankey plots
- scans and Pareto studies
