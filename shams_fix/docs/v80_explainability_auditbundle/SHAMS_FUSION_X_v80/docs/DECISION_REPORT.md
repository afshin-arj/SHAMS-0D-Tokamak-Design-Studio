# Decision-grade PDF front page contract

Page 0 must include:
- Feasibility verdict (hard/soft constraints with margins)
- Dominant blockers (top failing constraints)
- Recommended knob moves (heuristic or sensitivity-based)
- Robustness (P(feasible) when UQ present)
- Scenario snapshot (when present)
- Verification summary + changelog excerpt
- Maturity/validity dependence flags (TRL/envelope)

This contract is implemented in `src/shams_io/plotting.py::plot_summary_pdf`.
