
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
    add("_v156_feasibility_atlas_panel", "Feasibility Atlas", requires=["v156_field"])
    add("_v157_feasibility_boundary_panel", "Feasibility Boundary", requires=["v157_boundary"])
    add("_v158_constraint_dominance_panel", "Constraint Dominance Topology", requires=["v158_dom"])
    add("_v159_feasibility_completion_panel", "Feasibility Completion Evidence", requires=["v159_completion"])
    add("_v160_authority_certificate_panel", "Feasibility Authority Certificate", requires=["v160_cert"])
    add("_v161_completion_frontier_panel", "Completion Frontier", requires=["v161_frontier"])
    add("_v162_directed_local_search_panel", "Directed Local Search", requires=["v162_local_search"])
    add("_v163_completion_pack_panel", "Completion Pack", requires=["v163_pack"])
    add("_v164_sensitivity_panel", "Sensitivity", requires=["v164_sensitivity"])
    add("_v165_study_protocol_panel", "Study Protocol", requires=["v165_protocol"])
    add("_v166_repro_lock_panel", "Repro Lock + Replay", requires=["v166_lock"], optional=["v166_replay"])
    add("_v167_authority_pack_panel", "Authority Pack", requires=["v167_manifest"])
    add("_v168_citation_panel", "Citation", requires=["v168_citation"])
    add("_v169_atlas_panel", "Feasibility Boundary Atlas", requires=["v169_manifest"])
    add("_v170_process_export_panel", "PROCESS Export", requires=["v170_manifest"])
    add("_v152_integrity_panel", "Run Integrity Lock", requires=["v152_last_lock"], optional=["v152_locks"])
    add("_v150_publishable_study_kit_panel", "Publishable Study Kit", requires=["v150_pack"])
    add("_v155_multi_study_pack_panel", "Multi-Study Pack", requires=["v143_bun"], notes="Uses multi-study bundle key as anchor.")
    add("_v154_caption_editor_panel", "Caption Editor", requires=["v154_captions"])
    add("_v153_doi_export_panel", "DOI Export Helper", requires=["v168_citation"])

    # Common live panels (point designer + scans)
    add("_v89_1_render_cached_point", "Cached Point Result", requires=["pd_last_outputs","pd_last_artifact"])
    add("_v89_2_point_cache_ui", "Point Cache UI", requires=["pd_last_outputs","pd_last_artifact"])
    add("_v100_scan_viewer", "Scan Viewer", requires=["scan_last_outputs","scan_last_artifact"])
    add("_v101_results_explorer", "Results Explorer", requires=["scan_last_outputs"])

    # Deck contracts (UI Phase B)
    add("render_point_designer_hero", "Point Designer Hero Strip", requires=["pd_last_outputs"], optional=["pd_last_artifact"])
    add("render_system_suite_header", "System Suite Feasibility Strip", requires=["pd_last_outputs"])
    add("render_overlay_authority_dashboard", "Authority Overlay Dashboard", requires=[], optional=["last_point_inp"])
    add("render_point_designer_export", "Point Export Bundle", requires=["pd_last_outputs", "pd_last_artifact"])

    return c
