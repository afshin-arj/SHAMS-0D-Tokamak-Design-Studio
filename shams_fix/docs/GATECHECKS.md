# SHAMS Gatechecks (Local)

Author: © 2026 Afshin Arjhangmehr

Run from the repository root:

## 1) Bytecode sanity

- `python -m compileall -q .`

## 2) Test suite

- `pytest -q`

## 3) UI smoke

- `streamlit run ui/app.py`

## Hygiene rules (must be absent in releases)

- `__pycache__/`
- `.pytest_cache/`
- `gspulse_ui/`
- `run_st*` launchers

Only minimal launchers are allowed:

- `run_ui.cmd`
- `run_ui.sh`
