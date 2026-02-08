
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

@dataclass(frozen=True)
class PanelContract:
    panel_fn_name: str
    title: str
    requires: List[str]
    optional: List[str]
    notes: str = ""
    # If any of these keys exist and evaluate to True, panel is blocked with message.
    blocked_if_true_keys: List[str] = None

def get_panel_contracts() -> Dict[str, PanelContract]:
    # Contracts are intentionally conservative: only depend on stable session_state artifact keys.
    c = {}

    def add(panel_fn_name: str, title: str, requires: List[str], optional: List[str]=None, notes: str=""):
        c[panel_fn_name] = PanelContract(
            panel_fn_name=panel_fn_name,
            title=title,
            requires=requires,
            optional=optional or [],
            notes=notes,
            blocked_if_true_keys=[],
        )

    # L7–L8 feasibility + authority layers (from ui/layer_registry.py)
    add("_v156_feasibility_atlas_panel", "Feasibility Atlas (v156)", requires=["v156_field"])
    add("_v157_feasibility_boundary_panel", "Feasibility Boundary (v157)", requires=["v157_boundary"])
    add("_v158_constraint_dominance_panel", "Constraint Dominance Topology (v158)", requires=["v158_dom"])
    add("_v159_feasibility_completion_panel", "Feasibility Completion Evidence (v159)", requires=["v159_completion"])
    add("_v160_authority_certificate_panel", "Feasibility Authority Certificate (v160)", requires=["v160_cert"])
    add("_v161_completion_frontier_panel", "Completion Frontier (v161)", requires=["v161_frontier"])
    add("_v162_directed_local_search_panel", "Directed Local Search (v162)", requires=["v162_local_search"])
    add("_v163_completion_pack_panel", "Completion Pack (v163)", requires=["v163_pack"])
    add("_v164_sensitivity_panel", "Sensitivity (v164)", requires=["v164_sensitivity"])
    add("_v165_study_protocol_panel", "Study Protocol (v165)", requires=["v165_protocol"])
    add("_v166_repro_lock_panel", "Repro Lock + Replay (v166)", requires=["v166_lock"], optional=["v166_replay"])
    add("_v167_authority_pack_panel", "Authority Pack (v167)", requires=["v167_manifest"])
    add("_v168_citation_panel", "Citation (v168)", requires=["v168_citation"])
    add("_v169_atlas_panel", "Feasibility Boundary Atlas (v169)", requires=["v169_manifest"])
    add("_v170_process_export_panel", "PROCESS Export (v170)", requires=["v170_manifest"])
    add("_v152_integrity_panel", "Run Integrity Lock (v152)", requires=["v152_last_lock"], optional=["v152_locks"])
    add("_v150_publishable_study_kit_panel", "Publishable Study Kit (v150)", requires=["v150_pack"])
    add("_v155_multi_study_pack_panel", "Multi-Study Pack (v155)", requires=["v143_bun"], notes="Uses multi-study bundle key as anchor.")
    add("_v154_caption_editor_panel", "Caption Editor (v154)", requires=["v154_captions"])
    add("_v153_doi_export_panel", "DOI Export Helper (v153)", requires=["v168_citation"])

    # Common live panels (point designer + scans)
    add("_v89_1_render_cached_point", "Cached Point Result", requires=["pd_last_outputs","pd_last_artifact"])
    add("_v89_2_point_cache_ui", "Point Cache UI", requires=["pd_last_outputs","pd_last_artifact"])
    add("_v100_scan_viewer", "Scan Viewer", requires=["scan_last_outputs","scan_last_artifact"])
    add("_v101_results_explorer", "Results Explorer", requires=["scan_last_outputs"])

    return c
