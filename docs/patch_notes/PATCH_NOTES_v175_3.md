# PATCH NOTES v175.3

- Fix: Panel Availability Map focus renderer now resolves panel functions by importing/searching across ui.* modules (robust, cached).
- Fix: 0-D Physics Model panel now shows full model documentation (replaced placeholder text).
- Safety: Resolver uses cache to avoid repeated module walks.
