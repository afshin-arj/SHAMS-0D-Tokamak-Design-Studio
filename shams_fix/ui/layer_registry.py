"""UI Layer Registry (v120)

A tiny registry that keeps SHAMS as a single UI with orthogonal layer panels.
Additive only; does not alter physics or solver behavior.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional

@dataclass(frozen=True)
class LayerEntry:
    layer: str
    title: str
    description: str
    panel_fn_name: str  # function defined in ui/app.py

def get_layers() -> List[LayerEntry]:
    # L0 panels are defined elsewhere in app; we list constitutional and higher layers here.
    return [
        LayerEntry("L9", "Panel Availability Map (v175)", "Self-explaining map of which panels are available and why (missing artifacts / blocked / N/A).", "_v175_panel_availability_map_panel"),

        LayerEntry("L7", "Feasibility Atlas (v156)", "Sample 2D design space slices; export feasibility field + atlas bundle.", "_v156_feasibility_atlas_panel"),
        LayerEntry("L7", "Feasibility Boundary (v157)", "Extract boundary curves from feasibility fields (grid interpolation).", "_v157_feasibility_boundary_panel"),
        LayerEntry("L7", "Constraint Dominance Topology (v158)", "Map dominant violated constraints and connected infeasible regions.", "_v158_constraint_dominance_panel"),
        LayerEntry("L7", "Feasibility Completion Evidence (v159)", "Search feasible completions from partial specs; witness + bottlenecks.", "_v159_feasibility_completion_panel"),
        LayerEntry("L7", "Completion Frontier (v161)", "Minimal-change feasible witness and distance–margin frontier.", "_v161_completion_frontier_panel"),
        LayerEntry("L7", "Directed Local Search (v162)", "Bounded coordinate search to reach feasibility from a baseline guess.", "_v162_directed_local_search_panel"),
        LayerEntry("L7", "Completion Pack (v163)", "Actionable recipe: witness + knob ranking + bounds recommendations.", "_v163_completion_pack_panel"),
        LayerEntry("L7", "Sensitivity + Bottleneck Attribution (v164)", "Local finite-difference leverage ranking around witness.", "_v164_sensitivity_panel"),
        LayerEntry("L8", "Feasibility Boundary Atlas (v169)", "Publishable figure pack + manifest (consistent captions).", "_v169_atlas_panel"),
        LayerEntry("L8", "Study Protocol Generator (v165)", "Journal-ready Methods protocol with protocol hash.", "_v165_study_protocol_panel"),
        LayerEntry("L8", "Reproducibility Lock + Replay Checker (v166)", "Freeze a run into a lockfile and verify replay within tolerances.", "_v166_repro_lock_panel"),
        LayerEntry("L8", "Design Study Authority Pack (v167)", "One ZIP bundle containing protocol + lock + replay + completion + sensitivity (+ certificate).", "_v167_authority_pack_panel"),
        LayerEntry("L8", "Citation-Grade Study Reference (v168)", "Study ID + CITATION.cff + BibTeX.", "_v168_citation_panel"),
        LayerEntry("L8", "PROCESS Downstream Export (v170)", "Export SHAMS studies into PROCESS-like tables (SHAMS upstream).", "_v170_process_export_panel"),
        LayerEntry("L7", "Feasibility Authority Certificate (v160)", "Issue authority certificates from feasibility fields (dense sampling basis).", "_v160_authority_certificate_panel"),

        LayerEntry("L6", "DOI Export Helper (v153)", "Export Zenodo/Crossref metadata from study registry.", "_v153_doi_export_panel"),
        LayerEntry("L6", "Caption Editor (v154)", "Edit captions for paper pack figures/tables.", "_v154_caption_editor_panel"),
        LayerEntry("L6", "Multi-Study Pack (v155)", "Compare multiple paper packs; produce comparison bundle + integrity.", "_v155_multi_study_pack_panel"),
        LayerEntry("L5", "Run Integrity Lock (v152)", "Lock/verify run artifact hashes; produce VERIFIED/MODIFIED status.", "_v152_integrity_panel"),
        LayerEntry("L5", "Publishable Study Kit (v148–v151)", "Paper pack export with registry + integrity + captions + session figures/tables.", "_v150_publishable_study_kit_panel"),
        LayerEntry("L4", "Feasibility Completion (v146–v147)", "Bridge witness + auto-shrunk certified safe domain.", "_v147_feasibility_completion_panel"),
        LayerEntry("L4", "Topology Certificate (v145)", "Citable certificate for feasible-set topology (islands) from deep-dive.", "_v145_topology_certificate_panel"),
        LayerEntry("L4", "Feasibility Deep Dive (v142–v144)", "Topology maps, constraint interactions, and interval feasibility certificates.", "_v144_deepdive_panel"),
        LayerEntry("L4", "Robustness Certificate (v141)", "Certificate combining feasibility + sensitivity into robustness indices.", "_v141_robustness_panel"),
        LayerEntry("L4", "Sensitivity Maps (v140)", "Finite perturbation fragility envelopes for feasibility.", "_v140_sensitivity_panel"),
        LayerEntry("L4", "Feasibility Certificate (v139)", "Generate immutable feasibility certificates for runs.", "_v139_feasibility_certificate_panel"),
        LayerEntry("L4", "Feasibility Completion Advanced (v134–v138)", "Atlas, guided completion, repair, compression, and handoff.", "_v138_fc_superpanel"),
        LayerEntry("L4", "Feasibility Completion (v133)", "Partial design inference: find feasible completions from incomplete inputs.", "_v133_fc_panel"),
        LayerEntry("L4", "Study Matrix Builder v2 (v132)", "2D/3D sweeps + derived columns; emits study_matrix_v132.zip.", "_v132_study_matrix_v2_panel"),
        LayerEntry("L4", "Vault Restore + Session Replay (v131)", "Restore vault entries into the run ledger; download attachments.", "_v131_vault_restore_panel"),
        LayerEntry("L4", "Persistent Run Vault (v130)", "Append-only vault to prevent losing results; restore provenance.", "_v130_run_vault_panel"),
        LayerEntry("L4", "Pareto from Study (v129)", "Compute Pareto fronts from study results (no optimizer).", "_v129_pareto_panel"),
        LayerEntry("L4", "Study Explorer + Comparator (v128)", "Load study zips, filter cases, compare two cases.", "_v128_study_explorer_panel"),
        LayerEntry("L4", "Study Matrix + Batch Paper Packs (v127)", "Batch cases → per-case paper packs + study index.", "_v127_study_matrix_panel"),
        LayerEntry("L4", "UI Smoke & Diagnostics (v126)", "Headless smoke runner + scenario checks.", "_v126_ui_smoke_panel"),
        LayerEntry("L4", "One-Click Paper Pack (v125)", "Orchestrated publishable export pipeline.", "_v125_paper_pack_panel"),
        LayerEntry("L3", "Feasibility Boundary Atlas (v124)", "2D feasibility scans + boundary extraction and publishable atlas bundle.", "_v124_feasibility_atlas_panel"),
        LayerEntry("L1", "Evidence Graph & Study Kit (v123)", "Provenance graph + traceability + publishable study kit export.", "_v123_evidence_and_studykit_panel"),
        LayerEntry("L1", "Authority & Reference (v120)", "Governance, citation, constitutional docs, and integrity manifest.", "_v120_constitution_panel"),
        LayerEntry("L2", "Engineering Interfaces", "Handoff/export adapters (e.g., v116).", "_v116_handoff_pack_panel"),
        LayerEntry("L3", "Mission Context (v121)", "Advisory mission overlays and mission gap reports.", "_v121_mission_context_panel"),
        LayerEntry("L4", "Explainability (v122)", "Post-processing narratives and causal summaries.", "_v122_explainability_panel"),
    ]
