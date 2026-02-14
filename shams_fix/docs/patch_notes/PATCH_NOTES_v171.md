# PATCH NOTES — v171 (2026-01-18)

UI bugfix release (results persistence + non-empty More tab)

Fixes:
- Point Designer results no longer disappear after downloads / reruns:
  - caches last outputs/artifact to st.session_state['pd_last_outputs'/'pd_last_artifact']
  - Point Designer always renders cached results section (v89.1 helper).
- "More" tab expanders are now populated with safe, always-available content:
  - Studies expander hosts v165–v170 study tools
  - other expanders show non-empty guidance so they never appear blank.

Safety:
- UI-layer only; no physics or solver logic changes.
