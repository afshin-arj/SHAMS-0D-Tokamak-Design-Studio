# PATCH NOTES — v165 (2026-01-18)

Study Protocol Generator (Design Study Authority)

Adds v165 study protocol generator (journal-ready Methods + protocol hash):
- tools.study_protocol_v165: build_study_protocol() + render_study_protocol_markdown()
- tools.cli_study_protocol_v165
- UI panel: Study Protocol Generator (v165) integrated after v164, before v160
- ui_self_test produces study_protocol_v165.json and study_protocol_v165.md

Safety:
- Reporting-only. No physics or solver logic changes.
