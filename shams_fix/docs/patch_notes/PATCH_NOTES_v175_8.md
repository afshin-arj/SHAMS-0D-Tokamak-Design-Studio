# PATCH NOTES — v175.8

## Point Designer: PNG export hygiene (fix mixed captions)

### What was happening
Some users reported the **downloaded radial build PNG** occasionally showing **overlapping / mixed captions** (legend + axis-label collisions). This can happen when matplotlib computes text metrics slightly differently across platforms/backends.

### Fix
- The radial build plot now uses **deterministic legend placement below the axis** and reserves extra bottom margin.
- The export intentionally avoids `bbox_inches="tight"` for this figure, which can reflow elements unpredictably.
- Legend labels are de-duplicated defensively.

### Files changed
- `src/shams_io/plotting.py`
