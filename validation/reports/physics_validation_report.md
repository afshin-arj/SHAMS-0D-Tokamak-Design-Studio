# SHAMS–FUSION-X Physics Validation Report
**Generated:** 2026-01-06

## 1. Scope
This report documents quantitative validation of SHAMS–FUSION-X physics models against canonical fusion literature.
References are *validation-only* and never active model inputs.

## 2. Validation Philosophy
- Constraint-first, feasibility-first
- Explicit non-feasibility
- Invariant-based validation (not curve fitting)
- Mode independence (Point / Systems / Scan / Pareto)

## 3. Physics Models & Invariants

### 3.1 Greenwald Density Limit
- Invariant: n / n_G ≤ specified fraction
- Reference: Greenwald (1988)
- Status: PASS (definition-level invariant)

### 3.2 Normalized Beta (β_N)
- Invariant: β_N = β (%) a B / I_p
- Reference: Troyon (1984)
- Status: PASS (normalization invariant)

### 3.3 Heat Flux Width (λ_q)
- Envelope comparison only (no tuning)
- References: Eich, Goldston
- Status: PENDING quantitative envelope check

### 3.4 Bootstrap Fraction
- Aspect ratio and collisionality trends
- Reference: Sauter
- Status: PENDING quantitative comparison

### 3.5 REBCO Limits
- Surface field and current density envelopes
- Reference: ARC / REBCO literature
- Status: PENDING quantitative comparison

## 4. UI Mode Consistency
All UI modes call identical physics evaluators and constraint logic.
Invariant results are mode-independent.

## 5. Explicit Non-Claims
- No turbulence-resolved transport
- No time-dependent MHD
- No empirical tuning beyond published envelopes

## 6. Conclusion
SHAMS–FUSION-X physics is definitionally correct and solver-honest.
Quantitative envelope validation is ongoing.

## 7. Quantitative Benchmark Status (Populated)
- λq (Eich proportionality): computed `C_Eich` across golden artifacts; mean=0.164634, spread=7.61% (coefficient absent → ratio/consistency benchmark).
- Bootstrap (Sauter): SHAMS outputs recorded; reference numeric band extraction pending.
- REBCO (Senatore): SHAMS margin recorded; reference surface extraction pending.
- ARC point: extraction pending.
