# SHAMS NiceGUI UI

Desktop/browser UI parallel to the Streamlit app (`ui/app.py`). Primary UI after migration Phase 18.

## Run

**Windows:** double-click `run_ui_nicegui.cmd` (opens a **persistent** terminal and browser).

```powershell
cd SHAMS-0D
run_ui_nicegui.cmd
```

**Linux:**

```bash
cd SHAMS-0D
chmod +x run_ui_nicegui.sh
./run_ui_nicegui.sh
```

**Direct (developers):**

```powershell
cd SHAMS-0D
python -u ui_nicegui/launch.py
```

Open http://127.0.0.1:8080 (auto-fallback to 8081+ if busy).

### Launch troubleshooting

| Issue | Fix |
|-------|-----|
| Window closes instantly | Fixed in `run_ui_nicegui.cmd` — avoid `(text)` inside batch `if` blocks |
| No browser | Set `SHAMS_NICEGUI_SHOW=0` and open URL manually; or check firewall |
| Port in use | Close other NiceGUI/Streamlit instances; or `set SHAMS_NICEGUI_PORT=8090` |

## Architecture

| Module | Role |
|--------|------|
| `launch.py` | Error handling + pause on failure (Windows) |
| `app.py` | Entry, sidebar, deck router, explicit browser open |
| `session.py` | `DesignSession` (typed session state) |
| `evaluate.py` | `ui_evaluate()` → `Evaluator.evaluate()` (L0 choke point) |
| `decks/` | One `render_<deck>()` per deck |
| `components/` | Verdict banner, KPI row, empty state, proposal banner |

## Migration status (Phase 18)

| Deck | Status |
|------|--------|
| Point Designer | **Full parity batch (Phase 19):** Configure overlays + templates, 7 telemetry views, constraints atlas/diff/notebook |
| System Suite | **Complete** — 5-tab workflow, plant/thermal/lifetime overlays, envelope robustness, scenarios & exports |
| Systems Mode | **Complete** — 5-tab workflow, post-solve plant authority, feasibility map heatmap, power-balance diagram, recovery advanced controls, reproduce/diff, guided mode |
| Scan Lab | Cartography + workbench |
| Pareto Lab | Internal + 11 external optimizer decks |
| Trade Study Studio | Setup + 8 advanced decks |
| Reactor Design Forge | Intent + Machine Finder + Capsules |
| Compare | Core compare parity |
| Publication Benchmarks | All 5 tabs |
| Control Room | Orientation, Constitution, Diagnostics, Provenance, **Artifacts**, **Chronicle** |

Streamlit (`run_ui.cmd`) remains available for any expert panels not yet ported.

Orchestrator: `/shams-nicegui-migration`

## Tests

```powershell
cd SHAMS-0D
python -m pytest tests/ -k nicegui -q
python -m pytest tests/test_golden_physics_outputs.py -q
```

## UI law

Same as Streamlit — see `.cursor/rules/shams-nicegui-ui.mdc`. All evaluation through `ui_evaluate()`; never call `hot_ion_point()` directly from NiceGUI code.
