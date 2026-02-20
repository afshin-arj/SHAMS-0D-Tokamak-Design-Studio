# v393 — Irradiation damage → strength coupling

This example enables the v393 authority, which couples the v390 DPA-rate proxy to v389 structural allowables
and produces *derived* degraded margins.

Usage:
- Load `point_enable_v393.json` into Point Designer (or merge into your point JSON)
- Run Systems Solve
- Inspect:
  - Outputs: `*_struct_margin_degraded_v393`, `*_sigma_allow_degraded_MPa_v393`
  - Certifications: `damage_strength_coupling_v393`

Notes:
- This authority does **not** modify upstream truth outputs.
- The degradation model is a conservative, linear screening envelope.
