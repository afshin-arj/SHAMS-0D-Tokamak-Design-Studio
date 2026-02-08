# Contributing to SHAMS

Thanks for considering a contribution.

SHAMS has **non-negotiable governance laws** that preserve determinism, audit safety, and scientific defensibility.
If a proposed change violates these laws, it will not be merged.

## Non-negotiable laws

### 1) Frozen Truth (no internal solvers)
- The evaluator is **algebraic** and **deterministic**.
- **No Newton solvers, no iteration, no hidden relaxation, no smoothing, no penalties-as-negotiation**.
- Same inputs must produce the same outputs (bitwise reproducible where practical).

### 2) Separation of concerns
- Truth (evaluator) must not depend on exploration or optimization paths.
- Optimization must remain **external-only** and firewalled.

### 3) Feasibility-first
- Constraints are explicit; violations are reported, not negotiated.

### 4) Audit/reviewer safety
- Changes must be testable, replayable, and explainable.
- Add/update documentation and patch notes for user-visible behavior.

## Where you can safely contribute

- UI improvements that do not change truth
- Governance/reporting improvements (evidence packs, manifests, provenance)
- New diagnostics and validators
- Documentation, examples, and tests
- External optimizer kits (clients) that do not mutate truth

## Areas with extra scrutiny (often blocked)

The following directories are treated as **truth-critical** and are subject to the strictest review:
- `src/`, `physics/`, `constraints/`, `models/`, `profiles/`, `schemas/`

Edits here require:
- explicit model-spec justification
- deterministic gatechecks
- conservative closures
- updated validity-domain notes where applicable

## Development workflow

1. Create a virtual environment.
2. Install requirements: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Run hygiene cleaner: `python scripts/hygiene_clean.py`
5. Ensure no forbidden artifacts (`__pycache__`, `.pytest_cache`, `*.pyc`) appear.

## Reporting bugs

Open an issue with:
- SHAMS version (`VERSION`)
- inputs / scenario used
- expected vs actual behavior
- relevant log snippets or evidence pack IDs (if any)

