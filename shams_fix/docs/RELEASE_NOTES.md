# SHAMS v281.1 — UI Icon Coverage + Expert Cockpits for Phase/UQ (2026-02-06)

- New: **v280.x Quasi-Static Phase Envelopes** implemented as a deterministic outer-loop (`src/phase_envelopes/`).
  - Ordered phases with explicit input overrides and optional policy-tier overrides.
  - Each phase evaluated independently against the frozen truth; **worst phase** determines envelope verdict.
  - No ODEs, no PF solvers, no time-domain integration, no hidden iteration.

- New: **v281.x Uncertainty Contracts (Interval Truth)** implemented as deterministic corner enumeration (`src/uq_contracts/`).
  - User-declared input intervals → deterministic 2^N corner evaluation.
  - Verdicts: **ROBUST_PASS / FRAGILE / FAIL**.
  - No probability, no Monte Carlo, no statistics.

- UI: surfaced in **Point Designer** as a deck selector:
  - 🧭 Truth Console / 🗺️ Phase Envelopes / 🛡️ Uncertainty Contracts
  - Also available in **System Suite** as two additional tabs for workflow continuity.

- Audit artifacts:
  - Exportable, hash-manifested ZIPs for Phase Envelopes and Uncertainty Contracts (`tools/phase_envelopes.py`, `tools/uncertainty_contracts.py`).

- Tests:
  - Added `tests/test_phase_uq_contracts.py` to assert deterministic execution and corner counts.

Author: © 2026 Afshin Arjhangmehr

# Release notes generation

SHAMS includes a lightweight release-notes generator that summarizes:
- **Structural changes** (constraints set/meta changes, model card hash/version changes, schema_version changes)
- **Benchmark numeric deltas** that exceed tolerances (from `benchmarks/last_diff_report.json`)

## Typical workflow

1. In the *new* version repo, run benchmarks:

```bash
python benchmarks/run.py --write-diff
```

2. Generate markdown release notes comparing two repos:

```bash
python tools/release_notes.py --old ..\SHAMS_old --new . --out RELEASE_NOTES.md
```

## Notes

- Structural diffs use the full golden artifacts under `benchmarks/golden_artifacts/`.
- Numeric diffs use the diff report JSON, if available.
