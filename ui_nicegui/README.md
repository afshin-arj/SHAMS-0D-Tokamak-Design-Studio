# SHAMS NiceGUI UI

Desktop/browser UI parallel to the Streamlit app (`ui/app.py`). Primary UI after NiceGUI migration.

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

## Migration status

| Deck | Status |
|------|--------|
| Point Designer | **Full parity:** Configure overlays + templates, 7 telemetry views, constraints atlas/diff/notebook |
| System Suite | **Complete** — 5-tab workflow, phase cockpit, UQ absolute bounds, campaign preview, parity suite ID, mode contracts |
| Systems Mode | **Complete** — 5-tab workflow, post-solve plant authority, feasibility map heatmap, power-balance diagram, recovery advanced controls, reproduce/diff, guided mode |
| Scan Lab | **Complete** — 4-tab workflow, deep landscape maps, intent-split atlas, full interpret suite, mode contract |
| Pareto Lab | **Complete** — 5-tab workflow, explore/interpret/audit, publication pack, Scan Lab & Systems Mode handoffs, 11 external decks |
| Trade Study Studio | **Complete** — 5-tab workflow, frontier atlas, robust certification, surrogate, optimizer kits |
| Reactor Design Forge | **Complete** — 5-tab workflow, 67 expert instruments, staged run, collaboration sessions |
| Compare | **Complete** — 5-tab workflow (Load · Performance · Constraints · Inputs & Structure · Export) |
| Publication Benchmarks | **Complete** — 5-tab workflow (Atlas · Pack · Cross-Code · Governance · Evidence) |
| Control Room | **Complete** — 6-section workflow (Orient · Constitution · Provenance · Artifacts · Diagnostics · Chronicle) |

Streamlit (`run_ui.cmd`) redirects **Scan Lab**, **System Suite**, **Pareto Lab**, **Trade Study Studio**, **Reactor Design Forge**, **Compare**, **Publication Benchmarks**, and **Control Room** to NiceGUI. The only deliberate Streamlit-only path is the archived legacy nested grid scan (Ti/H98/a/Q/g_conf) — noted in Scan Lab orientation.

User-facing labels use plain language (no internal `v###` / Batch / Phase tags). Legacy session values are normalized via `ui_nicegui/lib/display_labels.py`. Re-run `python tools/clean_user_version_tags.py --write` after adding new version-tagged UI strings.

Orchestrator: `/shams-nicegui-migration`

## Tests

```powershell
cd SHAMS-0D
python -m pytest tests/ -k nicegui -q
python -m pytest tests/test_golden_physics_outputs.py -q
```

## UI law

Same as Streamlit — see `.cursor/rules/shams-nicegui-ui.mdc`. All evaluation through `ui_evaluate()`; never call `hot_ion_point()` directly from NiceGUI code.
