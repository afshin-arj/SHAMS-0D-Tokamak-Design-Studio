# v388.0.0 — Cost Authority 3.0 (Industrial Depth) examples

## Files

- `industrial_cost_demo.json`
  - Minimal Point inputs that enable the v388 industrial-depth cost authority.
  - Note: You must also set `include_economics: true` (the global economics overlay toggle), otherwise `cost_proxies()` is not executed.

## How to run

1. Launch the UI (`run_ui.cmd` / `run_ui.sh`).
2. Open **Point Designer** → load JSON → select `industrial_cost_demo.json`.
3. Run **Point Evaluate**.
4. Inspect outputs:
   - `CAPEX_industrial_v388_MUSD`
   - `OPEX_industrial_v388_MUSD_per_y`
   - `LCOE_lite_v388_USD_per_MWh`
5. In **Systems Mode** → Run Systems Solve, then open:
   - **🏭 Cost authority — industrial depth (certified)**

