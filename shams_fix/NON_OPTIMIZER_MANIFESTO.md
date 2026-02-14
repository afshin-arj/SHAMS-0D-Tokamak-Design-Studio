# SHAMS Non‑Optimizer Manifesto (v120)

SHAMS is **not** an optimizer.

## What SHAMS does
- Evaluates physics deterministically for explicit inputs.
- Enforces feasibility explicitly and transparently.
- Builds evidence artifacts (run artifacts, atlases, packs).
- Supports preference-aware annotation (post-processing only).
- Treats external optimizers as downstream proposal generators.

## What SHAMS will not do
- No embedded black-box optimization selecting a “best design”.
- No hidden weighted objectives driving solver behavior.
- No stochastic Monte Carlo interpreted as probability without explicit modeling.

## Why
Optimization-first tools can conceal assumptions and produce non-auditable conclusions.
SHAMS prioritizes auditability, reproducibility, and scientific honesty.

