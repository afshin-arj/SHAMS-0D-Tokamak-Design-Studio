from __future__ import annotations

"""UI console for the external feasible-only optimizer client.

This module intentionally sits on the UI side of the SHAMS boundary:
- It launches an external client process (subprocess) that queries the frozen evaluator.
- It never modifies physics, constraints, or the evaluator truth graph.

All outputs are written as deterministic evidence packs under:
<repo_root>/runs/optimizer/<run_id>/

v230.0: External Optimizer UI Console Bundle
© 2026 Afshin Arjhangmehr
"""

import json
import os
import sys
import time
import zipfile
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from ui.tablekit import install_expandable_tables
install_expandable_tables(st)



RUNS_REL = Path("runs") / "optimizer"
PENDING_REL = Path("runs") / "_pending_optimizer"


@dataclass(frozen=True)
class KnobSpec:
    name: str
    lo: float
    hi: float
    enabled: bool = True




def _objective_contract_v2(
    objective_key: str,
    *,
    direction: str,
    robustness_first: bool,
    scenario_robustness_required: bool,
    design_intent: str,
) -> Dict[str, Any]:
    """Build an explicit, reviewer-safe objective contract.

    This is a UI-side declaration only. The external optimizer client must treat this
    as authoritative for selection ordering, while the frozen evaluator remains unchanged.
    """
    direction = str(direction).lower().strip()
    if direction not in ("min", "max"):
        direction = "max"
    ordering = ["worst_hard_margin", "objective"] if bool(robustness_first) else ["objective", "worst_hard_margin"]
    return {
        "schema": "objective_contract.v2",
        "primary": {"key": str(objective_key), "direction": direction},
        "ordering": ordering,
        "scenario_robustness_required": bool(scenario_robustness_required),
        "design_intent": str(design_intent),
        "notes": "Selection contract for feasible-only external optimization. Evaluator truth is immutable.",
    }

def _scan_artifact_from_session() -> Optional[Dict[str, Any]]:
    # Scan Lab stores these keys when a cartography run completes.
    return st.session_state.get("scan_cartography_artifact") or st.session_state.get("scan_cartography_report")


def _label_components(ok: List[List[bool]]) -> Tuple[List[List[int]], Dict[int, int]]:
    """Label 4-neighborhood connected components. Returns (labels, sizes)."""
    ny = len(ok)
    nx = len(ok[0]) if ny else 0
    lab = [[-1 for _ in range(nx)] for _ in range(ny)]
    sizes: Dict[int, int] = {}
    cid = 0
    for j in range(ny):
        for i in range(nx):
            if not ok[j][i] or lab[j][i] != -1:
                continue
            stack = [(i, j)]
            lab[j][i] = cid
            cnt = 0
            while stack:
                x, y = stack.pop()
                cnt += 1
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x+dx, y+dy
                    if 0 <= xx < nx and 0 <= yy < ny and ok[yy][xx] and lab[yy][xx] == -1:
                        lab[yy][xx] = cid
                        stack.append((xx, yy))
            sizes[cid] = cnt
            cid += 1
    return lab, sizes


def _extract_scan_seeds(
    scan_art: Dict[str, Any],
    *,
    intent: str,
    n_seeds: int,
    island: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extract robust feasible seeds from a Scan Lab artifact/report.

    Returns:
      seeds: list of full PointInputs-like dicts (base_inputs updated with x/y values)
      info:  auxiliary info for UI (x_key/y_key/bounds/components)
    """
    rep = scan_art.get("report") if isinstance(scan_art.get("report"), dict) else scan_art
    x_key = str(rep.get("x_key", "")).strip()
    y_key = str(rep.get("y_key", "")).strip()
    cube = rep.get("field_cube") or {}
    it = str(intent)
    itvars = ((cube.get("intent_vars") or {}).get(it) or {})
    ok = itvars.get("blocking_feasible") or []
    pfe = itvars.get("local_p_feasible") or []
    minm = itvars.get("min_blocking_margin") or []
    coords = (cube.get("coords") or {})
    xs = coords.get("x") or rep.get("x_vals") or []
    ys = coords.get("y") or rep.get("y_vals") or []

    # Component labeling for island selection
    labels, sizes = _label_components([[bool(v) for v in row] for row in ok]) if ok else ([[ ]], {})
    # Choose island ids
    island_ids: List[int] = []
    if sizes:
        if island == "largest":
            best = max(sizes.items(), key=lambda kv: kv[1])[0]
            island_ids = [best]
        elif island == "all":
            island_ids = sorted(sizes.keys())
        else:
            try:
                island_ids = [int(island)]
            except Exception:
                island_ids = sorted(sizes.keys())
    # Candidate cells scored by (p_feasible desc, min_margin desc)
    cells: List[Tuple[float, float, int, int]] = []
    ny = len(ok)
    nx = len(ok[0]) if ny else 0
    for j in range(ny):
        for i in range(nx):
            if not ok[j][i]:
                continue
            if island_ids and (labels[j][i] not in island_ids):
                continue
            try:
                s1 = float(pfe[j][i])
            except Exception:
                s1 = float('nan')
            try:
                s2 = float(minm[j][i])
            except Exception:
                s2 = float('nan')
            if not (s1 == s1):  # nan
                s1 = -1.0
            if not (s2 == s2):
                s2 = -1e9
            cells.append((s1, s2, i, j))
    cells.sort(key=lambda t: (t[0], t[1]), reverse=True)

    base = rep.get("base_inputs") or {}
    if not isinstance(base, dict):
        base = {}

    seeds: List[Dict[str, Any]] = []
    for (s1, s2, i, j) in cells[: max(0, int(n_seeds))]:
        d = dict(base)
        if x_key and i < len(xs):
            d[x_key] = float(xs[i])
        if y_key and j < len(ys):
            d[y_key] = float(ys[j])
        # Seed provenance for multi-island optimization
        try:
            isl = int(labels[j][i]) if labels and j < len(labels) and i < len(labels[j]) else -1
        except Exception:
            isl = -1
        d["_seed_meta"] = {
            "intent": str(it),
            "island_id": isl,
            "i": int(i),
            "j": int(j),
            "x_key": x_key,
            "y_key": y_key,
        }
        seeds.append(d)

    info = {
        "x_key": x_key,
        "y_key": y_key,
        "x_lo": float(min(xs)) if xs else float('nan'),
        "x_hi": float(max(xs)) if xs else float('nan'),
        "y_lo": float(min(ys)) if ys else float('nan'),
        "y_hi": float(max(ys)) if ys else float('nan'),
        "n_components": int(len(sizes)),
        "component_sizes": sizes,
        "selected_island": island,
    }
    return seeds, info


def _repo_runs_root(repo_root: Path) -> Path:
    return (repo_root / RUNS_REL).resolve()


def _pending_root(repo_root: Path) -> Path:
    return (repo_root / PENDING_REL).resolve()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _list_run_dirs(repo_root: Path) -> List[Path]:
    root = _repo_runs_root(repo_root)
    if not root.exists():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name, reverse=True)  # newest first
    return dirs


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_progress(run_dir: Path) -> Optional[Dict[str, Any]]:
    return _read_json(run_dir / "progress.json")


def _zip_dir_bytes(dir_path: Path) -> bytes:
    """Create an in-memory zip (deterministic ordering)."""
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        files: List[Path] = []
        for p in dir_path.rglob("*"):
            if p.is_file():
                files.append(p)
        files.sort(key=lambda p: str(p.relative_to(dir_path)).replace(os.sep, "/"))
        for p in files:
            arc = str(p.relative_to(dir_path)).replace(os.sep, "/")
            zf.write(p, arcname=arc)
    return buf.getvalue()


def _default_knobs() -> List[KnobSpec]:
    """Conservative starter knob set (user can edit)."""
    return [
        KnobSpec("R0_m", 4.5, 9.0, True),
        KnobSpec("a_m", 1.2, 3.0, True),
        KnobSpec("kappa", 1.6, 2.3, True),
        KnobSpec("delta", 0.25, 0.6, True),
        KnobSpec("Bt_T", 4.0, 7.5, True),
        KnobSpec("Ip_MA", 8.0, 20.0, True),
        KnobSpec("n_frac_GW", 0.6, 1.1, True),
        KnobSpec("H98", 0.9, 1.3, True),
    ]


def _render_boundary_banner() -> None:
    st.info(
        "External Selection Layer: this console launches an external client that queries the frozen SHAMS evaluator. "
        "It does not modify physics, constraints, or truth. Candidates are selected from feasible points only.",
        icon="🧱",
    )


def _get_proc_state() -> Dict[str, Any]:
    return st.session_state.setdefault("_extopt_proc_v230", {})


def _launch_client(repo_root: Path, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    """Launch external client. Returns (ok, message)."""
    runs_root = _repo_runs_root(repo_root)
    pending = _pending_root(repo_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    pending.mkdir(parents=True, exist_ok=True)

    # Write config into pending area (immutable once launched).
    cfg_bytes = json.dumps(cfg, indent=2, sort_keys=True).encode("utf-8")
    cfg_hash = _sha256_bytes(cfg_bytes)[:12]
    ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    cfg_name = f"optcfg_{ts}_{cfg_hash}.json"
    cfg_path = pending / cfg_name
    cfg_path.write_bytes(cfg_bytes)

    client = (repo_root / "clients" / "feasible_optimizer_client" / "feasible_opt.py").resolve()
    if not client.exists():
        return False, f"Missing client script: {client}"

    cmd = [
        sys.executable,
        str(client),
        "--config",
        str(cfg_path),
        "--repo-root",
        str(repo_root.resolve()),
    ]

    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(repo_root.resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        return False, f"Failed to start optimizer client: {e}"

    state = _get_proc_state()
    state.clear()
    state["pid"] = p.pid
    state["popen"] = p
    state["cfg_path"] = str(cfg_path)
    state["handshake_path"] = str(cfg_path.with_suffix(".run_dir.txt"))
    state["stdout_tail"] = []

    return True, "Launched external optimizer client."


def _poll_process() -> Tuple[Optional[int], Optional[Path]]:
    """Poll running process. Returns (returncode, run_dir)."""
    state = _get_proc_state()
    p: subprocess.Popen | None = state.get("popen")
    if p is None:
        return None, None

    # Capture incremental output (bounded).
    tail: List[str] = state.setdefault("stdout_tail", [])
    try:
        if p.stdout is not None:
            for _ in range(30):
                line = p.stdout.readline()
                if not line:
                    break
                tail.append(line.rstrip("\n"))
            if len(tail) > 250:
                state["stdout_tail"] = tail[-250:]
    except Exception:
        pass

    rc = p.poll()

    run_dir = None
    hs = state.get("handshake_path")
    if hs and Path(hs).exists():
        try:
            run_dir = Path(Path(hs).read_text(encoding="utf-8").strip())
        except Exception:
            run_dir = None

    return rc, run_dir


def _render_knob_table(knobs: List[KnobSpec]) -> List[KnobSpec]:
    st.caption("Choose the knobs to sample and their bounds. Only enabled knobs are sampled.")
    rows = [{"enabled": k.enabled, "knob": k.name, "lo": k.lo, "hi": k.hi} for k in knobs]
    edited = st.data_editor(
        rows,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "enabled": st.column_config.CheckboxColumn("Enabled", width="small"),
            "knob": st.column_config.TextColumn("Knob", width="medium"),
            "lo": st.column_config.NumberColumn("Min", width="small"),
            "hi": st.column_config.NumberColumn("Max", width="small"),
        },
        key="extopt_knob_editor_v230",
    )
    out: List[KnobSpec] = []
    for r in edited:
        try:
            name = str(r.get("knob", "")).strip()
            if not name:
                continue
            lo = float(r.get("lo"))
            hi = float(r.get("hi"))
            enabled = bool(r.get("enabled", True))
            out.append(KnobSpec(name=name, lo=lo, hi=hi, enabled=enabled))
        except Exception:
            continue
    return out


def render_external_optimizer_launcher(repo_root: Path) -> None:
    """Pareto Lab deck: configure + run external optimizer."""
    st.subheader("🧭 Feasible Optimizer (External)")
    _render_boundary_banner()

    # Defaults persisted in session state.
    knobs0 = st.session_state.setdefault("_extopt_default_knobs_v230", [k.__dict__ for k in _default_knobs()])
    knobs = [KnobSpec(**d) for d in knobs0]
    
    # --- Strategy & robustness controls (v241+) ---
    c1, c2, c3 = st.columns([1.2, 1.0, 1.0])
    with c1:
        strategy_label = st.selectbox(
            "Strategy",
            ["Random", "Scan-seeded pattern", "Boundary trace (frontier)", "Boundary trace (frontier families)"],
            index=int(st.session_state.get("extopt_strategy_idx_v241", 1)),
            key="extopt_strategy_label_v241",
            help="Random sampling, cartography-seeded local search, or boundary tracing along the feasibility frontier.",
        )
        st.session_state["extopt_strategy_idx_v241"] = ["Random","Scan-seeded pattern","Boundary trace (frontier)","Boundary trace (frontier families)"].index(strategy_label)
        mech_mode_label = st.selectbox(
            "Mechanism steering",
            ["Neutral", "Avoid mechanism switches", "Seek mechanism switches"],
            index=int(st.session_state.get("extopt_mech_switch_mode_idx_v252", 0)),
            key="extopt_mech_switch_mode_label_v252",
            help="Client-side guidance only: conditions proposal scoring on mechanism classes. Does not modify evaluator truth.",
        )
        st.session_state["extopt_mech_switch_mode_idx_v252"] = ["Neutral","Avoid mechanism switches","Seek mechanism switches"].index(mech_mode_label)
    with c2:
        scenario_robust = st.checkbox(
            "Scenario robustness",
            value=bool(st.session_state.get("extopt_scenario_robust_v241", False)),
            key="extopt_scenario_robust_v241",
            help="Evaluate feasible candidates on a deterministic scenario cube (multiplicative factors) and select robust designs.",
        )
    with c3:
        scenario_max = st.number_input(
            "Scenario max",
            min_value=1,
            max_value=128,
            value=int(st.session_state.get("extopt_scenario_max_v241", 16)),
            step=1,
            key="extopt_scenario_max_v241",
            help="Max number of scenario corners evaluated per candidate (deterministic truncation).",
        )

    scenario_factors: Dict[str, List[float]] = st.session_state.get("extopt_scenario_factors_v241") or {}
    with st.expander("Scenario factors (multiplicative, deterministic)", expanded=False):
        st.caption("Keys must match PointInputs fields (e.g., Paux_MW, fG, Ti_keV). Only numeric present keys are perturbed.")
                # v246.0: UQ-lite scenario library presets (authority + intent)
        preset_options = ["(custom)", "proxy", "parametric", "external"]
        try:
            from tools.scenario_library import preset_names  # type: ignore
            preset_options = ["(custom)"] + preset_names()
        except Exception:
            pass

        # Persist index robustly even if option set changes between versions.
        idx0 = int(st.session_state.get("extopt_scenario_preset_idx_v242", 0))
        idx0 = max(0, min(idx0, len(preset_options) - 1))

        scenario_preset = st.selectbox(
            "Scenario preset",
            preset_options,
            index=idx0,
            key="extopt_scenario_preset_v242",
            help="Fixed, deterministic UQ-lite presets tied to authority tiers and intent. If not (custom) and scenario_factors is empty, the client auto-populates from the library.",
        )
        st.session_state["extopt_scenario_preset_idx_v242"] = int(preset_options.index(scenario_preset))

        if not scenario_factors:
            # Auto-fill from library when preset is not custom; otherwise keep a minimal editable default.
            if str(scenario_preset).strip().lower() not in ("(custom)", "custom"):
                try:
                    from tools.scenario_library import get_preset  # type: ignore
                    scenario_factors = get_preset(str(scenario_preset))
                except Exception:
                    scenario_factors = {"Paux_MW":[0.95,1.05], "fG":[0.95,1.05], "Ti_keV":[0.95,1.05]}
            else:
                scenario_factors = {"Paux_MW":[0.95,1.05], "fG":[0.95,1.05], "Ti_keV":[0.95,1.05]}
        sf_text = st.text_area(
            "scenario_factors (JSON)",
            value=json.dumps(scenario_factors, indent=2, sort_keys=True),
            height=120,
            key="extopt_scenario_factors_text_v241",
        )
        try:
            sf_parsed = json.loads(sf_text)
            if isinstance(sf_parsed, dict):
                scenario_factors = sf_parsed
                st.session_state["extopt_scenario_factors_v241"] = scenario_factors
                st.success("Scenario factors parsed.")
            else:
                st.warning("scenario_factors must be a JSON object.")
        except Exception as e:
            st.warning(f"Invalid JSON: {e}")

    # Boundary trace parameters
    with st.expander("Boundary trace parameters", expanded=(strategy_label in ("Boundary trace (frontier)", "Boundary trace (frontier families)"))):
        boundary_steps = st.number_input("Boundary steps", min_value=1, max_value=10000, value=int(st.session_state.get("extopt_boundary_steps_v241", 30)), step=1, key="extopt_boundary_steps_v241")
        boundary_tol = st.number_input("Boundary tol (margin)", min_value=0.0001, max_value=1.0, value=float(st.session_state.get("extopt_boundary_tol_v241", 0.02)), step=0.01, key="extopt_boundary_tol_v241")
        boundary_step_frac = st.number_input("Boundary step frac", min_value=0.001, max_value=0.5, value=float(st.session_state.get("extopt_boundary_step_frac_v241", 0.05)), step=0.01, key="extopt_boundary_step_frac_v241")
# v233: optional Scan Lab seeding
    use_scan = False
    seeds: List[Dict[str, Any]] = []
    scan_info: Dict[str, Any] = {}

    c1, c2 = st.columns([2, 1], vertical_alignment="top")
    with c1:
        knobs = _render_knob_table(knobs)
        st.session_state["_extopt_default_knobs_v230"] = [k.__dict__ for k in knobs]

        st.markdown("#### 🗺️ Seed from Scan Lab (cartography)")
        scan_art = _scan_artifact_from_session()
        use_scan = st.toggle("Use last Scan Lab cartography as seed source", value=False, key="extopt_use_scan_v233")
        seeds: List[Dict[str, Any]] = []
        scan_info: Dict[str, Any] = {}
        if use_scan:
            if not isinstance(scan_art, dict):
                st.warning("No Scan Lab cartography artifact found in this session. Run Scan Lab first.", icon="🧭")
            else:
                rep = scan_art.get("report") if isinstance(scan_art.get("report"), dict) else scan_art
                intents = list(rep.get("intents") or ["Reactor"])
                it = st.selectbox("Intent lens for seeding", intents, index=0, key="extopt_scan_intent_v233")
                island_mode = st.selectbox("Feasible island", ["largest", "all"], index=0, key="extopt_scan_island_v233")
                n_seeds = st.slider("Number of robust seeds", min_value=1, max_value=50, value=12, step=1, key="extopt_scan_nseeds_v233")
                seeds, scan_info = _extract_scan_seeds(scan_art, intent=str(it), n_seeds=int(n_seeds), island=str(island_mode))
                if not seeds:
                    st.warning("No feasible seeds extracted (check intent/island).", icon="⚠️")
                else:
                    st.success(f"Extracted {len(seeds)} robust feasible seed(s) from Scan Lab.", icon="🧬")
                    cA, cB, cC = st.columns(3)
                    cA.metric("Scan x knob", scan_info.get("x_key","—"))
                    cB.metric("Scan y knob", scan_info.get("y_key","—"))
                    cC.metric("Feasible components", scan_info.get("n_components","—"))
                    # Optional: offer to auto-add scan x/y knobs to the knob table if missing
                    if st.button("Auto-add scan x/y knobs to bounds", use_container_width=True, key="extopt_autobounds_v233"):
                        xk = str(scan_info.get("x_key","")).strip()
                        yk = str(scan_info.get("y_key","")).strip()
                        def _has(nm: str) -> bool:
                            return any(k.name == nm for k in knobs)
                        if xk and not _has(xk):
                            knobs.append(KnobSpec(xk, float(scan_info.get("x_lo",0.0)), float(scan_info.get("x_hi",1.0)), True))
                        if yk and not _has(yk):
                            knobs.append(KnobSpec(yk, float(scan_info.get("y_lo",0.0)), float(scan_info.get("y_hi",1.0)), True))
                        st.session_state["_extopt_default_knobs_v230"] = [k.__dict__ for k in knobs]
                        st.rerun()

    with c2:
        st.markdown("#### Design intent")
        design_intent = st.selectbox(
            "Intent (affects defaults; does not modify truth)",
            ["Reactor", "Research"],
            index=0,
            key="extopt_design_intent_v235",
        )
        # A1: set robustness-first default by intent (only if user hasn't set it yet)
        if "extopt_robust_first_v234" not in st.session_state:
            st.session_state["extopt_robust_first_v234"] = (str(design_intent).lower() == "reactor")
        # v238: Hybrid guidance combines (sensitivities → mechanism steering → surrogate) in a deterministic, auditable way.
        if "extopt_hybrid_guidance_v238" not in st.session_state:
            st.session_state["extopt_hybrid_guidance_v238"] = (str(design_intent).lower() == "reactor")
        hybrid_guidance = st.toggle(
            "Hybrid guidance (sensitivities → mechanism → surrogate)",
            value=bool(st.session_state.get("extopt_hybrid_guidance_v238", False)),
            key="extopt_hybrid_guidance_v238",
            help="Forces the safe ordering: sensitivities first (if available), then mechanism-informed steering, then surrogate-guided sampling. External selection only."
        )
        if hybrid_guidance:
            # Force-enable constituent guidance components (UI remains explicit; evaluator truth unchanged).
            st.session_state["extopt_constraint_aware_v235"] = True
            st.session_state["extopt_sensitivity_step_v237"] = True
            st.session_state["extopt_surrogate_guidance_v236"] = True
            st.session_state["extopt_mechanism_classifier_v240"] = True
        constraint_aware = st.toggle("Constraint-aware steering (dominant-driver guided)", value=True, key="extopt_constraint_aware_v235")
        sensitivity_step = st.toggle("Sensitivity step guidance (Newton-lite)", value=True, key="extopt_sensitivity_step_v237", help="Uses signed margin sensitivities (if available) to try a single directed step before coordinate search. External selection only.")
        multi_island = st.toggle("Multi-island optimization (seed groups)", value=True, key="extopt_multi_island_v235")
        surrogate_guidance = st.toggle("Mechanism-conditioned surrogate guidance", value=True, key="extopt_surrogate_guidance_v236", help="Bias sampling toward feasible regions learned online (per dominant mechanism). External selection only; never modifies physics truth.")

        mechanism_classifier = st.toggle(
            "Mechanism-conditioned feasibility classifier (pre-filter proposals)",
            value=True,
            key="extopt_mechanism_classifier_v240",
            help="Learns P(feasible|x, mechanism) online and uses it to score/filter proposal batches before evaluator calls. External selection only."
        )
        with st.expander("Classifier tuning (deterministic)", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.number_input("min pos", min_value=5, max_value=200, value=int(st.session_state.get("extopt_mech_min_pos_v240", 10)), step=1, key="extopt_mech_min_pos_v240", help="Minimum feasible samples before classifier is used.")
            with c2:
                st.number_input("min neg", min_value=5, max_value=200, value=int(st.session_state.get("extopt_mech_min_neg_v240", 10)), step=1, key="extopt_mech_min_neg_v240", help="Minimum failures for a mechanism before classifier is used for that mechanism.")
            with c3:
                st.number_input("batch", min_value=8, max_value=512, value=int(st.session_state.get("extopt_mech_batch_v240", 64)), step=8, key="extopt_mech_batch_v240", help="Number of candidates scored per proposal batch.")

        st.markdown("#### Feasibility policy")
        policy = st.radio(
            "Candidate acceptance",
            ["Strict PASS only", "PASS + DIAG allowed"],
            index=0,
            key="extopt_policy_v230",
        )
        st.markdown("#### Objective contract")
        objective = st.selectbox(
            "Objective (feasible-only)",
            ["P_net_MW", "CAPEX_$", "recirc_frac", "ignition_margin", "P_fus_MW"],
            index=0,
            key="extopt_objective_v230",
        )
        robustness_first = st.toggle("Robustness-first selection (maximize min signed margin first)", value=True, key="extopt_robust_first_v234")
        st.caption("If enabled: candidates are ranked by worst hard-constraint margin first, then by the objective contract. Feasible-only still applies.")
        st.markdown("#### Run control")
        n = st.number_input("Evaluation budget N", min_value=5, max_value=5000, value=200, step=10, key="extopt_n_v230")
        seed = st.number_input("Deterministic seed", min_value=0, max_value=10_000_000, value=0, step=1, key="extopt_seed_v230")
        tag = st.text_input("Run tag (optional)", value="", key="extopt_tag_v230")

    enabled = [k for k in knobs if k.enabled]
    problems: List[str] = []
    if not enabled:
        problems.append("Enable at least one knob.")
    for k in enabled:
        if not (k.hi > k.lo):
            problems.append(f"Invalid bounds for {k.name}: max must be > min.")
    if problems:
        st.warning(" | ".join(problems), icon="⚠️")

    st.markdown("### Run status")
    state = _get_proc_state()
    rc, run_dir = _poll_process()

    cols = st.columns(4)
    running = (state.get("popen") is not None) and (rc is None)
    cols[0].metric("Process", "Running" if running else ("Idle" if state.get("popen") is None else f"Exit {rc}"))
    cols[1].metric("PID", state.get("pid", "—"))
    cols[2].metric("Run dir", (run_dir.name if run_dir else "—"))
    prog = _load_progress(run_dir) if run_dir else None
    cols[3].metric("Feasible so far", (prog.get("n_feasible") if prog else "—"))

    if run_dir:
        if prog:
            frac = float(prog.get("i", 0)) / max(1.0, float(prog.get("n", 1)))
            st.progress(min(1.0, max(0.0, frac)))
            st.caption(
                f"i={prog.get('i')}/{prog.get('n')} | feasible={prog.get('n_feasible')} | "
                f"last={prog.get('last_verdict','—')} | dominant={prog.get('last_dominant','—')}"
            )
        else:
            st.caption("Progress file not yet available.")

    disabled = bool(problems) or running
    if st.button("Run external optimizer", type="primary", disabled=disabled, use_container_width=True, key="extopt_run_btn_v230"):
        cfg = {
            "schema": "extopt_config.v251",
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tag": str(tag),
            "seed": int(seed),
            "n": int(n),
            "objective": str(objective),
            "objective_contract": _objective_contract_v2(
                str(objective),
                direction=("min" if str(objective) in ("CAPEX_$", "recirc_frac") else "max"),
                robustness_first=bool(robustness_first),
                scenario_robustness_required=bool(scenario_robust),
                design_intent=str(st.session_state.get("extopt_design_intent_v235","Reactor")),
            ),
            "design_intent": str(st.session_state.get("extopt_design_intent_v235","Reactor")),

            "robustness_first": bool(robustness_first),
            "constraint_aware": bool(st.session_state.get("extopt_constraint_aware_v235", True)),
            "multi_island": bool(st.session_state.get("extopt_multi_island_v235", True)),
            "hybrid_guidance": bool(st.session_state.get("extopt_hybrid_guidance_v238", False)),
            "surrogate_guidance": bool(st.session_state.get("extopt_surrogate_guidance_v236", True)),
            "sensitivity_step": bool(st.session_state.get("extopt_sensitivity_step_v237", True)),
            "sens_step_frac": float(st.session_state.get("extopt_sens_step_frac_v237", 0.05)),
            "mechanism_classifier": bool(st.session_state.get("extopt_mechanism_classifier_v240", True)),
            "mechanism_switch_mode": {"Neutral":"neutral", "Avoid mechanism switches":"avoid", "Seek mechanism switches":"seek"}.get(str(st.session_state.get("extopt_mech_switch_mode_label_v252","Neutral")), "neutral"),
            "mech_min_pos": int(st.session_state.get("extopt_mech_min_pos_v240", 10)),
            "mech_min_neg": int(st.session_state.get("extopt_mech_min_neg_v240", 10)),
            "mech_batch": int(st.session_state.get("extopt_mech_batch_v240", 64)),
            "policy": "strict_pass" if policy.startswith("Strict") else "pass_plus_diag",
            "objective_direction": ("min" if str(objective) in ("CAPEX_$", "recirc_frac") else "max"),
            "strategy": {"Random":"random", "Scan-seeded pattern":"scan_seeded_pattern", "Boundary trace (frontier)":"boundary_trace", "Boundary trace (frontier families)":"boundary_trace_multi"}.get(strategy_label, "random"),
            "seeds": (seeds if strategy_label != "Random" else []),
            "seed_source": (scan_info if strategy_label != "Random" else {}),

            "scenario_robustness": bool(scenario_robust),
            "scenario_max": int(scenario_max),
            "scenario_factors": (scenario_factors if isinstance(scenario_factors, dict) else {}),
            "scenario_preset": ("custom" if str(st.session_state.get("extopt_scenario_preset_v242","(custom)")).startswith("(") else str(st.session_state.get("extopt_scenario_preset_v242","custom"))),
            "boundary_steps": int(st.session_state.get("extopt_boundary_steps_v241", 30)),
            "boundary_tol": float(st.session_state.get("extopt_boundary_tol_v241", 0.02)),
            "boundary_step_frac": float(st.session_state.get("extopt_boundary_step_frac_v241", 0.05)),

            "bounds": {k.name: [k.lo, k.hi] for k in enabled},
            "fixed": {},
            "caps": {},
        }
        ok, msg = _launch_client(repo_root, cfg)
        (st.success if ok else st.error)(msg)

    with st.expander("Client log tail (read-only)", expanded=False):
        tail: List[str] = state.get("stdout_tail", [])
        if tail:
            st.code("\n".join(tail[-100:]))
        else:
            st.caption("No client output captured yet.")


def render_optimizer_evidence_packs(repo_root: Path) -> None:
    """Pareto Lab deck: browse/inspect/export optimization evidence packs."""
    st.subheader("📦 Optimization Evidence Packs")
    _render_boundary_banner()

    run_dirs = _list_run_dirs(repo_root)
    if not run_dirs:
        st.warning("No optimizer runs found yet. Run one from the 'Feasible Optimizer (External)' deck.", icon="📭")
        return

    names = [p.name for p in run_dirs]
    sel = st.selectbox("Select a run", names, index=0, key="extopt_pack_sel_v230")
    run_dir = _repo_runs_root(repo_root) / sel

    meta = _read_json(run_dir / "meta.json") or {}
    cfg = _read_json(run_dir / "run_config.json")
    obj_contract = _read_json(run_dir / "objective_contract.json")
    proof = _read_json(run_dir / "frontier_proof_pack.json")
    proof_all = _read_json(run_dir / "frontier_proof_pack_all_islands.json") or {}
    fam_gal = _read_json(run_dir / "optimizer_family_gallery.json") or {}
    summary = _read_json(run_dir / "summary.json") or {}
    best = _read_json(run_dir / "best.json") or {}

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("N", meta.get("n", cfg.get("n", "—")))
    k2.metric("Feasible", meta.get("n_feasible", "—"))
    k3.metric("Objective", meta.get("objective", cfg.get("objective", "—")))
    k4.metric("Elapsed (s)", meta.get("elapsed_wall_s", "—"))

    # Robust Pareto view: objective vs worst hard margin (feasible-only)
    recs = _read_json(run_dir / "records.json") or []
    if isinstance(recs, list) and recs:
        pts = [r for r in recs if isinstance(r, dict) and r.get("candidate")]
        if pts:
            obj_key = str(cfg.get("objective", meta.get("objective", "objective")))
            data = {
                "objective": [float(p.get("objective", float('nan'))) for p in pts],
                "worst_hard_margin": [float(p.get("worst_hard_margin", float('nan'))) for p in pts],
            }
            st.markdown("#### 📈 Robust Pareto (feasible-only)")
            st.scatter_chart(data)
            # Show top candidates by robustness then objective
            pts_sorted = sorted(
                pts,
                key=lambda r: (-(float(r.get("worst_hard_margin", float('-inf'))) if r.get("worst_hard_margin") is not None else float('-inf')), float(r.get("objective", float('nan')))),
            )
            st.dataframe([
                {
                    "i": p.get("i"),
                    "objective": p.get("objective"),
                    "worst_hard_margin": p.get("worst_hard_margin"),
                    "dominant_mechanism": p.get("dominant_mechanism"),
                    "dominant_constraint": p.get("dominant_constraint"),
                }
                for p in pts_sorted[: min(25, len(pts_sorted))]
            ])
        else:
            st.info("No feasible candidates recorded in this run.")
    

    # Scenario-robust view (if scenario metrics exist)
    if isinstance(recs, list) and recs:
        pts2 = [r for r in recs if isinstance(r, dict) and r.get("candidate") and ("scenario_pass_frac" in r or "scenario_worst_hard_margin" in r)]
        if pts2:
            st.markdown("#### 🧪 Scenario robustness (feasible-only)")
            data2 = {
                "scenario_pass_frac": [float(p.get("scenario_pass_frac", float('nan'))) for p in pts2],
                "scenario_worst_hard_margin": [float(p.get("scenario_worst_hard_margin", float('nan'))) for p in pts2],
            }
            st.scatter_chart(data2)
            st.dataframe([
                {
                    "i": p.get("i"),
                    "scenario_pass_frac": p.get("scenario_pass_frac"),
                    "scenario_worst_hard_margin": p.get("scenario_worst_hard_margin"),
                    "objective": p.get("objective"),
                    "dominant_mechanism": p.get("dominant_mechanism"),
                }
                for p in sorted(pts2, key=lambda r: (-(float(r.get("scenario_pass_frac", -1.0))), -(float(r.get("scenario_worst_hard_margin", -1e9))), -(float(r.get("worst_hard_margin", -1e9)))) )[:25]
            ])


    # v252: Optimization family gallery
    if isinstance(fam_gal, dict) and fam_gal.get("schema") == "optimizer_family_gallery.v1":
        with st.expander("🧬 Family Gallery (feasible-only)", expanded=False):
            fams = fam_gal.get("families") or []
            if not fams:
                st.caption("No feasible families found.")
            else:
                labels = [f"Family {f.get('family_id')} (N={f.get('n_feasible')})" for f in fams]
                sel_i = st.selectbox("Select family", list(range(len(labels))), format_func=lambda i: labels[i], index=0, key="extopt_fam_sel_v252")
                f = fams[int(sel_i)]
                c1, c2, c3 = st.columns(3)
                c1.metric("Family ID", f.get("family_id"))
                c2.metric("Feasible N", f.get("n_feasible"))
                c3.metric("Objective key", f.get("objective_key"))
                st.markdown("**Worst hard margin stats**")
                st.json(f.get("worst_hard_margin", {}), expanded=False)
                st.markdown("**Objective stats**")
                st.json(f.get("objective", {}), expanded=False)
                st.markdown("**Representatives**")
                st.json(f.get("representatives", {}), expanded=False)
                # Quick lookup of representative records
                reps = f.get("representatives", {}) or {}
                recs = _read_json(run_dir / "records.json") or []
                for rname in ("robust_best", "objective_best"):
                    rr = (reps.get(rname) or {})
                    ridx = rr.get("record_index")
                    if isinstance(ridx, int) and 0 <= ridx < len(recs):
                        with st.expander(f"Show {rname} record #{ridx}", expanded=False):
                            st.json(recs[ridx], expanded=False)

    # Boundary frontier artifacts (if boundary_trace strategy was used)
    bf_json = run_dir / "boundary_frontier.json"
    fp_csv = run_dir / "frontier_points.csv"
    if bf_json.exists() or fp_csv.exists():
        with st.expander("🧵 Boundary frontier (constraint surface)", expanded=False):
            if bf_json.exists():
                st.json(_read_json(bf_json))
            if fp_csv.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(fp_csv)
                    st.dataframe(df.head(200))
                except Exception as e:
                    st.caption(f"Could not read frontier_points.csv: {e}")
    
    # Frontier families / atlas (multi-frontier per island)
    ff_sum = run_dir / "frontier_family_summary.json"
    frontiers_dir = run_dir / "frontiers"
    if ff_sum.exists() or (frontiers_dir.exists() and frontiers_dir.is_dir()):
        with st.expander("🗺️ Frontier Atlas (families, islands, mechanisms)", expanded=False):
            if ff_sum.exists():
                try:
                    ff = _read_json(ff_sum) or {}
                    st.caption("Frontier families compare feasibility boundaries across scan-seeded islands (feasible-only, external optimizer).")
                    # Summary table
                    fam = ff.get("families", []) or ff.get("islands", []) or []
                    if isinstance(fam, list) and fam:
                        st.markdown("**Island summary**")
                        st.dataframe([{
                            "island_id": d.get("island_id"),
                            "frontier_n": d.get("frontier_n", d.get("n")),
                            "best_objective": d.get("best_objective"),
                            "worst_hard_margin_min": d.get("worst_hard_margin_min"),
                            "dominant_mechanism_top": d.get("dominant_mechanism_top"),
                        } for d in fam])
                    else:
                        st.json(ff)
                    try:
                        st.download_button("Download family summary JSON", data=ff_sum.read_bytes(), file_name=ff_sum.name, mime="application/json")
                    except Exception:
                        pass
                except Exception as e:
                    st.caption(f"Could not read frontier_family_summary.json: {e}")

            # List available frontier CSVs
            fcsvs = []
            if frontiers_dir.exists() and frontiers_dir.is_dir():
                try:
                    fcsvs = sorted([p for p in frontiers_dir.glob('*.csv') if p.is_file()], key=lambda p: p.name)
                except Exception:
                    fcsvs = []
            # Backwards-compat: single frontier_points.csv
            if (run_dir / "frontier_points.csv").exists():
                fcsvs = fcsvs + [run_dir / "frontier_points.csv"]

            if not fcsvs:
                st.info("No frontier CSV files found in this run.")
            else:
                names = [p.name for p in fcsvs]
                sel_f = st.selectbox("Select a frontier CSV", names, index=0, key="frontier_atlas_sel_csv_v243")
                fpath = None
                for p in fcsvs:
                    if p.name == sel_f:
                        fpath = p
                        break
                if fpath is not None:
                    try:
                        import pandas as pd
                        df = pd.read_csv(fpath)
                        st.markdown("**Preview**")
                        st.dataframe(df.head(200))
                        # Choose axes for a compact atlas scatter
                        num_cols = [c for c in df.columns if c not in ('dominant_mechanism','dominant_constraint') and pd.api.types.is_numeric_dtype(df[c])]
                        if len(num_cols) >= 2:
                            # Prefer common axes if present
                            def _pick(preferred):
                                for k in preferred:
                                    if k in num_cols:
                                        return k
                                return num_cols[0]
                            x_default = _pick(['objective','worst_hard_margin','R0_m','Bt_T','Ip_MA','a_m'])
                            y_default = _pick(['worst_hard_margin','objective','Bt_T','R0_m','q95','fg','Pnet_MW'])
                            c1, c2 = st.columns(2)
                            with c1:
                                xcol = st.selectbox("X axis", num_cols, index=num_cols.index(x_default) if x_default in num_cols else 0, key="frontier_atlas_x_v243")
                            with c2:
                                ycol = st.selectbox("Y axis", num_cols, index=num_cols.index(y_default) if y_default in num_cols else 1, key="frontier_atlas_y_v243")
                            st.markdown("**Frontier scatter**")
                            st.scatter_chart({"x": [float(v) for v in df[xcol].tolist()], "y": [float(v) for v in df[ycol].tolist()]})                        # Mechanism filtering + switch points along frontier (v246.0)
                        try:
                            from tools.frontier_mechanism import (
                                discover_mechanism_column,
                                filter_by_mechanisms,
                                compressed_sequence,
                                transition_counts,
                                compute_switch_points,
                            )
                            mech_col = discover_mechanism_column(list(df.columns))
                        except Exception:
                            mech_col = None

                        if mech_col:
                            all_mechs = sorted({str(x) for x in df[mech_col].fillna("—").astype(str).tolist()})
                            sel = st.multiselect(
                                "Mechanism filter",
                                options=all_mechs,
                                default=all_mechs,
                                key="frontier_mech_filter_v246",
                                help="Filter points by dominant mechanism (UI only). Frontier ordering remains CSV row order.",
                            )
                            dff = filter_by_mechanisms(df, mech_col, sel)
                            seq = [str(s) for s in dff[mech_col].fillna("—").tolist()]
                            st.markdown("**Mechanism sequence (compressed, filtered)**")
                            comp = compressed_sequence(seq, max_len=80)
                            st.write(" → ".join(comp) + (" …" if len(comp) >= 80 else ""))

                            rows = transition_counts(seq)
                            if rows:
                                st.markdown("**Mechanism transitions (filtered)**")
                                st.dataframe(rows[:200], use_container_width=True, hide_index=True)

                            sp = compute_switch_points(dff, mech_col=mech_col, xcol=xcol, ycol=ycol, max_points=300)
                            if sp:
                                with st.expander("Mechanism switch points (row-order indices)", expanded=False):
                                    st.dataframe(sp, use_container_width=True, hide_index=True)
                        
                        try:
                            st.download_button("Download selected frontier CSV", data=fpath.read_bytes(), file_name=fpath.name, mime="text/csv")
                        except Exception:
                            pass
                    except Exception as e:
                        st.caption(f"Could not read frontier CSV: {e}")

        # Micro-atlas: small multiples per island (compact, expert-friendly)
        # Goal: compare islands at a glance without scrolling. Uses one global axis pick and renders
        # a grid of small scatter views + mechanism overlays.
        with st.expander("🧩 Frontier Micro-Atlas (island small multiples)", expanded=False):
            try:
                import pandas as pd
            except Exception:
                pd = None

            fam = []
            if ff_sum.exists():
                ff = _read_json(ff_sum) or {}
                fam = ff.get("families", []) or ff.get("islands", []) or []
                if not isinstance(fam, list):
                    fam = []

            # Discover per-island frontier CSVs
            island_csv = {}
            if frontiers_dir.exists() and frontiers_dir.is_dir():
                for p in sorted([q for q in frontiers_dir.glob("*.csv") if q.is_file()], key=lambda x: x.name):
                    # Expected: frontier_island_<id>.csv
                    name = p.stem
                    if "frontier_island_" in name:
                        try:
                            island_id = name.split("frontier_island_")[-1]
                            island_csv[str(island_id)] = p
                        except Exception:
                            continue

            if not island_csv and (run_dir / "frontier_points.csv").exists():
                island_csv["single"] = (run_dir / "frontier_points.csv")

            if not island_csv:
                st.info("No island frontier CSVs found for this run.")
            else:
                # Decide which islands to render
                ids = sorted(island_csv.keys(), key=lambda s: (s != "single", s))
                # Prefer ordering from family summary if present
                if fam:
                    fam_ids = [str(d.get("island_id")) for d in fam if isinstance(d, dict) and d.get("island_id") is not None]
                    ids = [i for i in fam_ids if i in island_csv] + [i for i in ids if i not in fam_ids]

                cA, cB, cC = st.columns([2, 2, 2])
                with cA:
                    max_islands = st.slider("Max islands", 1, 12, min(6, len(ids)), key="micro_atlas_max_islands_v244")
                with cB:
                    cols_per_row = st.selectbox("Columns", [2, 3, 4], index=1, key="micro_atlas_cols_v244")
                with cC:
                    show_tables = st.checkbox("Show mini tables", value=True, key="micro_atlas_tables_v244")


                # Optional: rank islands by robustness envelope (max worst_hard_margin, then objective)
                rank_by_envelope = st.checkbox("Rank islands by robustness envelope", value=True, key="micro_atlas_rank_v245")
                color_by_mech = st.checkbox("Color points by mechanism", value=True, key="micro_atlas_color_mech_v245")

                ids = ids[:max_islands]
                # Compute envelope metrics and optionally reorder islands for rendering
                envelope_rows = []
                if pd is not None:
                    for iid in ids:
                        try:
                            dfi = pd.read_csv(island_csv[iid])
                            if "worst_hard_margin" in dfi.columns and pd.api.types.is_numeric_dtype(dfi["worst_hard_margin"]):
                                max_margin = float(dfi["worst_hard_margin"].max())
                                obj_at_max = float("nan")
                                if "objective" in dfi.columns and pd.api.types.is_numeric_dtype(dfi["objective"]):
                                    j = int(dfi["worst_hard_margin"].astype(float).idxmax())
                                    try:
                                        obj_at_max = float(dfi.loc[j, "objective"])
                                    except Exception:
                                        obj_at_max = float("nan")
                                envelope_rows.append({
                                    "island_id": iid,
                                    "frontier_n": int(len(dfi)),
                                    "max_worst_hard_margin": max_margin,
                                    "objective_at_max_margin": obj_at_max,
                                })
                        except Exception:
                            continue

                if envelope_rows:
                    def _obj_key(v):
                        try:
                            return float(v)
                        except Exception:
                            return float("nan")

                    envelope_rows_sorted = sorted(
                        envelope_rows,
                        key=lambda r: (
                            -float(r.get("max_worst_hard_margin", -1e9)),
                            float("inf") if (str(r.get("objective_at_max_margin")) == "nan") else _obj_key(r.get("objective_at_max_margin")),
                        ),
                    )

                    if rank_by_envelope:
                        sorted_ids = [str(r["island_id"]) for r in envelope_rows_sorted]
                        ids = [i for i in sorted_ids if i in ids] + [i for i in ids if i not in sorted_ids]

                    st.markdown("**Robustness envelope ranking** (per island)")
                    st.dataframe(envelope_rows_sorted, use_container_width=True, hide_index=True)

                # Choose global axes (based on first readable CSV)
                xcol = ycol = None
                num_cols = []
                if pd is not None:
                    for iid in ids:
                        try:
                            df0 = pd.read_csv(island_csv[iid])
                            num_cols = [
                                c for c in df0.columns
                                if c not in ("dominant_mechanism", "dominant_constraint") and pd.api.types.is_numeric_dtype(df0[c])
                            ]
                            if len(num_cols) >= 2:
                                def _pick(preferred):
                                    for k in preferred:
                                        if k in num_cols:
                                            return k
                                    return num_cols[0]
                                xcol = _pick(["objective", "R0_m", "Bt_T", "Ip_MA", "a_m"]) 
                                ycol = _pick(["worst_hard_margin", "objective", "Bt_T", "R0_m", "q95", "fg", "Pnet_MW"]) 
                            break
                        except Exception:
                            continue

                if pd is None or len(num_cols) < 2:
                    st.warning("Micro-atlas requires pandas and numeric columns in frontier CSVs.")
                else:
                    ax1, ax2 = st.columns(2)
                    with ax1:
                        xcol = st.selectbox("Global X axis", num_cols, index=num_cols.index(xcol) if xcol in num_cols else 0, key="micro_atlas_x_v244")
                    with ax2:
                        ycol = st.selectbox("Global Y axis", num_cols, index=num_cols.index(ycol) if ycol in num_cols else 1, key="micro_atlas_y_v244")

                    # v246.0: Global mechanism filter for micro-atlas (UI only)
                    mech_col = None
                    all_mechs = []
                    try:
                        from tools.frontier_mechanism import discover_mechanism_column  # type: ignore
                        # discover from first readable CSV
                        mech_col = discover_mechanism_column(list(df0.columns)) if 'df0' in locals() else None
                    except Exception:
                        mech_col = None
                    if mech_col:
                        mech_set = set()
                        for iid in ids:
                            try:
                                dfi = pd.read_csv(island_csv[iid])
                                if mech_col in dfi.columns:
                                    for m in dfi[mech_col].fillna('—').astype(str).tolist():
                                        mech_set.add(str(m))
                            except Exception:
                                continue
                        all_mechs = sorted(mech_set)
                        sel_mechs = st.multiselect(
                            'Global mechanism filter',
                            options=all_mechs,
                            default=all_mechs,
                            key='micro_atlas_mech_filter_v246',
                            help='Filter points by dominant mechanism (UI only).',
                        )
                    else:
                        sel_mechs = None

                    # Render small multiples
                    rows = (len(ids) + cols_per_row - 1) // cols_per_row
                    k = 0
                    for _r in range(rows):
                        cols = st.columns(cols_per_row)
                        for c in cols:
                            if k >= len(ids):
                                break
                            iid = ids[k]
                            k += 1
                            with c:
                                st.markdown(f"**Island {iid}**" if iid != "single" else "**Frontier**")
                                try:
                                    df = pd.read_csv(island_csv[iid])

                                    df_plot = df
                                    if mech_col and (sel_mechs is not None):
                                        try:
                                            from tools.frontier_mechanism import filter_by_mechanisms  # type: ignore
                                            df_plot = filter_by_mechanisms(df, mech_col, sel_mechs)
                                        except Exception:
                                            df_plot = df
                                    if hasattr(df_plot, '__len__') and len(df_plot) == 0:
                                        st.caption('No points after mechanism filter.')
                                        continue


                                    # Scatter (small) with optional mechanism coloring (plotly, default palette)
                                    if color_by_mech and (("dominant_mechanism" in df_plot.columns) or ("dominant_mechanism_group" in df_plot.columns)):
                                        try:
                                            import plotly.express as px
                                            mech_col_plot = "dominant_mechanism_group" if "dominant_mechanism_group" in df_plot.columns else "dominant_mechanism"
                                            fig = px.scatter(df_plot, x=xcol, y=ycol, color=mech_col_plot)
                                            fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=220)
                                            st.plotly_chart(fig, use_container_width=True)
                                        except Exception:
                                            st.scatter_chart({
                                                "x": [float(v) for v in df_plot[xcol].tolist()],
                                                "y": [float(v) for v in df_plot[ycol].tolist()],
                                            })
                                    else:
                                        st.scatter_chart({
                                            "x": [float(v) for v in df_plot[xcol].tolist()],
                                            "y": [float(v) for v in df_plot[ycol].tolist()],
                                        })
                                    # Mechanism overlay (filtered)
                                    if mech_col and (mech_col in df_plot.columns):
                                        mech = [str(s) for s in df_plot[mech_col].fillna("—").tolist()]
                                        # counts
                                        counts = {}
                                        for m in mech:
                                            counts[m] = counts.get(m, 0) + 1
                                        top = sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:3]
                                        st.caption("Mech top: " + ", ".join([f"{a}:{b}" for a, b in top]))
                                        # top transitions
                                        trans = {}
                                        for a, b in zip(mech[:-1], mech[1:]):
                                            trans[(a, b)] = trans.get((a, b), 0) + 1
                                        if trans:
                                            (a, b), n = sorted(trans.items(), key=lambda kv: (-int(kv[1]), str(kv[0][0]), str(kv[0][1])))[0]
                                            st.caption(f"Top Δ: {a}→{b} ({n})")

                                    if show_tables:
                                        # Mini metrics table from family summary if available
                                        row = None
                                        for d in fam:
                                            if isinstance(d, dict) and str(d.get("island_id")) == str(iid):
                                                row = d
                                                break
                                        if row is not None:
                                            st.dataframe([{
                                                "frontier_n": row.get("frontier_n", row.get("n")),
                                                "best_obj": row.get("best_objective"),
                                                "min_margin": row.get("worst_hard_margin_min"),
                                                "top_mech": row.get("dominant_mechanism_top"),
                                            }])
                                except Exception as e:
                                    st.caption(f"Could not render island {iid}: {e}")
    # Frontier family narrative (v246.0) — compact publication-ready summary
    fn_md = run_dir / "frontier_family_narrative.md"
    fn_js = run_dir / "frontier_family_narrative.json"
    if fn_md.exists() or fn_js.exists():
        with st.expander("📜 Frontier family narrative", expanded=False):
            if fn_js.exists():
                rep = _read_json(fn_js) or {}
                try:
                    st.write({"ok": rep.get("ok"), "n_islands": len(rep.get("islands_ranked", []) or []), "mechanisms": rep.get("mechanism_coverage")})
                except Exception:
                    pass
            if fn_md.exists():
                try:
                    st.markdown(fn_md.read_text(encoding='utf-8'))
                except Exception:
                    st.caption('Could not render narrative markdown.')

    # Mechanism transition map (publishable search dynamics)
    mt_path = run_dir / "mechanism_transition_map.json"
    if mt_path.exists():
        mt = _read_json(mt_path) or {}
        with st.expander("🧭 Dominant-mechanism transition map", expanded=False):
            try:
                st.write({
                    "sequence_len": mt.get("sequence_len"),
                    "states": mt.get("states"),
                })
            except Exception:
                pass
            # Table view
            try:
                counts = mt.get("state_counts", {}) or {}
                st.markdown("**State counts**")
                st.dataframe([{"state": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))])

                trans = mt.get("transitions_counts", {}) or {}
                rows = []
                for a in sorted(trans.keys()):
                    for b in sorted((trans[a] or {}).keys()):
                        rows.append({"from": a, "to": b, "count": int(trans[a][b])})
                if rows:
                    st.markdown("**Transitions**")
                    st.dataframe(rows)
            except Exception:
                pass
            # Matrix CSV
            csv_path = run_dir / "mechanism_transition_matrix.csv"
            if csv_path.exists():
                try:
                    st.download_button("Download transition matrix CSV", data=csv_path.read_bytes(), file_name=csv_path.name, mime="text/csv")
                except Exception:
                    pass

    # Classifier snapshot (if enabled)
    cl_path = run_dir / "mechanism_classifiers.json"
    if cl_path.exists():
        cl = _read_json(cl_path) or {}
        with st.expander("🧪 Mechanism-conditioned feasibility classifier", expanded=False):
            try:
                st.write({
                    "schema": cl.get("schema"),
                    "min_pos": cl.get("min_pos"),
                    "min_neg": cl.get("min_neg"),
                })
            except Exception:
                pass
            mechs = cl.get("mechanisms", []) or []
            if isinstance(mechs, list) and mechs:
                st.dataframe([{
                    "mechanism": m.get("mechanism"),
                    "n_pos": m.get("n_pos"),
                    "n_neg": m.get("n_neg"),
                } for m in mechs])
            stats = cl.get("filter_stats", {}) or {}
            if stats:
                st.markdown("**Usage stats**")
                st.json(stats)
            try:
                st.download_button("Download classifier JSON", data=cl_path.read_bytes(), file_name=cl_path.name, mime="application/json")
            except Exception:
                pass

    st.caption(f"Strategy: {meta.get('strategy', cfg.get('strategy', 'random'))} | Objective dir: {meta.get('objective_direction', cfg.get('objective_direction', 'max'))} | Seeded: {bool(cfg.get('seeds'))}")


    with st.container(border=True):
        st.markdown("**Run config (read-only)**")
        
        if cfg:
            st.json(cfg)
        else:
            st.caption("No run_config.json found (older run).")


    with st.container(border=True):
        st.markdown("**Objective contract (v2)**")
        if obj_contract:
            st.json(obj_contract)
        else:
            # Fallback to legacy keys from run_config.json
            if cfg and isinstance(cfg, dict) and cfg.get("objective"):
                st.json({
                    "schema": "objective_contract.v2 (derived)",
                    "primary": {"key": cfg.get("objective"), "direction": cfg.get("objective_direction", "max")},
                    "ordering": ["worst_hard_margin", "objective"] if cfg.get("robustness_first", False) else ["objective", "worst_hard_margin"],
                })
            else:
                st.caption("No objective contract found.")
    
    with st.container(border=True):
        st.markdown("**Frontier proof pack**")
        if proof:
            st.json(proof)
        elif proof_all:
            st.json(proof_all)
        else:
            st.caption("No frontier proof pack found (run was not a boundary-tracing strategy).")

    with st.container(border=True):
        st.markdown("**Best feasible (by objective contract)**")
        if best:
            st.json({"i": best.get("i"), "objective": best.get("objective"), "inputs": best.get("inputs", {}), "outputs": best.get("outputs", {})})
        else:
            st.caption("No best.json found (no feasible points or run incomplete).")

    with st.container(border=True):
        st.markdown("**Dominant failure mechanisms (rejected points)**")
        mech = summary.get("dominant_failures", {})
        if isinstance(mech, dict) and mech:
            items = sorted(mech.items(), key=lambda kv: kv[1], reverse=True)[:10]
            st.table([{"dominant_constraint": k, "count": v} for k, v in items])
        else:
            st.caption("No failure mechanism summary found (older run or incomplete).")

    with st.container(border=True):
        st.markdown("**Export evidence pack**")
        if st.button("Build evidence pack ZIP", use_container_width=True, key="extopt_zip_build_v230"):
            data = _zip_dir_bytes(run_dir)
            st.session_state["_extopt_last_zip_bytes_v230"] = data
            st.session_state["_extopt_last_zip_name_v230"] = f"{run_dir.name}.zip"
            st.success(f"ZIP built ({len(data)/1e6:.2f} MB).")

        data = st.session_state.get("_extopt_last_zip_bytes_v230")
        name = st.session_state.get("_extopt_last_zip_name_v230", "evidence_pack.zip")
        if data:
            st.download_button(
                "Download evidence pack ZIP",
                data=data,
                file_name=name,
                mime="application/zip",
                use_container_width=True,
                key="extopt_zip_dl_v230",
            )
