# PATCH NOTES — v168 (2026-01-18)

Citation-Grade Study ID + BibTeX

Adds v168 citation bundle generator:
- tools.citation_v168: build_citation_bundle() -> Study ID + CITATION.cff + BibTeX + reference markdown
- tools.cli_citation_v168
- UI panel integrated after v167, before v160
- ui_self_test produces citation_bundle_v168.json + CITATION.cff + study_citation_v168.bib + study_reference_v168.md

Safety:
- Packaging/metadata only; no physics or solver logic changes.
