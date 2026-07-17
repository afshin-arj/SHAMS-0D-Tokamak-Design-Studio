# SHAMS independence exit evidence (Phase 4.3)

**Schema:** `shams.independence_exit_evidence.v1`  **SHAMS VERSION:** `v418.1.0`  **Report SHA-256:** `b626d0f7b062c833c83f00f40b87438e96a366fb24a2b99d99334ff4ff56ba64`

## Stance

PROCESS remains available as an optional proposer / legacy reproduce path. SHAMS is the feasibility authority for admissible designs, NO-SOLUTION attribution, and citeable VERSION + artifact hashes. **Blanket PROCESS-retirement claim?** **NO**.

## Verdict

- Phase 4 engineering complete (shipped gates): **True**
- Phase 4 full exit complete: **False**
- Scientific release status: **CONDITIONAL**
- Blanket PROCESS retired: **False**

In-repo independence engineering for Phase 4.3 is evidence-backed (citation unit, scoped retirement report, migration, champions, parity contribution channel, CCFS, atlas). Full Phase-4 *exit* (new studies default to citing SHAMS in the wild) remains open: community adoption and APPROVED DOI are EXTERNAL. Do not claim PROCESS retired.

## Checklist

| Status | Item | Evidence class |
|--------|------|----------------|
| `DONE` | Cite-SHAMS citation unit shipped (`cite_shams_handoff_pack`) | shipped |
| `DONE` | Scoped PROCESS retirement evidence report (`scoped_retirement_report`) | shipped |
| `DONE` | PROCESS → SHAMS migration path live (`migration_guide`) | shipped |
| `DONE` | Champion feasibility templates (`champion_templates`) | shipped |
| `DONE` | Parity contribution channel open (`parity_contribution_channel`) | shipped |
| `DONE` | CCFS propose-only firewall (`ccfs_firewall`) | shipped |
| `DONE` | NO-SOLUTION atlas on infeasible artifacts (`no_solution_atlas`) | shipped |
| `CONDITIONAL` | Scientific release gate (CONDITIONAL) (`scientific_release_conditional`) | conditional |
| `EXTERNAL` | APPROVED release + Zenodo DOI (`approved_zenodo_doi`) | external |
| `EXTERNAL` | Community adoption (new studies cite SHAMS by default) (`community_adoption`) | external |

Counts: DONE=7, CONDITIONAL=1, PENDING=0, EXTERNAL=2.

## Item detail

### Cite-SHAMS citation unit shipped — `DONE`

New studies can export VERSION + artifact SHA-256 packs without PROCESS.

Anchors:
- `src/reports/cite_shams_handoff_pack.py` (yes; sha256=`c035c185f96a86b0b1ab0dfca65bbc91737108f8288818083f1eaae75d11a229`)
- `docs/CITE_SHAMS_HANDOFF.md` (yes; sha256=`a04b61f58dfc6def07d0aa55b0f5c8cceb9fa6ff1aaa9a81ac18b48636c4521b`)
- `tests/test_cite_shams_handoff_pack.py` (yes; sha256=`d4987f76f9e28aa567658c9a90ea2d142cafdde689a7a0c78fd7bb23f9eea092`)

### Scoped PROCESS retirement evidence report — `DONE`

Domain coverage is evidence-backed; blanket retirement is refused.

Anchors:
- `src/reports/process_retirement_report.py` (yes; sha256=`8417360ae2ac12b96525606e18a75e0fcbb62e347a3108f1ba3391d39732cd79`)
- `docs/PROCESS_RETIREMENT_REPORT.md` (yes; sha256=`0c404057953da0f2cc15b41c26f15b22c84c5b9b165ddc6e4d8bad0a8cd9f302`)
- `docs/validation/reports/process_retirement_report.json` (yes; sha256=`7c3e5a1c895de8fc16afd67917585c2560daec623262970c914e4bcb5742487b`)
- `tests/test_process_retirement_report.py` (yes; sha256=`d0205a25e7340b61da28ef731ad026bc7961705cf9c476a206083f7381c055c0`)

### PROCESS → SHAMS migration path live — `DONE`

Labs can map IN.DAT/MFILE workflows onto Cases and artifacts.

Anchors:
- `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` (yes; sha256=`64db3c508e6edaefaa5c3d26d0debdec2c301ce33fbaa9b264143e8bebaa2287`)
- `tests/test_process_migration_guide.py` (yes; sha256=`0339e508d61ea5cc68bb696e235922db8b7e1322506577e5088d5ce47169dc21`)

### Champion feasibility templates — `DONE`

SHAMS-only reproducible studies with citation hashes and NO-SOLUTION stories.

Anchors:
- `docs/CHAMPION_CASES.md` (yes; sha256=`013fd2b4cd6136aa52601dfea6d13d640d769ad769313a736ed91b93b98ac68d`)
- `benchmarks/champions/cases.json` (yes; sha256=`e1d5dfc8e148e59345a7221a4e608ec3c419445df350a97959658c8183ca43aa`)
- `src/studies/champion_cases.py` (yes; sha256=`5881d0bb58a539ef921fde6e780a3c3347246946374c6763e0557dab36c2821c`)
- `tests/test_champion_cases.py` (yes; sha256=`6e78655e7e5154c202f1bd3631f280e21b891ffcaae55c8e18f8a58a08bd2abf`)

### Parity contribution channel open — `DONE`

Labs can submit licensed PROCESS refs and receive hashed SHAMS delta dossiers.

Anchors:
- `docs/PARITY_CONTRIBUTION.md` (yes; sha256=`b5723afab63fffe0f2d498cf3fa5d320389529619e146d6242d2c5217a0c3e69`)
- `src/parity_harness/contribution.py` (yes; sha256=`a867f30149a8a20a71368858ac48c31acad872a04fda5cabfd1aef8dd3a7598c`)
- `benchmarks/parity/contributions/submission_template.json` (yes; sha256=`fa769802926d1aa89b5f1915c7aa0a7989b22a4b669dfbc5f92ec25140b0fe7c`)
- `tests/test_parity_contribution_and_exit_evidence.py` (yes; sha256=`dfb7cb94a0f66db7ffde585f691ed55b41055064906b15198c5eced26a48468d`)

### CCFS propose-only firewall — `DONE`

Optimizers (including PROCESS) propose inputs only; SHAMS re-certifies.

Anchors:
- `src/extopt/certified_solve.py` (yes; sha256=`5eb991e4df4dfc51b1f73faf71dbaa4b4c2028bb58709a3b3483da97ceea1b42`)
- `tests/test_ccfs_verified_hard_gate.py` (yes; sha256=`cba5a6511ad71d66ec8cd12976b9b65768ddbaac55745c355b47d7aa7e8c507e`)

### NO-SOLUTION atlas on infeasible artifacts — `DONE`

Infeasibility is attributed, not negotiated away.

Anchors:
- `src/diagnostics/no_solution_atlas.py` (yes; sha256=`adcb9b465430e86038c872261b7e2bd62131dd789d5bc44e959c48258a1a17d1`)
- `tests/test_no_solution_atlas.py` (yes; sha256=`d8c9c22c446d0973b227eb6629abc2cca7a3f7298a0b4d2cd39972d78c95c861`)

### Scientific release gate (CONDITIONAL) — `CONDITIONAL`

Community-facing release is CONDITIONAL with documented limitations — not APPROVED.

*Note:* Release remains CONDITIONAL — not APPROVED.

Anchors:
- `docs/validation/reports/scientific_release_readiness_20260716.md` (yes; sha256=`20e2b9a4d0f1b43578999e5ea4665fe9839c265063a9f046af30ffebc8df8e36`)
- `docs/LIMITATIONS.md` (yes; sha256=`4708925ed7a7594c5005e216ec1a84bb64b1869148c411fb822ad9b304f18dd1`)
- `tests/test_scientific_release_gate.py` (yes; sha256=`1697bf79f56e786478d33033c4255c881eea597dcdadd32868dda2648db241cf`)

### APPROVED release + Zenodo DOI — `EXTERNAL`

Packaging exists; DOI mint and APPROVED verdict require external archival evidence.

*Note:* Packaging/checklist anchors present; adoption/DOI still EXTERNAL.

Anchors:
- `docs/RELEASE_ARCHIVAL_CHECKLIST.md` (yes; sha256=`368979043f36c1fd9b6d474069c3cff348fedf9e7f8143c101a1711b316e80eb`)
- `.zenodo.json` (yes; sha256=`330e0442ba7e39d97543856b90b53975a43cb439fe18ec4e6d7f9eab0b3b7f7e`)
- `CITATION.cff` (yes; sha256=`cc807fe2f4a90ae26babb0bed800a542f12adc2472ad0c157cb8746f29624284`)

### Community adoption (new studies cite SHAMS by default) — `EXTERNAL`

Whether labs actually start new studies in SHAMS is EXTERNAL evidence — shipping code cannot claim adoption.

*Note:* Requires outside-world evidence; cannot be marked DONE by code.

## Honesty

This report records engineering evidence only. EXTERNAL checklist items cannot be marked DONE by regenerating this artifact.

- `process_retired_claimed`: false
- `community_adoption_claimed`: false
- `approved_doi_claimed`: false
- `invented_mfile`: false

## Related

- `docs/PARITY_CONTRIBUTION.md` — lab contribution process
- `docs/PROCESS_RETIREMENT_REPORT.md` — scoped coverage
- `docs/CITE_SHAMS_HANDOFF.md` — citation pack
- `docs/PROCESS_SURPASS_ROADMAP.md` — campaign roadmap
