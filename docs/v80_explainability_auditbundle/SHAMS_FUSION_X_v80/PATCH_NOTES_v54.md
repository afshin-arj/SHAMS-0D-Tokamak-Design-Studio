# PATCH_NOTES_v54 — Guided Non-Feasibility Mode (UI)

Adds a new Streamlit tab: **Non-Feasibility Guide**.

- UI-only (no physics changes)
- Displays `nonfeasibility_certificate` (or reconstructs it from hard-failed constraints)
- Lets the user apply transparent knob adjustments, re-evaluate, and export a follow-up `case_deck.v1` plus `scenario_delta.json`.
