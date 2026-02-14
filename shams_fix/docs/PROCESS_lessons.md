# Lessons from UKAEA PROCESS (for SHAMS–FUSION-X)

This note summarizes architectural patterns observed in PROCESS (Python port) that are valuable to *learn from*,
while keeping SHAMS fully independent.

## 1. Clear seams: solver ↔ evaluator ↔ models

PROCESS makes the mapping from an iteration vector to residuals a *single, testable choke-point*.
This supports:
- consistent scaling
- solver diagnostics
- easy backend swapping
- caching/memoization in one place

**SHAMS takeaway:** keep physics/engineering models pure; put “vector packing + residual assembly” in one layer.

## 2. Solver backends behind a small adapter

PROCESS wraps solver choices behind a uniform API. Even when the backend changes, the *problem definition* stays stable.

**SHAMS takeaway:** create a small adapter protocol for solvers and standardize the `SolveResult`.

## 3. Constraints as structured objects, not scattered checks

PROCESS treats constraints as a collection with metadata and consistent packing order.

**SHAMS takeaway:** introduce a constraint registry that can:
- classify eq vs ineq
- scale/normalize residuals
- produce per-constraint diagnostics artifacts

## 4. “Canonical artifacts” are first-class

PROCESS produces standard outputs (MFILE-like) and organizes them with dedicated IO helpers.

**SHAMS takeaway:** keep pushing artifact-first; add solve-diagnostics JSON alongside existing run artifacts.

## 5. Tests that guard solver stability

PROCESS includes integration-level tests that prevent silent regressions.

**SHAMS takeaway:** add “golden solve” tests for reference envelopes and “batch robustness” tests for studies.

## What not to copy

PROCESS inherits historic global data-structures. SHAMS should *avoid* global mutable state and keep its clean,
explicit provenance approach.
