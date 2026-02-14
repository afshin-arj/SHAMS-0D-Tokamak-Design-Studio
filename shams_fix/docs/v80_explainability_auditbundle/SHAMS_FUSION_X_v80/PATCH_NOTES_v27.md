# SHAMS–FUSION-X v27

## What changed
- Streamlit UI now **auto-runs** `python verification/run_verification.py` when needed (report missing or older than requirements/runner).
- Added a Sidebar expander: **Verification (requirements)** with:
  - Auto-run toggle
  - Run now button
  - Optional stdout/stderr logs

## Files touched
- `ui/app.py`
- Added `PATCH_NOTES_v27.md`
