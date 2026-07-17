# SHAMS Champion Cases

**Campaign:** Independence Phase 3.3 (`docs/PROCESS_SURPASS_ROADMAP.md`)  
**SHAMS version:** see repository root `VERSION`  
**Status:** Publication-oriented **templates** — SHAMS-only feasibility studies labs can copy.  
**Does not** invent PROCESS MFILE numbers. **Does not** claim PROCESS retirement. Device names are **class/like** inspiration, not measured device parity.

---

## What these cases show

| Case ID | Family | Intent | Expected verdict | Why it matters |
|---------|--------|--------|------------------|----------------|
| `champion.sparc_class.burning_plasma` | SPARC-class | Research | Hard-feasible | Compact HTS burning-plasma template (q95-gated Research policy) |
| `champion.step_like.st_baseline` | STEP-like | Reactor | NO-SOLUTION | ST baseline under Reactor hard set — mechanism atlas (typically PROFILE / q95) |
| `champion.reactor_conservative.iter_like` | reactor-conservative | Research | Hard-feasible | Large LTS-class conservative template |
| `champion.sparc_class.overdriven_nosolution` | SPARC-class | Research | NO-SOLUTION | Deliberate overdriven variant — atlas story within the same family |

Feasibility uses the **same Design Intent policy as Point Designer**:

- **Research:** only `q95` is hard-blocking; engineering limits are diagnostic; `TBR` ignored  
- **Reactor:** full reactor hard set (`q95`, `q_div`, `P_SOL/R`, `sigma_vm`, `B_peak`, `HTS margin`, `TBR`, `NWL`)  
- Non-finite constraint values are **omitted** (not evaluated — do not gate)

NO-SOLUTION rows carry `no_solution_atlas.v1` on the run artifact (dominant mechanism + constraint).

---

## How to reproduce

From the `SHAMS-0D/` repo root:

```bash
python benchmarks/champions/run_champions.py
python benchmarks/champions/run_champions.py --outdir benchmarks/champions/out
```

Outputs:

- `benchmarks/champions/out/summary.json` — pack summary + per-case citation hashes  
- `benchmarks/champions/out/artifacts/*.json` — full run artifacts  

Definitions live in `benchmarks/champions/cases.json`.  
Python API: `src/studies/champion_cases.py` (`run_all_champions`, `write_champion_pack`).

Lock tests:

```bash
python -m pytest tests/test_champion_cases.py -v
```

---

## How to cite

1. Record the repository `VERSION` string.  
2. Record each case `citation_sha256` from `summary.json` (or the pack `pack_sha256`).  
3. Prefer attaching the case artifact JSON (SHA-256 of the file is fine for archival).  

Example citation sentence:

> Feasibility evaluated with SHAMS `VERSION` \<vX.Y.Z\>; champion case \<case_id\> citation SHA-256 \<hash\> (Design Intent \<Research|Reactor\>).

---

## Honest limitations

- **CONDITIONAL** scientific release status — see `docs/LIMITATIONS.md` and the Phase 1.4 readiness report.  
- Engineering / plant / cost **authority overlays** are proxies when enabled; champion defaults use frozen L0 + governance constraints under Design Intent, not a claim of full DEMO plant closure.  
- Reference machines are **qualitative / literature-geometry** seeds (`src/models/reference_machines.py`) — not SPARC/STEP/ITER measured operating points.  
- PROCESS numeric parity remains **METHOD-ONLY** until a lab lands a real MFILE dossier (`benchmarks/parity/`).  
- Do **not** treat Research-intent hard-feasible as Reactor-intent plant readiness.

---

## Related docs

| Doc | Role |
|-----|------|
| `PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` | IN.DAT → Case / MFILE → artifact |
| `PROCESS_SURPASS_ROADMAP.md` | Independence campaign |
| `LIMITATIONS.md` | What SHAMS does not claim |
| `REFERENCE_STUDY_GALLERY.md` | Communication anchors |

UI: Control Room → Constitution → Docs Library → `CHAMPION_CASES.md`.
