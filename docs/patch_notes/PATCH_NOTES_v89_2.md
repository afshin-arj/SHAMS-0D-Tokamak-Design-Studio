# PATCH NOTES — v89.2 (2026-01-08)

Hotfix: Point Designer persistence, More tab fallback content, radial PNG layout.

Fixed / improved:
- Point Designer: results no longer vanish after downloading PNG/JSON (session_state cache shown unconditionally).
- Added Clear cached result button + in-UI preview of cached radial build PNG.
- More tab: fallback diagnostics so 'More' never shows blank expanders.
- Radial build PNG: legend/xlabel layout rewritten using fig.legend + bottom margin to prevent caption/legend overlap.

Unchanged:
- Physics
- Solvers
- Defaults
