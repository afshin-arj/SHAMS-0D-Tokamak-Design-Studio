# Reviewer Packet

The **Reviewer Packet** is a **one-click**, **deterministic**, **audit-safe** ZIP export intended for
review rooms, publication appendices, and regulatory-style evidence trails.

It is **descriptive only**:
- no ranking
- no optimization
- no recommendations

## Bundle contents (default)

### Core governance docs
- `docs/MODEL_SCOPE_CARD.md`
- `docs/VOCABULARY_LEDGER.md`
- `docs/EXTERNAL_EXPOSURE_GUARDRAILS.md`
- `docs/EXTERNAL_EXPOSURE_CHECKLIST.md`
- `docs/PROCESS_CROSSWALK.md`
- `docs/REVIEWER_PACKET.md` (this file)

### Candidate + derived descriptive artifacts
- `candidate.json`
- `report_pack/` (Forge candidate report: JSON + markdown + CSV)
- `review_trinity/` (Existence Proof → Stress Story → Positioning)
- `attack_simulation/` (hostile review rehearsal scaffold)

### Provenance
- `MANIFEST_PACKET_SHA256.json` (SHA256 + size for every file in the packet)
- optional: `repo/` (repo-level manifests + governance docs)

### Optional contextual additions
- `run_capsule.json` (replay capsule)
- `scan_grounding.json` (cartography grounding)
- `do_not_build_brief.json` (diagnostic brief)

## Determinism guarantee

Packets are built with:
- stable JSON encoding (`sort_keys=True`)
- deterministic ZIP ordering and timestamps

Given the same candidate and inputs, the packet content is reproducible.
