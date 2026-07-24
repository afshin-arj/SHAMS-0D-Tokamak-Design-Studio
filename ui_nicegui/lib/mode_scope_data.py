"""Mode scope constitutional summaries (ported from ui/icons.py MODE_SCOPE)."""
from __future__ import annotations

MODE_SCOPE: dict[str, dict[str, list[str]]] = {
    "point": {
        "does": [
            "Runs the frozen deterministic evaluator for a single design point.",
            "Reports PASS/FAIL, margins, dominant failure mechanism, and key outputs.",
            "Surfaces which physics blocks were executed (transparency registry).",
        ],
        "does_not": [
            "Does not optimize, iterate, or negotiate constraints.",
            "Does not hide infeasibility via solver convergence or penalty smoothing.",
            "Does not rank designs as best.",
        ],
    },
    "systems_eval": {
        "does": [
            "Performs feasibility-first system-level negotiation as an explanation layer.",
            "Runs Monte Carlo precheck and Newton target solve that propose PointInputs only.",
            "Provides deterministic what-would-need-to-change guidance without modifying truth.",
        ],
        "does_not": [
            "Does not change the frozen evaluator or alter physics truth — solvers propose; L0 re-evaluates.",
            "Does not hide NO-SOLUTION or relax hard constraints inside the evaluator.",
            "Does not claim Newton/MC results are authoritative without a frozen post-apply evaluate.",
        ],
    },
    "opt_lab": {
        "does": [
            "Provides a verdict-first entry to certified search (propose→CCFS).",
            "Routes into Systems Mode, Pareto Lab, and Control Room Certified Search without duplicating them.",
            "States honesty copy: Proposed — SHAMS-certified; VERIFIED vs REJECTED with atlas.",
        ],
        "does_not": [
            "Does not put optimizers inside L0 or negotiate hard constraints.",
            "Does not claim an authoritative global optimum.",
            "Does not certify surrogate or PROCESS MFILE scores without frozen re-eval.",
        ],
    },
    "governance": {
        "does": [
            "Provides governance and operations utilities (run manifests, gatechecks, status).",
            "Surfaces toolchain health and deterministic reproducibility checks.",
            "Centralizes review-room readiness indicators and evidence export.",
        ],
        "does_not": [
            "Does not change model outputs or evaluator behavior.",
            "Does not run background tasks that mutate artifacts.",
            "Does not bypass hygiene or verification requirements.",
        ],
    },
    "bench": {
        "does": [
            "Hosts constitutional benchmarks and parity tracking (e.g., PROCESS parity atlas).",
            "Allows user-supplied reference comparisons with explicit deltas.",
            "Acts as regression safety for the evaluator and UI wiring.",
        ],
        "does_not": [
            "Does not assume external reference values are authoritative without provenance.",
            "Does not auto-fit SHAMS to match other codes by tuning hidden knobs.",
            "Does not import or run external tools implicitly.",
        ],
    },
    "suite": {
        "does": [
            "Provides cross-cutting diagnostics and derived reports on the last Point Designer evaluation.",
            "Exposes plant closure, thermal traces, lifetime budgets, envelope robustness, and export packs.",
            "Exports audit-ready dossiers derived from frozen artifacts.",
        ],
        "does_not": [
            "Does not change truth or reclassify failed points as feasible.",
            "Does not introduce hidden state that affects evaluator outcomes.",
            "Does not add iterative balancing loops inside L0.",
        ],
    },
    "scan": {
        "does": [
            "Maps feasible/empty/fragile regions and dominant limiters over a 2D parameter slice.",
            "Reveals failure order, intent splits, and interpretability tools on frozen truth.",
            "Exports replayable scan artifacts and atlases.",
        ],
        "does_not": [
            "Does not search adaptively or optimize inside truth.",
            "Does not smooth constraints to fill empty regions.",
            "Does not claim global optima or recommend a best design.",
        ],
    },
    "pareto": {
        "does": [
            "Samples the blocking-OK (intent-gate) set (LHS) and reports non-dominated fronts — not L0 FEASIBLE.",
            "Annotates points with dominant constraints, intent, and robust-margin filters.",
            "Exports replayable Pareto artifacts and publication packs.",
        ],
        "does_not": [
            "Does not optimize or relax constraints to reach objectives.",
            "Does not recommend a best design or negotiate infeasibility.",
            "Does not claim exhaustive coverage of continuous design space.",
        ],
    },
    "compare": {
        "does": [
            "Side-by-side diff of two frozen-evaluator artifacts (performance, constraints, inputs).",
            "Reports margin regressions, new failures, and structural/schema changes.",
            "Exports markdown/JSON comparison bundles and applies inputs to Point Designer explicitly.",
        ],
        "does_not": [
            "Does not rank designs or recommend a winner.",
            "Does not re-solve or relax constraints during diff tables.",
            "Does not auto-evaluate after apply-to-Point-Designer handoff.",
        ],
    },
    "trade": {
        "does": [
            "Runs budgeted LHS trade studies over explicit knob sets.",
            "Extracts Pareto subsets only from blocking-OK (intent-gate) sampled points — not L0 FEASIBLE.",
            "Launches firewalled external optimizer kits and study capsules.",
        ],
        "does_not": [
            "Does not modify frozen evaluator truth.",
            "Does not use internal solvers or penalty smoothing.",
            "Does not claim a globally best machine.",
        ],
    },
    "forge": {
        "does": [
            "Compiles reactor intent to candidate PointInputs and runs hybrid Machine Finder searches.",
            "Builds candidate archives, resistance atlases, and replayable run capsules.",
            "Supports explicit promote-to-Point-Designer handoff after frozen-truth audit.",
        ],
        "does_not": [
            "Does not modify frozen evaluator truth or relax constraints silently.",
            "Does not auto-apply candidates — promotion is always explicit.",
            "Does not guarantee feasibility; NO-SOLUTION is valid.",
        ],
    },
    "profile_contracts": {
        "does": [
            "Evaluates frozen truth at finite certified profile/transport corners (C8/C16/C32).",
            "Reports optimistic vs robust feasibility and margin ranges.",
            "Flags certification gaps (optimistic pass, robust fail) with stamped fingerprints.",
        ],
        "does_not": [
            "Does not run transport solvers or Monte Carlo sampling.",
            "Does not modify evaluator outputs — only re-evaluates at declared corners.",
            "Does not negotiate constraint violations across the envelope.",
        ],
    },
    "campaign_pack": {
        "does": [
            "Exports deterministic campaign bundles for external optimizers.",
            "Runs batch evaluation locally with the frozen evaluator.",
            "Keeps optimization firewalled: optimizers propose; SHAMS evaluates.",
        ],
        "does_not": [
            "Does not run internal optimization or adjust truth for objectives.",
            "Does not hide infeasibility via solvers.",
            "Does not mutate evaluator state.",
        ],
    },
    "parity_harness": {
        "does": [
            "Runs deterministic benchmark suites and exports parity artifacts.",
            "Produces SHAMS artifacts and optional PROCESS delta dossiers.",
            "Treats discrepancies as mechanisms to explain, not tuning targets.",
        ],
        "does_not": [
            "Does not run PROCESS internally or assume it is authoritative without provenance.",
            "Does not tune SHAMS to match other codes.",
            "Does not modify the frozen evaluator.",
        ],
    },
}
