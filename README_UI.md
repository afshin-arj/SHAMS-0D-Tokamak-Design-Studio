# SHAMS — Tokamak Design Authority (UI)
## Navigation

The UI keeps the primary workflows in a small set of tabs (Point Designer, Systems Mode, Scan Lab, Pareto Lab, Reactor Design Forge, **System Suite**, Compare).

## System Suite (Helm)
System Suite is a **read-only system-code overlay** on top of the frozen Point Designer truth. The verdict hero renders first (verdict-first layout); diagnostics are grouped into **six compact tabs** (no scroll walls):

- **Closure & Power** — plant power closure snapshots + SHA-256 stamps
- **Ops · Thermal · Trajectory** — duty/availability, thermal network, and pulse-envelope trajectory diagnostics (sub-tabs)
- **Lifetime · Fuel · Regimes** — static lifetime budgets, tritium closure proxies, and regime-transition labels (sub-tabs)
- **Phase Envelopes** — outer-loop quasi-static phases (worst-phase determines verdict)
- **Profile Contracts** — robust vs optimistic feasibility under certified profile/transport envelopes
- **Authority · Exports · UQ** — scenario library, campaign/parity exports, and uncertainty interval contracts (sub-tabs)

These decks never modify physics truth and never perform recovery iteration.

### Shared deck components (`ui/components/`)
- `kpi_row(items)` — compact horizontal `st.metric` strip used by every diagnostic deck.
- `empty_state(message, kind)` — consistent "no data" / "overlay unavailable" placeholder.
Both are pure presentation; no physics, state, or routing logic.


## Run (Windows)

**NiceGUI (recommended):** double-click `run_ui_nicegui.cmd` → http://127.0.0.1:8080

**Streamlit (legacy):** double-click `run_ui.cmd` → http://127.0.0.1:8501

## Structure
- `src/` : physics & models (your Phase-1 refactor + clean design additions)
- `ui/app.py` : Streamlit UI entrypoint + deck router (legacy; parallel to NiceGUI)
- `ui_nicegui/` : NiceGUI UI (`run_ui_nicegui.cmd` / `launch.py`)
- `ui/decks/` : extracted deck modules (Point Designer, System Suite, ...) — each rendered via a router call in `app.py`
- `ui/components/` : shared presentation components (`kpi_row`, `empty_state`)
- `api.py` : optional FastAPI wrapper (for future Next.js/React UI)

## Notes
- This UI imports `src` directly and does not require Node/JS toolchains.
- Scan runs can be compute-heavy depending on grid size.

## PROCESS-inspired extensions (Windows-native)
SHAMS-FUSION-X keeps the original fast 0-D point-design workflow, and adds optional systems-code features:
- Analytic profiles (`src/profiles/`) with pedestal normalization and derived averages
- Constraint evaluation (`src/constraints/`) and bounded vector solvers (`src/solvers/constraint_solver.py`)
  - Advanced robustness: optional trust-region step cap (`trust_delta`) with explicit `trust_region` / `linesearch` trace events.
- SPARC-oriented engineering hooks (TF/HTS) in `src/engineering/`
- Plant/net-electric closure, neutronics and divertor proxies in `src/physics/`
- Benchmarks + sensitivity + Pareto tools surfaced in the UI Benchmarks tab

All of the above remains pure Python (no WSL / Fortran / PROCESS runtime dependency).

## Continuing in a new chat
To continue development in a new ChatGPT conversation, upload **the latest SHAMS-FUSION-X zip** you are running
and include:
1) The exact error traceback (if any)
2) Which UI tab / action triggered it
3) The input point (or benchmark case name) you used

If everything is working, just upload the zip and tell me the next feature you want.

### Solver robustness: Block-ordered solve

In **Systems Mode**, you can enable **Block-ordered solve (density → power → confinement → exhaust)**. This runs a staged solve before the final coupled solve, which often reduces brittle Jacobian singularities. The solver trace records `block_stage` events for full auditability.


- **TF winding-pack Jop (optional):** Systems Mode includes an expander to compute TF operating current density from required ampere-turns and a simple winding-pack area proxy.
