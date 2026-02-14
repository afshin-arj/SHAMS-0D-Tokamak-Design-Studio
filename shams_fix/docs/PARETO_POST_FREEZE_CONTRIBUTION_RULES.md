# Pareto Mode Post-Freeze Contribution Rules

## Guiding Principle

Pareto Mode is frozen to preserve semantic stability, reproducibility, and scientific trust.
Contributions must not alter meaning, interpretation, or evaluator interaction.

## Allowed Contributions
- Documentation improvements
- Teaching and onboarding materials
- UI clarity improvements that do not change semantics
- Bug fixes that preserve behavior and determinism
- Performance improvements that do not change results
- Backward-compatible artifact readers or upgraders

## Disallowed Contributions
- Optimization/solver logic or recommendation engines
- Constraint relaxation or policy modification
- Weighted objective sliders implying a single “best” design
- Smoothing/interpolation of evaluator results that changes meaning
- Non-deterministic behavior

## Major Version Changes
Any change affecting interpretation, classification, determinism, artifact meaning, or evaluator interaction requires a formal proposal and a new major version.

