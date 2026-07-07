"""Mode scope constitutional summaries (ported from ui/icons.py MODE_SCOPE)."""
from __future__ import annotations

MODE_SCOPE: dict[str, dict[str, list[str]]] = {
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
            "Samples the feasible set (LHS) and reports non-dominated trade-off fronts.",
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
            "Extracts Pareto subsets only from feasible sampled points.",
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
