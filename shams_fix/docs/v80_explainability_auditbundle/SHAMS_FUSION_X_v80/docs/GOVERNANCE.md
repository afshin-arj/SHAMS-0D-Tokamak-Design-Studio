# Governance (Journal / GitHub / Regulator-Ready)

## Authoritative branch policy
The mainline release is **authoritative** and **frozen by default**:
- Physics frozen
- Solver logic frozen
- Numerical assumptions frozen

Any change that could alter results requires an explicit change proposal and a version fork.

## Change control
A change proposal must include:
1. Motivation and scope
2. Risk classification (UI/telemetry-only vs scientific behavior)
3. Reproduction plan (frozen benchmarks re-run)
4. Artifact comparison (before/after)
5. Explicit statement of what **did not** change

## Transparency guarantees
Each release must publish:
- Solver backend selection and versions
- Constraint set identifiers / hashes where applicable
- Benchmark provenance and citations
- Performance telemetry disclosure
- “Known limits” and “Not intended for” statements

## Research forks
Exploratory work occurs in research forks that are explicitly marked:
- **Non-authoritative**
- **Not benchmark-equivalent**
- **Not suitable for publication/regulatory review**
