# Cite-SHAMS handoff pack

**Independence Phase 4.2** — default cite/reproduce unit for new SHAMS feasibility studies.

**Related:** `CITATION.cff`, `docs/LIMITATIONS.md`, `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`, `docs/PROCESS_RETIREMENT_REPORT.md`, `docs/RELEASE_ARCHIVAL_CHECKLIST.md`.

## Purpose

Export **one ZIP** that a paper, lab note, or reviewer can use to cite and reproduce a SHAMS result **without depending on UKAEA PROCESS**:

| Content | Role |
|---------|------|
| `VERSION` | Software version string |
| `provenance.json` | Version + optional `git describe` |
| `point_inputs.json` | PointInputs for re-evaluation |
| `run_artifact.json` + `run_artifact.sha256` | Frozen evaluation record + hash |
| `no_solution_atlas.json` | Present when hard-infeasible |
| `citation.txt` / `citation.bib` | CITATION.cff-derived snippets |
| `release_gate.json` | Scientific release status (**CONDITIONAL**) |
| `HONESTY.md` | PROCESS optional; METHOD-ONLY parity; no blanket retirement |
| `manifest.json` / `MANIFEST_SHA256.txt` | Per-file SHA-256 integrity |

## How to build

### Python API

```python
from pathlib import Path
from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack, write_cite_shams_handoff_pack

pack = build_cite_shams_handoff_pack(run_artifact_dict)
Path("out/cite_pack.zip").write_bytes(pack["zip_bytes"])
# or:
write_cite_shams_handoff_pack(run_artifact_dict, Path("out/cite_pack.zip"))
```

### CLI

```powershell
cd SHAMS-0D
python -m reports.cite_shams_handoff_pack path\to\run_artifact.json -o out\cite_handoff.zip
```

### Studio UI

* **Point Designer** → Export → “Download cite-SHAMS handoff pack”
* **Control Room** → Artifacts → Export & Share → same button

Labels are version-tag-free. PROCESS import remains optional; this pack is SHAMS-native.

## Citation posture

1. Cite SHAMS `VERSION` **and** the run-artifact SHA-256 from the pack.
2. State scientific release status **CONDITIONAL** (until APPROVED evidence exists).
3. If PROCESS is mentioned, declare **METHOD-ONLY** parity unless a lab NUMERIC dossier is attached — never invent MFILE numbers.
4. Do **not** claim “PROCESS retired.” Scoped coverage: `docs/PROCESS_RETIREMENT_REPORT.md`.

## Schema

`shams.cite_shams_handoff_pack.v1` — additive export only; L0 evaluator untouched.

Lock tests: `tests/test_cite_shams_handoff_pack.py`.
