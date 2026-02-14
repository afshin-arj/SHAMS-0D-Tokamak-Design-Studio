# PATCH NOTES v175.4.1

- Fix: Panel Availability Map (PAM) 'Open a panel here' runtime crash (NameError: fn not defined) caused by indentation regression.
- Hardened: PAM now uses the shared `_resolve_panel_function()` resolver and renders the selected panel only when callable.

