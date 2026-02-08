# PATCH NOTES — v325.0

Author: © 2026 Afshin Arjhangmehr

## Scope

v325.0 upgrades the **🧾 Certified Optimization Orchestrator** to a stricter 3.0 contract:

- Stronger external firewall (mutation detection)
- Explicit objective contracts (objective_contract.v3)
- Evidence-integrated optimizer dossiers

Frozen deterministic truth remains unchanged.

## Changes

### 1) Firewall: Repo Mutation Guard
- The orchestrator now hashes frozen areas **before** running any external kit and re-hashes **after**.
- Guarded paths: `src/`, `constraints/`, `physics/`, `models/`, `profiles/`, `schemas/`.
- Any mutation triggers a **certification failure** and is recorded in `repo_mutation_guard.json`.

### 2) Explicit Objective Contracts (v3)
- Added support for `objective_contract.v3`:
  - `objectives: [{key, sense}]`
  - `selection.ordering` (e.g. `["worst_hard_margin", "objective"]`)
  - optional `selection.scenario_robustness` flag (still deterministic; no Monte Carlo)
- The orchestrator persists the contract as `objective_contract.json` and references it by SHA-256 in the dossier.

### 3) Evidence-Integrated Optimizer Dossier
- Orchestrator now produces `optimizer_dossier.json` which links:
  - kit run directories under `runs/optimizer_kits/`
  - the specific feasible optimizer evidence packs under `runs/optimizer/` used as proposals
  - CCFS verification summary counts (proposed/verified/feasible/pareto)
  - objective contract hash + kit config hash
  - repo mutation guard status

### 4) Deterministic evidence pack attribution
- External kits propagate `orchestrator_job_id` into each feasible optimizer run config.
- The orchestrator only harvests candidates from evidence packs with a matching `orchestrator_job_id`.

## UI

Pareto Lab → **🧾 Certified Optimization Orchestrator** deck:
- updated to 3.0
- emits objective_contract.v3
- adds `optimizer_dossier.json` as a first-class downloadable artifact

## Files of note
- `src/extopt/orchestrator.py`
- `clients/optimizer_kits/run_kit.py`
- `clients/feasible_optimizer_client/feasible_opt.py`
- `ui/certified_opt_orchestrator.py`
