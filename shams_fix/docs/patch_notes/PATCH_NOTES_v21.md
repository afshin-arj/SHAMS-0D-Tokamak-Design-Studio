# SHAMS–FUSION-X v21 patch notes

## Fixes
- **Streamlit UI import-time crash**: `NameError: _sync_point_designer_from_last_point_inp is not defined`
  - Root cause: the module called `_sync_point_designer_from_last_point_inp()` before the function was defined (top-level execution order).
  - Fix: defer the call until after the function definition so Streamlit reruns can safely sync preset-loaded values into Point Designer widget state.

## Files changed
- `ui/app.py`
