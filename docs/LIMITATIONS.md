# SHAMS Known Limitations (community release)

**Version:** see `VERSION`  
**Authority:** Honesty over false confidence — these limitations ship with every scientific handoff.  
**Related:** `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` (community migration), `docs/PROCESS_SURPASS_ROADMAP.md`, `GOVERNANCE.md`, Phase 1 release gate report under `docs/validation/reports/`.

This document is the public limitations list for CONDITIONAL scientific release. It does **not** claim that UKAEA PROCESS is retired or that SHAMS is a drop-in numeric clone of PROCESS.

---

## Scientific / model

1. **L0 is 0-D algebraic feasibility truth**, not a time-domain transport solver, Monte Carlo neutronics core, or coupled plant optimizer. Same inputs → same outputs; NO-SOLUTION is a valid outcome.
2. **Magnets / radial build / structural stress** beyond declared overlays (e.g. v400, v389) remain **engineering proxies**. Do not treat them as PROCESS-class TF/PF/CS closure without Phase 2 DEMO MATCH overlays.
3. **Plant power / availability / cost** KPIs are **proxies** unless an authority overlay explicitly certifies otherwise. Hard-infeasible points must not be read as healthy `Pe_net` / COE — see `plant_kpi_honesty.v1` watermark on run artifacts.
4. **Exhaust / divertor / edge / neutrals** depth is limited (PROCESS is also thin here). Treat divertor claims as surrogate unless an exhaust authority is active and cited.
5. **Neutronics / TBR** overlays (v401/v407/v408 family) are scaffolding / proxy grade for integrated plant studies until DEMO MATCH plant closure is complete.
6. **Confinement scalings** (IPB98, ITER89P, etc.) are empirical envelopes with declared validity regimes — not device-specific validated transport.
7. **PROCESS numeric parity** is **METHOD-ONLY** until a lab-supplied MFILE / reference pack lands. Hashed METHOD-ONLY dossiers exist; **no invented PROCESS numbers**. NUMERIC upgrade is documented in `benchmarks/parity/` and `src/parity_harness/`.

---

## Architecture / product

8. **Optimizers never live inside L0.** Systems Mode / extopt / Pareto propose inputs only; CCFS re-evaluates. `VERIFIED` requires hard-feasible governance constraints.
9. **NiceGUI is the primary studio**; legacy Streamlit remains for compatibility redirects. UI polish and full product QA depth continue under Phase 3.
10. **Stellarator / IFE** branches are out of default mission (IGNORE unless explicitly requested).
11. **MANIFEST_SHA256.txt** may lag uncommitted local dirty trees; regenerate before a tagged public cut (`/shams-patch-release`).

---

## What SHAMS does claim (bounded)

- Deterministic frozen evaluator choke point: `Evaluator.evaluate()` → `hot_ion_point`.
- Explicit hard / diagnostic / ignored constraints; NO-SOLUTION atlas on infeasible artifacts (`no_solution_atlas.v1`).
- CCFS firewall: claims ≠ VERIFIED when hard constraints fail.
- Reproducible artifacts with provenance suitable for reviewer packs (when exported with manifests).

## What SHAMS does **not** claim

- “PROCESS retired” or “PROCESS replaced for all DEMO engineering closure.”
- Bitwise numeric agreement with unpublished or invented MFILE values.
- That plant / magnet / cost proxies are peer-review substitutes for full PROCESS plant breadth **without** Phase 2 overlays and scoped evidence.

---

## Citation posture

Cite `VERSION` + artifact SHA-256 hashes for feasibility studies. Use `CITATION.cff` for software citation metadata. For PROCESS comparisons, attach a parity dossier (METHOD-ONLY or NUMERIC) and declare assumptions — never soft-land infeasibility to look like solver convergence.
