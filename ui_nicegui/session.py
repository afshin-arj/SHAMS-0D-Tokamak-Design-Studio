"""DesignSession — typed session state for the NiceGUI UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


_DEFAULT_INPUTS: dict[str, Any] = {
    "R0_m": 1.81,
    "a_m": 0.62,
    "kappa": 1.8,
    "delta": 0.0,
    "Bt_T": 10.0,
    "Ip_MA": 8.0,
    "Ti_keV": 10.0,
    "fG": 0.8,
    "Paux_MW": 50.0,
    "Paux_for_Q_MW": 50.0,
    "Ti_over_Te": 2.0,
    "t_shield_m": 0.70,
    "q95_enforcement": "hard",
    "greenwald_enforcement": "hard",
    "tech_tier": "TRL7",
    "magnet_technology": "HTS_REBCO",
    "Tcoil_K": 20.0,
    "confinement_scaling": "IPB98y2",
    "zeff": 1.8,
    "dilution_fuel": 0.85,
    "fuel_mode": "DT",
}


@dataclass
class DesignSession:
    active_deck: str = "Point Designer"
    design_intent: str = "Power Reactor (net-electric)"
    pd_subdeck: str = "Truth Console"
    inputs: dict[str, Any] = field(default_factory=lambda: dict(_DEFAULT_INPUTS))
    knobs: dict[str, Any] = field(default_factory=dict)
    overlay: dict[str, Any] = field(default_factory=lambda: {
        "include_magnet_technology_authority_v400": True,
    })
    # Studio default entry (Independence 3.4): landing card shown until first
    # evaluation or explicit dismiss (per-session, never persisted).
    studio_entry_dismissed: bool = False
    last_eval: Optional[dict[str, Any]] = None
    pd_last_outputs: Optional[dict[str, Any]] = None
    pd_last_artifact: Optional[dict[str, Any]] = None
    pd_last_run_ts: Optional[float] = None
    # Presentation caches (UI only) — filled by set_point_evaluation; never L0 truth.
    pd_verdict_summary_cache: Optional[dict[str, Any]] = None
    pd_no_solution_atlas_cache: Optional[dict[str, Any]] = None
    last_error: Optional[str] = None
    evaluating: bool = False
    # System Suite
    suite_availability: float = 0.75
    profile_contracts_v362_last: Optional[dict[str, Any]] = None
    # Systems Mode
    systems_workflow_step: str = "1 · Targets"
    systems_workflow_power_user: bool = False
    systems_block_solve: bool = False
    systems_do_precheck: bool = True
    systems_last_solve_result: Optional[dict[str, Any]] = None
    systems_last_solve_artifact: Optional[dict[str, Any]] = None
    last_precheck_report: Optional[Any] = None
    systems_precheck_seconds: Optional[float] = None
    systems_precheck_running: bool = False
    systems_solve_running: bool = False
    systems_atlas_running: bool = False
    systems_use_q: bool = True
    systems_q_target: float = 10.0
    systems_use_h: bool = False
    systems_h_target: float = 1.15
    systems_use_pnet: bool = False
    systems_pnet_target: float = 50.0
    systems_use_pfus: bool = False
    systems_pfus_target: float = 200.0
    systems_solve_ip: bool = False
    systems_solve_fg: bool = False
    systems_solve_paux: bool = True
    systems_precheck_n_random: int = 8
    systems_precheck_seed: int = 1337
    systems_max_iter: int = 35
    systems_tol: float = 1e-3
    systems_damping: float = 0.6
    # Systems Mode Phase 12 — recovery / search / apply / export
    systems_recovery_last: Optional[dict[str, Any]] = None
    systems_feasible_search_last: Optional[dict[str, Any]] = None
    systems_run_cards: list[dict[str, Any]] = field(default_factory=list)
    systems_recovery_budget: int = 120
    systems_recovery_local_steps: int = 40
    systems_recovery_multistart: int = 20
    systems_recovery_seed: int = 2026
    systems_recovery_running: bool = False
    systems_fs_budget: int = 150
    systems_fs_topk: int = 8
    systems_fs_radius: float = 0.25
    systems_fs_seed: int = 2026
    systems_fs_running: bool = False
    systems_selected_candidate_id: str = ""
    # Systems Mode parity — overrides, assistant, solve advanced, audit
    systems_base_overrides: dict[str, Any] = field(default_factory=dict)
    systems_base_history: list[dict[str, Any]] = field(default_factory=list)
    systems_inputs_overrides: dict[str, float] = field(default_factory=dict)
    systems_bounds_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    systems_targets_overrides: dict[str, float] = field(default_factory=dict)
    systems_undo_stack: list[dict[str, Any]] = field(default_factory=list)
    systems_apply_undo_stack: list[dict[str, Any]] = field(default_factory=list)
    systems_last_applied_change: Optional[dict[str, Any]] = None
    systems_do_continuation: bool = True
    systems_cont_steps: int = 10
    systems_feasibility_scout_enabled: bool = False
    systems_scout_n_samples: int = 64
    systems_scout_n_refine: int = 20
    systems_trust_delta: float = 0.0
    systems_use_trust_delta: bool = False
    systems_journal: list[dict[str, Any]] = field(default_factory=list)
    systems_ranking_profile: str = "Balanced"
    systems_atlas_var_x: str = "Paux_MW"
    systems_atlas_var_y: str = "Ip_MA"
    systems_atlas_grid_n: int = 12
    systems_last_micro_atlas: Optional[dict[str, Any]] = None
    systems_cert_cache: dict[str, Any] = field(default_factory=dict)
    systems_recovery_auto: bool = True
    systems_recovery_enabled: bool = True
    systems_recovery_autotrigger: bool = False
    systems_expert_view: bool = False
    systems_assistant_proposals: list[dict[str, Any]] = field(default_factory=list)
    systems_design_stories: list[dict[str, Any]] = field(default_factory=list)
    systems_frontier_src: str = "Precheck samples"
    systems_frontier_x: str = "Paux_MW"
    systems_frontier_y: str = "Q_DT_eqv"
    systems_timeline_src: str = "Seeded recovery"
    systems_assumption_lock_hash: str = ""
    systems_assumption_lock_enabled: bool = False
    systems_sensitivities_last: Optional[dict[str, Any]] = None
    systems_fs_multiseed_n: int = 1
    systems_fs_objective: str = "q_div_MW_m2"
    systems_fs_src: str = "Manual (midpoint of bounds)"
    systems_fs_vars: list[str] = field(default_factory=list)
    systems_fs_bounds: dict[str, dict[str, float]] = field(default_factory=dict)
    systems_fs_trace_keep: int = 2500
    systems_decision_state: str = "Diagnose infeasibility"
    systems_teaching_mode: bool = True
    systems_recovery_seed_mode: str = "Point Designer baseline"
    systems_recovery_basevars_enabled: bool = False
    systems_recovery_basevars: list[str] = field(default_factory=list)
    systems_recovery_base_bounds: dict[str, Any] = field(default_factory=dict)
    systems_recovery_manual_seed: dict[str, float] = field(default_factory=dict)
    systems_exhaust_authority: Optional[dict[str, Any]] = None
    systems_repro_pick: str = ""
    systems_diff_a: str = ""
    systems_diff_b: str = ""
    systems_atlas_robust_thr: float = 0.10
    # Scan Lab
    scan_cartography_report: Optional[dict[str, Any]] = None
    scan_cartography_artifact: Optional[dict[str, Any]] = None
    scan_cart_x_key: str = "Ip_MA"
    scan_cart_y_key: str = "R0_m"
    scan_cart_intents: list[str] = field(default_factory=lambda: ["Reactor"])
    scan_cart_x_lo: Optional[float] = None
    scan_cart_x_hi: Optional[float] = None
    scan_cart_y_lo: Optional[float] = None
    scan_cart_y_hi: Optional[float] = None
    scan_cart_nx: int = 11
    scan_cart_ny: int = 11
    scan_cart_include_outputs: bool = False
    scan_cart_base_override: Optional[dict[str, Any]] = None
    scan_running: bool = False
    scan_progress: float = 0.0
    scan_progress_text: str = ""
    # Scan Lab Phase 13 — workbench
    scan_wb_intent: str = "Reactor"
    scan_wb_view: str = "Dominance (blocking)"
    scan_wb_i: int = 0
    scan_wb_j: int = 0
    scan_wb_compare_intents: bool = False
    scan_wb_contour_field: str = ""
    scan_causality_rel_step: float = 0.01
    scan_causality_last: Optional[dict[str, Any]] = None
    scan_df_intent: str = "Reactor"
    scan_df_min_points: int = 12
    scan_design_families_v394: Optional[dict[str, Any]] = None
    scan_design_families_v394_cert: Optional[dict[str, Any]] = None
    scan_atlas_title: str = "SHAMS — Scan Lab Atlas"
    scan_atlas_pdf_bytes: Optional[bytes] = None
    scan_signature_atlas_pdf_bytes: Optional[bytes] = None
    scan_signature_atlas_title: str = "SHAMS — Scan Lab Signature Atlas"
    scan_workflow_step: str = "1 · Setup & Run"
    scan_decision_state: str = "Map my limits (2D slice)"
    scan_teaching_mode: bool = True
    scan_expert_view: bool = False
    scan_import_errors: list[str] = field(default_factory=list)
    scan_local_insight: str = "Causality trace"
    scan_next_tier_pick: str = "Explain infeasible region"
    scan_claim_intent: str = "Reactor"
    scan_probe_focus: Optional[dict[str, Any]] = None
    scan_claim_type: str = "Dominance"
    scan_claim_title: str = ""
    scan_claim_statement: str = ""
    scan_claim_expected: str = ""
    scan_claim_notes: str = ""
    scan_claim_falsify_last: Optional[dict[str, Any]] = None
    scan_claim_pdf_bytes: Optional[bytes] = None
    scan_claim_last: Optional[dict[str, Any]] = None
    scan_path_follow_last: Optional[dict[str, Any]] = None
    scan_lib_tag: str = "interesting"
    scan_lib_note: str = ""
    scan_slice_z_key: str = ""
    scan_slice_rel_step: float = 0.05
    scan_slice_diag_last: Optional[dict[str, Any]] = None
    scan_legacy_spec: Optional[dict[str, Any]] = None
    scan_legacy_last: Optional[dict[str, Any]] = None
    scan_legacy_running: bool = False
    scan_legacy_progress: float = 0.0
    scan_benchmark_learned: bool = False
    scan_benchmark_note: str = ""
    scan_view_mode: str = ""
    scan_promote_note: str = "Probed scan cell"
    scan_iso_constraint: str = ""
    scan_deep_viz_intent: str = "Reactor"
    # Opt Lab / Certified Optimizer (Phase 1.2 + 3.3 unify)
    opt_lab_last_run_stamp: Optional[dict[str, Any]] = None
    opt_lab_show_certified_front: bool = False
    certified_front_handoff: Optional[dict[str, Any]] = None
    # Pareto Lab
    pareto_deck: str = "Internal Pareto Frontier"
    pareto_last: Optional[dict[str, Any]] = None
    pareto_bounds: Optional[dict[str, Any]] = None
    pareto_template: str = "Custom"
    pareto_sel_objs: list[str] = field(
        default_factory=lambda: ["R0_m", "B_peak_T", "P_e_net_MW"]
    )
    pareto_obj_senses: dict[str, str] = field(
        default_factory=lambda: {
            "R0_m": "min",
            "B_peak_T": "min",
            "P_e_net_MW": "max",
        }
    )
    pareto_intent_mode: str = "Reactor"
    pareto_n_samples: int = 300
    pareto_seed: int = 1
    pareto_robust_margin_thr: float = 0.10
    pareto_running: bool = False
    pareto_workflow_step: str = "1 · Setup & Run"
    pareto_decision_state: str = "Sample a new frontier"
    pareto_teaching_mode: bool = True
    pareto_expert_view: bool = False
    pareto_plot_x: str = "R0_m"
    pareto_plot_y: str = "P_e_net_MW"
    pareto_plot_color: str = "dominant_constraint"
    pareto_intent_split: bool = False
    pareto_robust_only: bool = False
    pareto_robust_overlay: bool = True
    pareto_hide_mirages: bool = False
    pareto_show_failures: bool = True
    pareto_focus_metrics: list[str] = field(default_factory=lambda: ["Q_DT_eqv", "H98", "TBR"])
    pareto_policy_filtered: Optional[list[dict[str, Any]]] = None
    pareto_external_group: str = "Robust screening"
    pareto_external_tool: str = "Robust Pareto Frontier (Phase+UQ)"
    feasible_optimizer_last: Optional[dict[str, Any]] = None
    systems_mode_queue: list[dict[str, Any]] = field(default_factory=list)
    # Trade Study Studio
    trade_studio_deck: str = "Study Setup & Run"
    trade_last: Optional[dict[str, Any]] = None
    trade_last_lane: str = "Optimistic vs Robust"
    trade_knob_set: Optional[str] = None
    trade_n_samples: int = 200
    trade_seed: int = 7
    trade_objectives: list[str] = field(default_factory=list)
    trade_lane_mode: str = "Optimistic vs Robust"
    trade_running: bool = False
    trade_workflow_step: str = "1 · Setup & Run"
    trade_decision_state: str = "Run a new trade study"
    trade_teaching_mode: bool = True
    trade_expert_view: bool = False
    trade_plot_x: str = "min_R0"
    trade_plot_y: str = "max_Pnet"
    trade_plot_color: str = "design_family"
    trade_show_failures: bool = True
    trade_advanced_group: str = "Frontier & certification"
    trade_advanced_deck: str = "Multi-Objective Feasible Frontier Atlas"
    ts_sa_verified_rows: Optional[list] = None
    v351_lane_rows: Optional[list] = None
    v351_empty_region: Optional[dict[str, Any]] = None
    active_study_capsule: Optional[dict[str, Any]] = None
    # Reactor Design Forge (Batch 7 + workflow)
    forge_workflow_step: str = "1 · Compile Intent"
    forge_decision_state: str = "Compile intent to a candidate"
    forge_teaching_mode: bool = True
    forge_expert_view: bool = False
    forge_wb_view: str = "Archive overview"
    forge_scatter_x: str = "R0_m"
    forge_scatter_y: str = "P_e_net_MW"
    forge_inspect_idx: int = 0
    forge_review_bench: list[int] = field(default_factory=list)
    forge_conflict_atlas: Optional[dict[str, Any]] = None
    forge_filter_robust: bool = False
    forge_filter_min_score: float = float("-inf")
    forge_filter_max_coe: Optional[float] = None
    forge_instrument_group: str = "Run intelligence"
    forge_instrument_tool: str = "Run dashboard"
    forge_provenance_constraint: str = "q_div"
    forge_surface_constraint: str = ""
    forge_localcart_x: str = "R0_m"
    forge_localcart_y: str = "Ip_MA"
    forge_localcart_span: int = 20
    forge_localcart_grid: int = 21
    forge_localcart_df: Optional[Any] = None
    forge_uq_samples: int = 200
    forge_uq_pct: int = 5
    forge_uq_result: Optional[dict[str, Any]] = None
    forge_casebook: list[dict[str, Any]] = field(default_factory=list)
    forge_casebook_results: list[dict[str, Any]] = field(default_factory=list)
    forge_adv_surface: bool = True
    forge_adv_skeleton: bool = True
    forge_adv_memory: bool = False
    forge_adv_multi_intent: bool = False
    forge_adv_staged: bool = False
    forge_min_margin_guard: float = 0.0
    forge_use_cost: bool = False
    forge_stage_state: Optional[dict[str, Any]] = None
    forge_review_session: Optional[dict[str, Any]] = None
    forge_deck: str = "Intent Compiler"
    forge_review_mode: bool = False
    # Helm Console (sidebar parity with Streamlit)
    helm_drawer_open: bool = True
    helm_drawer_width: int = 340
    explain_mode: bool = True
    expert_mode: bool = False
    guided_mode: bool = True
    activity_log_auto: bool = True
    activity_log_tail: int = 200
    ui_last_invalidation_reason: Optional[str] = None
    # Helm Console — fidelity, calibration, verification (Streamlit sidebar parity)
    fidelity_config: dict[str, Any] = field(default_factory=lambda: {
        "plasma": "0D",
        "magnets": "limits",
        "exhaust": "proxy",
        "neutronics": "proxy",
        "profiles": "off",
        "economics": "proxy",
    })
    calib_confinement: float = 1.0
    calib_divertor: float = 1.0
    calib_bootstrap: float = 1.0
    verify_show_logs: bool = False
    helm_verify_ok: Optional[bool] = None
    helm_verify_out: str = ""
    helm_verify_err: str = ""
    helm_verify_dt: Optional[float] = None
    helm_verify_running: bool = False
    shams_exit_confirm: bool = False
    shams_exit_force_busy: bool = False
    shams_clear_log_confirm: bool = False
    pd_clear_confirm: bool = False
    _activity_logger: Optional[Any] = field(default=None, repr=False)
    _activity_log_inited: bool = field(default=False, repr=False)
    # Design State Graph (exploration layer)
    _shams_dsg: Optional[Any] = field(default=None, repr=False)
    dsg_selected_node_id: str = ""
    dsg_context_edge_kind: str = "derived"
    dsg_edge_kind_auto: bool = True
    scan_last_node_ids: list[str] = field(default_factory=list)
    scan_last_parent_node_id: str = ""
    pareto_last_node_ids: list[str] = field(default_factory=list)
    pareto_last_parent_node_id: str = ""
    trade_last_node_ids: list[str] = field(default_factory=list)
    trade_last_parent_node_id: str = ""
    extopt_last_node_ids: list[str] = field(default_factory=list)
    extopt_last_parent_node_id: str = ""
    forge_intent_compiler_last: Optional[dict[str, Any]] = None
    forge_last_audit: Optional[dict[str, Any]] = None
    forge_pfus_target: float = 140.0
    forge_q_target: float = 2.0
    forge_override_r0: float = 0.0
    forge_override_a: float = 0.0
    forge_override_bt: float = 0.0
    forge_override_ip: float = 0.0
    forge_compiling: bool = False
    forge_auditing: bool = False
    # Forge Phase 14 — Machine Finder + Capsules
    forge_mf_intent_label: str = "Power Reactor (net-electric)"
    forge_mf_pack_name: str = ""
    forge_mf_var_keys: list[str] = field(default_factory=lambda: ["R0_m", "Bt_T", "Ip_MA", "Paux_MW"])
    forge_mf_bound_mode: str = "Medium (±20%)"
    forge_mf_custom_bounds: Optional[dict[str, tuple[float, float]]] = None
    forge_mf_pop_size: int = 64
    forge_mf_generations: int = 40
    forge_mf_surrogate_rounds: int = 6
    forge_mf_local_steps: int = 70
    forge_mf_archive_topk: int = 60
    forge_mf_require_feasible_only: bool = True
    forge_mf_seed: int = 1
    forge_mf_running: bool = False
    forge_mf_last_bounds: Optional[dict[str, list[float]]] = None
    forge_workbench_run: Optional[dict[str, Any]] = None
    forge_lens_contract: Optional[dict[str, Any]] = None
    forge_capsule_zip_bytes: Optional[bytes] = None
    forge_capsule_zip_name: str = "opt_capsule.zip"
    forge_audit_pack_bytes: Optional[bytes] = None
    forge_audit_pack_name: str = "shams_forge_audit_pack.zip"
    forge_capsule_diff_a: Optional[dict[str, Any]] = None
    forge_capsule_diff_b: Optional[dict[str, Any]] = None
    forge_capsule_diff: Optional[dict[str, Any]] = None
    # System Suite Phase 15
    suite_campaign_spec_json: str = ""
    suite_campaign_candidates: Optional[list[dict[str, Any]]] = None
    suite_campaign_summary: Optional[dict[str, Any]] = None
    suite_campaign_results_preview: Optional[list[dict[str, Any]]] = None
    suite_campaign_jsonl_bytes: Optional[bytes] = None
    suite_parity_suite: str = "v364"
    suite_parity_preset: str = "C8"
    suite_parity_tier: str = "both"
    suite_parity_case: str = ""
    suite_parity_last_report: Optional[dict[str, Any]] = None
    suite_workflow_step: str = "1 · Plant & Power"
    suite_decision_state: str = "Plant closure & duty"
    suite_teaching_mode: bool = True
    suite_expert_view: bool = False
    suite_running: bool = False
    suite_pareto_bridge_meta: Optional[dict[str, Any]] = None
    # Control Room Provenance Phase 15
    cr_provenance_tab: str = "Studies & Protocol"
    cr_selected_run_id: str = ""
    cr_studies: list[dict[str, Any]] = field(default_factory=list)
    cr_protocol_title: str = "SHAMS Design Study"
    cr_protocol_objective: str = ""
    cr_protocol_seed: int = 0
    cr_study_protocol_last: Optional[dict[str, Any]] = None
    cr_repro_tol_json: str = ""
    cr_repro_lock_last: Optional[dict[str, Any]] = None
    cr_replay_report_last: Optional[dict[str, Any]] = None
    cr_authority_pack_bytes: Optional[bytes] = None
    cr_citation_title: str = ""
    cr_citation_repo: str = ""
    cr_citation_doi: str = ""
    cr_citation_author: str = "SHAMS Contributors"
    cr_citation_last: Optional[dict[str, Any]] = None
    cr_regression_diff: Optional[dict[str, Any]] = None
    cr_repo_regression_last: Optional[dict[str, Any]] = None
    # Compare deck workflow
    cmp_slot_a: Optional[dict[str, Any]] = None
    cmp_slot_b: Optional[dict[str, Any]] = None
    cmp_slot_a_meta: dict[str, Any] = field(default_factory=dict)
    cmp_slot_b_meta: dict[str, Any] = field(default_factory=dict)
    cmp_use_slot_a: bool = True
    cmp_use_slot_b: bool = True
    cmp_workflow_step: str = "1 · Load A & B"
    cmp_teaching_mode: bool = True
    cmp_expert_view: bool = False
    cmp_decision_state: str = "Load baseline vs variant"
    cmp_show_all_outputs: bool = False
    # Publication Benchmarks
    pub_bench_tab: str = "Tokamak Constitutional Atlas"
    pub_atlas_bucket: str = ""
    pub_atlas_preset_key: str = ""
    pub_atlas_intent: str = "Research"
    pub_atlas_last: Optional[dict[str, Any]] = None
    pub_atlas_fragility: Optional[dict[str, Any]] = None
    pub_atlas_running: bool = False
    pub_atlas_fragility_running: bool = False
    # Publication Benchmarks Phase 16
    pub_crosscode_code: str = ""
    pub_crosscode_intent: str = "research"
    pub_crosscode_last: Optional[dict[str, Any]] = None
    pub_bench_ack: bool = False
    pub_bench_running: bool = False
    pub_bench_cases_file: str = "cases_point_designer.json"
    pub_bench_progress: str = ""
    pub_bench_last_outdir: Optional[str] = None
    pub_bench_last_rc: Optional[int] = None
    pub_bench_last_log: str = ""
    pub_bench_delta_md: str = ""
    pub_contract_sel_a: str = ""
    pub_contract_sel_b: str = "(none)"
    pub_v387_include: dict[str, bool] = field(default_factory=dict)
    pub_v387_notes: str = ""
    pub_v387_last_index: Optional[dict[str, Any]] = None
    pub_v387_last_bytes: Optional[bytes] = None
    pub_workflow_step: str = "1 · Constitutional Atlas"
    pub_teaching_mode: bool = True
    pub_expert_view: bool = False
    pub_running: bool = False
    pub_decision_state: str = "Benchmark a tokamak preset (ITER, SPARC, …)"
    pub_regulatory_zip_bytes: Optional[bytes] = None
    pub_regulatory_validate: Optional[dict[str, Any]] = None
    pub_licensing_zip_bytes: Optional[bytes] = None
    pub_licensing_validate: Optional[dict[str, Any]] = None
    # Phase 17 — external optimizers / advanced trade decks
    robust_pareto_source: str = ""
    robust_pareto_phases_json: str = ""
    robust_pareto_uq_json: str = ""
    robust_pareto_last: Optional[dict[str, Any]] = None
    regime_atlas_records: list[dict[str, Any]] = field(default_factory=list)
    regime_atlas_gate: str = "robust_only"
    regime_atlas_min_bucket: int = 8
    regime_atlas_last: Optional[dict[str, Any]] = None
    design_families_last: Optional[dict[str, Any]] = None
    extopt_workbench_last: Optional[str] = None
    extopt_suite_upload_name: str = ""
    extopt_suite_upload_bytes: Optional[bytes] = None
    extopt_last_run: Optional[dict[str, Any]] = None
    extopt_copilot_yaml_name: str = ""
    extopt_copilot_yaml_bytes: Optional[bytes] = None
    extopt_copilot_last: Optional[dict[str, Any]] = None
    extopt_interpret_last: Optional[dict[str, Any]] = None
    certified_opt_last: Optional[dict[str, Any]] = None
    concept_cockpit_last: Optional[dict[str, Any]] = None
    optimizer_evidence_sel: str = ""
    v351_atlas_last: Optional[dict[str, Any]] = None
    v352_cert_last: Optional[dict[str, Any]] = None
    ts_sa_candidates: Optional[list[dict[str, Any]]] = None
    ts_kit_last: Optional[dict[str, Any]] = None
    lane_last: Optional[dict[str, Any]] = None
    v324_regime_maps: Optional[dict[str, Any]] = None
    pf_last: Optional[dict[str, Any]] = None
    # Control Room Phase 18
    cr_artifacts_tab: str = "Artifacts Explorer"
    cr_chronicle_tab: str = "Variable Registry"
    cr_selected_artifact: Optional[dict[str, Any]] = None
    cr_selected_artifact_id: str = ""
    cr_study_index_path: str = ""
    cr_study_index: Optional[dict[str, Any]] = None
    cr_sensitivity_last: Optional[dict[str, Any]] = None
    cr_sensitivity_knobs: list[str] = field(default_factory=list)
    cr_sensitivity_outputs: list[str] = field(default_factory=list)
    cr_forensics_last: Optional[dict[str, Any]] = None
    cr_knob_grid_last: Optional[dict[str, Any]] = None
    cr_cprov_sel: str = ""
    cr_validation_env: str = ""
    cr_validation_report: Optional[dict[str, Any]] = None
    cr_invariants_report: Optional[dict[str, Any]] = None
    v340_cert_search_last: Optional[dict[str, Any]] = None
    v343_interval_narrowing_evidence: Optional[dict[str, Any]] = None
    # Control Room
    cr_section: str = "Orientation"
    cr_orient_tab: str = "Launchpad"
    cr_const_tab: str = "Model Ledger"
    cr_diag_tab: str = "Gatechecks"
    cr_launchpad_path: str = "Understand feasibility limits (cartography)"
    cr_docs_sel: str = ""
    cr_interop_report: Optional[dict[str, Any]] = None
    cr_contract_report: Optional[dict[str, Any]] = None
    cr_workflow_step: str = "1 · Orient"
    cr_teaching_mode: bool = True
    cr_expert_view: bool = False
    cr_decision_state: str = "Find my workflow (launchpad)"
    cr_case_deck_last: Optional[dict[str, Any]] = None
    cr_scenario_base: Optional[dict[str, Any]] = None
    cr_scenario_variant: Optional[dict[str, Any]] = None
    cr_constraint_inspect_name: str = ""
    # Point Designer workflow (Truth Console)
    pd_workflow_tab: str = "1 · Configure"
    pd_teaching_mode: bool = True
    pd_expert_view: bool = False
    pd_decision_state: str = "Set machine & authority overlays"
    # Point Designer Phase 11 — outer-loop + forensics
    pd_telemetry_view: str = "Verdict & KPIs"
    phase_envelopes_phases_json: str = ""
    phase_envelopes_label_prefix: str = "phase"
    phase_envelopes_last: Optional[dict[str, Any]] = None
    phase_envelopes_running: bool = False
    pd_forensics_running: bool = False
    uq_contract_name: str = "uq_contract"
    uq_contract_group: str = "PLASMA"
    uq_contract_dims: list[str] = field(default_factory=list)
    uq_contract_mode: str = "±% around baseline"
    uq_contract_pct: float = 5.0
    uq_contract_max_dims: int = 12
    uq_contract_abs_bounds: dict[str, Any] = field(default_factory=dict)
    uq_contract_last: Optional[dict[str, Any]] = None
    uq_contract_running: bool = False
    pd_last_forensics: Optional[dict[str, Any]] = None
    # Point Designer Phase 20 — solver, operating targets, export
    pd_eval_mode: str = "direct"
    pd_q_target: float = 2.0
    pd_h98_target: float = 1.15
    pd_ip_min: float = 0.0
    pd_ip_max: float = 0.0
    pd_fg_min: float = -1.0
    pd_fg_max: float = 0.0
    pd_solver_tol: float = 1e-3
    pd_show_solver_live: bool = True
    pd_do_opt: bool = False
    pd_opt_objective: str = "min_Bpeak"
    pd_opt_iters: int = 200
    pd_opt_seed: int = 1
    pd_include_secondary_dt: bool = True
    pd_tritium_retention: float = 0.5
    pd_tau_t_loss_s: float = 5.0
    pd_solver_trace: list[dict[str, Any]] = field(default_factory=list)
    pd_last_log_lines: list[str] = field(default_factory=list)
    pd_last_inputs_hash: Optional[str] = None
    pd_current_inputs_hash: Optional[str] = None
    pd_frontier_last: Optional[dict[str, Any]] = None
    pd_last_summary_pdf_bytes: Optional[bytes] = None
    pd_baseline_artifact: Optional[dict[str, Any]] = None
    pd_pert_scan_rows: list[dict[str, Any]] = field(default_factory=list)
    pd_last_radial_png_bytes: Optional[bytes] = None
    pd_pfus_target: float = 0.0
    pd_pnet_target: float = -1.0
    pd_pending_systems_action: Optional[str] = None

    def build_point_inputs(self):
        from ui_nicegui.lib.point_inputs_builder import build_point_inputs
        return build_point_inputs(self)

    @property
    def paux_for_q(self) -> float:
        return float(self.inputs.get("Paux_for_Q_MW", self.inputs.get("Paux_MW", 50.0)))
