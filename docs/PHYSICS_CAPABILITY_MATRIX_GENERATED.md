# Physics Capability Matrix (Generated)

**SHAMS version:** `v229.0_RWMFeasibleOptimizerClientBundle`
**Generated:** `2026-02-01T14:01:13Z`

This file is generated from the frozen internal declarations (authority contracts + model registry).
It is read-only in the UI; edit source declarations, then regenerate.

## Generation fingerprints
```json
{
  "authority_contracts_hash_sha256": "2daac33ba2626f8ea5bdd76f3d9605e284518ac93fe277db9c445b1be183ae8e",
  "generated_utc": "2026-02-01T14:01:13Z",
  "model_registry_hash_sha256": "1265625420a438aea4a21c63d734d183e564bd430e648ab6396e4258b64104c3",
  "shams_version": "v229.0_RWMFeasibleOptimizerClientBundle"
}
```

## Authority contract coverage
| Tier | Count |
| --- | --- |
| authoritative | 2 |
| proxy | 6 |
| semi-authoritative | 5 |

### Contract list
| Subsystem | Tier | Validity domain | Notes (truncated) |
| --- | --- | --- | --- |
| control.rwm | proxy | RWM screening proxy between no-wall and ideal-wall beta limits; uses wall-time constant tau_w and bounded parametric scalings in (kappa, delta, q95, li). | PROCESS-class screening: deterministic, no MHD simulation; intended for feasibil |
| current.bootstrap | semi-authoritative | Bootstrap fraction estimated from pressure-gradient proxies; optional Sauter-inspired mode with collisionality proxies. | Not a full neoclassical solver; output tagged with mode and validity flags. |
| current.drive | proxy | Actuator-scaled CD efficiency trends (NBI/ECCD/LHCD) with deterministic coupling into recirculating power. | No ray tracing or deposition physics. |
| engineering.magnets | semi-authoritative | Technology-aware TF proxies (Bpeak, stress, HTS critical-surface margin; copper I^2R loss coupling). | Monotone, bounded proxies; not a detailed FEM. |
| engineering.radial_build | semi-authoritative | PROCESS-inspired explicit inboard stack closure (sum of thicknesses) with signed margin; no CAD. | Constraint enforcement is opt-in to preserve legacy behavior. |
| exhaust.divertor | semi-authoritative | Two-point-style SOL/divertor proxy with optional Eich14 lambda_q; unified exhaust API ensures single-source outputs. | Not a SOL code replacement; used for feasibility screens and dominant-mechanism  |
| fuel_cycle.tritium | proxy | T burn and inventory proxies from fusion power; processing efficiency and reserve days. | Used for feasibility/risk screening only. |
| neutronics.proxy | proxy | Neutron wall load and TBR proxies; stack attenuation and nuclear heating shares are parametric. | Not a Monte-Carlo neutronics replacement. |
| plant.availability | proxy | Scheduled outage from replacement intervals (dpa/erosion proxies) + forced trips. | Not a plant operations simulator. |
| plasma.confinement | semi-authoritative | H-mode tokamak confinement scalings; 0-D global IPB98(H98) with explicit H-factor; L-mode handled via ITER89P proxy when enabled. | No transport or time evolution; intended for feasibility screening and trade-spa |
| plasma.profiles | proxy | Analytic 1/2-D profiles with deterministic pedestal scaffold; bounded and monotone by construction. | Profile shape is a scaffold for stored energy, bootstrap sensitivity, and radiat |
| radiation.core | authoritative | Line-radiation via Lz(T) cooling curves; external DB ingestion with SHA256 provenance; OFF by default. | Authority drops to proxy if DB missing and fallback curve used. |
| scan.cartography | authoritative | Deterministic mapping over frozen Point Designer evaluator; no optimization. | Cartography semantics are frozen; new derived layers must be purely post-process |

## Model registry snapshot
| Model key | Label | Authority | Validity |
| --- | --- | --- | --- |
| (unavailable) |  |  |  |

## Interpretation rules
- **Proxy**: screening-only; do not treat as licensing-grade.
- **Semi-authoritative**: regression / limited validation; requires reviewer attention.
- **Authoritative**: sourced from curated DB / validated closure within stated validity domain.

