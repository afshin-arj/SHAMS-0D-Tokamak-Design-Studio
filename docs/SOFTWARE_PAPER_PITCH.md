# SHAMS Software-Paper Pitch (JOSS-style skeleton)

**Independence Phase 3.2 deliverable.** Target venue class: JOSS (Journal of Open Source Software) or an equivalent open research-software venue. This is a **pitch + skeleton**, not a submitted manuscript. Submission is gated on the APPROVED-release path in `docs/RELEASE_ARCHIVAL_CHECKLIST.md` (tag + Zenodo DOI first).

---

## Working title

**SHAMS: a feasibility-authoritative 0-D tokamak design studio with a frozen deterministic evaluator and NO-SOLUTION as a first-class scientific outcome**

## Summary (draft)

SHAMS is an open-source tokamak 0-D systems studio built around a single frozen evaluation choke point (`Evaluator.evaluate()` → `hot_ion_point`): same inputs always produce same outputs, with no hidden solvers, smoothing, or infeasibility masking inside the truth path. Constraints are explicitly typed (hard / diagnostic / ignored), infeasibility is reported and mechanism-attributed via a NO-SOLUTION atlas rather than negotiated away, and external optimizers — including UKAEA PROCESS — may only *propose* inputs that SHAMS re-evaluates and certifies (CCFS). Engineering and plant depth (magnets, radial build, plant power ledger, availability→OPEX/LCOE, bottom-up costing) is provided as versioned, provenance-stamped authority overlays that are OFF by default and never alter frozen truth.

## Statement of need (draft)

Fusion systems studies today largely depend on optimizer-centric system codes, most prominently UKAEA PROCESS, which answer *"what design optimizes a figure of merit under solvable constraints?"* using solvers (VMCON/fsolve) embedded in a mutable model graph. That architecture makes three scientific questions hard to answer credibly:

1. **Which designs are admissible at all — and which cannot exist?** (Infeasibility is avoided or re-negotiated, not attributed.)
2. **Why exactly did a design fail?** (Failure attribution is entangled with solver trajectories.)
3. **Can a reviewer reproduce the claim without trusting the optimization path?** (Convergence artifacts are not deterministic feasibility evidence.)

SHAMS addresses this gap as a *feasibility authority*: a deterministic evaluator with explicit constraint governance, hash-manifested reproducible artifacts (VERSION + SHA-256), and honest KPI watermarks so hard-infeasible points never display healthy net-electric or cost figures. It complements rather than clones PROCESS: optimizers propose, SHAMS certifies.

## Functionality (draft bullet inventory)

- Frozen L0 evaluator; NO-SOLUTION atlas (`no_solution_atlas.v1`) on every hard-infeasible artifact.
- Typed constraint ontology with governance (`GOVERNANCE.md`); policy tiers.
- CCFS certified-solve firewall: external proposals re-evaluated; VERIFIED requires hard feasibility.
- Versioned authority overlays (magnets v410, machine build v412, plant Sankey ledger v419, availability→OPEX/LCOE v420, bottom-up costing v421, …) — OFF by default, provenance-stamped, PROXY-labeled.
- Plant KPI honesty (`plant_kpi_honesty.v1`): watermarked Pe_net / COE / LCOE on infeasible points.
- Interactive studio (NiceGUI decks: Point Designer, System Suite, Scan Lab, Control Room) plus scriptable API.
- Reproducibility tooling: golden regression baselines, verification harness, SHA-256 reviewer packs, `CITATION.cff` / `.zenodo.json`.
- PROCESS migration path: `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` (IN.DAT→`PointInputs`, MFILE→artifacts).

## Comparison stance vs PROCESS (must stay honest)

| | PROCESS | SHAMS |
|--|---------|-------|
| Core question | Optimize a FoM under negotiated constraints | Which designs are admissible, how robust, why others fail |
| Numerics | Solver inside the model graph | Frozen evaluator; solvers propose only |
| Failure | Avoided / re-run | NO-SOLUTION + mechanism attribution |
| Reproducibility claim | Convergence output | Deterministic re-evaluation from cited inputs |

The paper must state explicitly:

- PROCESS numeric parity is **METHOD-ONLY** (hashed method dossiers; no lab MFILE numbers reproduced or invented) until a lab-supplied reference pack lands.
- Plant/magnet/cost overlays are **proxy-grade** engineering models with declared provenance — not PROCESS-depth engineering closure.
- SHAMS does **not** claim PROCESS retirement; it claims a complementary, citable feasibility-authority role.
- Release status at pitch time is **CONDITIONAL** (`docs/validation/reports/scientific_release_readiness_20260716.md`); submission requires APPROVED + DOI.

## Acknowledgement of prior art (draft list)

PROCESS (Kovari et al.; UKAEA), SYCOMORE, BLUEPRINT/bluemira, other 0-D/systems frameworks — to be completed with full references at manuscript time.

## Submission checklist (JOSS-style)

- [ ] APPROVED release verdict (gates G1–G8 in `docs/RELEASE_ARCHIVAL_CHECKLIST.md`)
- [ ] Tagged release + Zenodo DOI minted; DOI recorded in `CITATION.cff`
- [ ] `paper.md` + `paper.bib` authored from this skeleton (statement of need, functionality, comparison, references)
- [ ] Repository review-ready: LICENSE (Apache-2.0), install docs, example usage, test instructions, contribution guidelines
- [ ] ORCID iDs for authors (real, not placeholders)
- [ ] Claims audit: no PROCESS-retired claim, no NUMERIC-parity claim without MFILE, CONDITIONAL/APPROVED status stated truthfully
