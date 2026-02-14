# Stage 3 — Robustness under uncertainty

Upgrades Monte-Carlo robustness to track additional metrics and threshold probabilities.

Key API:
- `analysis.uncertainty.robustness_summary(base, perturb, metrics=..., thresholds=...)`

Thresholds format: `{ "P_net_MWe": (">=", 500.0), "LCOE_proxy_USD_per_MWh": ("<=", 120.0) }`
