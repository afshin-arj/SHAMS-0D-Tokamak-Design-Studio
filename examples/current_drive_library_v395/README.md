# v395 — Current Drive Library Expansion (Multi-Channel Mix)

This example shows how to enable the v395 multi-channel current-drive library.

## UI path
Point Designer → *Current drive & NI closure*:
- set **CD efficiency model** = `channel_library_v395`
- enable **CD multi-channel library (v395.0)**
- enable **Enable CD actuator mix (v395)**
- set fractions for ECCD/LHCD/NBI/ICRF

## Minimal JSON snippet
```json
{
  "include_current_drive": true,
  "include_cd_library_v395": true,
  "cd_model": "channel_library_v395",
  "cd_mix_enable": true,
  "cd_mix_frac_eccd": 0.4,
  "cd_mix_frac_lhcd": 0.3,
  "cd_mix_frac_nbi": 0.2,
  "cd_mix_frac_icrf": 0.1
}
```

After a Systems solve, open Systems Mode and compute:
**📡 Current drive library (v395) — multi-channel mix bookkeeping (certified)**.
