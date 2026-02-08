# SHAMS–FUSION-X upgrade plan (inspired by PROCESS, still independent)

This document proposes an upgrade sequence that preserves SHAMS’ current behavior while improving
solver robustness, maintainability, UI clarity, and long-term extensibility.

## Goals

- Decision-grade solver diagnostics (why it converged, why it failed)
- Pluggable solver backends behind a stable interface
- Constraint registry to standardize packing/scaling and per-constraint reporting
- UI-integrated documentation and “what am I looking at?” guidance

## Deliverables (implemented as scaffolds)

1. **Solver adapter scaffold**
   - A small `SolverBackend` protocol and `SolverRequest` dataclass
   - An adapter that wires current SHAMS solvers through the protocol (no behavior change)

2. **Constraint registry scaffold**
   - `ConstraintSpec` and `ConstraintRegistry` for eq/ineq partitioning and residual packing
   - A compatibility helper that can build a registry-backed view from the existing constraint list

3. **Documentation**
   - `docs/PROCESS_lessons.md`
   - This plan document
   - UI “Docs” tab to read these documents inside Streamlit

4. **UI improvements**
   - A documentation tab in the UI
   - Contextual help text around solver/constraints concepts
   - Links to local docs so users don’t have to leave the app

## Next steps (when you choose to change behavior)

- Add optional analytic/AD Jacobians (hybrid analytic + finite difference fallback)
- Add solve-diagnostics artifact JSON (conditioning, scaling, per-constraint contributions)
- Add envelope-based validation harness and “golden solve” tests
