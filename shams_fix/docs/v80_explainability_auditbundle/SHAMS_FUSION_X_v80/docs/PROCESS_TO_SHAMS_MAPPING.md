# PROCESS → SHAMS clean mapping checklist (highest-value)

This checklist extracts the **highest-leverage** PROCESS documentation topics and maps them onto SHAMS modules.

Principle: **learn the architecture lessons**, keep SHAMS **Python-native, artifact-driven, constraint-first**, and do **not** copy PROCESS implementation.


## Checklist

### Cost models

- PROCESS doc: `documentation/cost-models/cost-models.md`

- SHAMS module(s): src/economics/cost.py, src/economics/lifecycle.py

- SHAMS implementation actions:

  - Keep proxy coefficients externalized (JSON) and versioned in artifacts.

  - Maintain explicit CAPEX/OPEX/replacements schedule (no hidden curves).

  - Expose scenario-level overrides (discount rate, availability, financing).



### Input format & variable discipline

- PROCESS doc: `documentation/io/input-guide.md`

- SHAMS module(s): src/models/inputs.py, src/shams_io/schema.py, src/shams_io/migrate.py

- SHAMS implementation actions:

  - Treat inputs as a stable contract; add fields with defaults and schema migration.

  - Maintain a variable registry doc for UI + reports; avoid ad-hoc keys.

  - Keep backwards compatibility by normalizing artifacts.



### Python utilities / workflow

- PROCESS doc: `documentation/io/utilities.md`

- SHAMS module(s): tools/, src/studies/, src/shams_io/

- SHAMS implementation actions:

  - Mirror PROCESS "utilities" concept with SHAMS tools that operate on artifacts: indexing, plotting, comparisons.

  - Keep everything Windows-safe and headless-friendly.



### Radial build / machine build closure

- PROCESS doc: `documentation/eng-models/machine-build.md`

- SHAMS module(s): src/engineering/radial_stack.py, src/physics/neutronics.py

- SHAMS implementation actions:

  - Ensure radial build is a first-class closure constraint (like PROCESS build).

  - Record each layer thickness, allocated margins, and dominant closure driver in artifacts.



### TF coil superconducting

- PROCESS doc: `documentation/eng-models/tf-coil-superconducting.md`

- SHAMS module(s): src/engineering/tf_coil.py, src/engineering/coil_thermal.py

- SHAMS implementation actions:

  - Separate limits: stress, Jc(B,T), temperature margin, quench margin.

  - Make peak field location explicit, and include an audit table in reports.



### TF coil overview (general)

- PROCESS doc: `documentation/eng-models/tf-coil.md`

- SHAMS module(s): src/engineering/tf_coil.py

- SHAMS implementation actions:

  - Use this to ensure naming parity and completeness of TF subsystem outputs (but keep SHAMS proxy math).



### Central solenoid

- PROCESS doc: `documentation/eng-models/central-solenoid.md`

- SHAMS module(s): src/engineering/pf_cs.py

- SHAMS implementation actions:

  - Treat flux swing, stress, and current density as explicit constraints.

  - Record pulse/inductive scenario assumptions clearly in artifacts.



### PF coils

- PROCESS doc: `documentation/eng-models/pf-coil.md`

- SHAMS module(s): src/engineering/pf_system.py

- SHAMS implementation actions:

  - Keep PF sizing proxy but add clear constraints: volt-seconds, coil space, stored energy proxy.



### Divertor

- PROCESS doc: `documentation/eng-models/divertor.md`

- SHAMS module(s): src/physics/divertor.py, src/engineering/thermal_hydraulics.py

- SHAMS implementation actions:

  - Elevate heat exhaust feasibility: q_div limit, detachment margin proxy, coolant limits.

  - Ensure 'dominant blocker' reporting highlights divertor when it binds.



### First wall / blanket

- PROCESS doc: `documentation/eng-models/fw-blanket.md`

- SHAMS module(s): src/physics/neutronics.py, src/engineering/radial_stack.py

- SHAMS implementation actions:

  - Expose blanket thickness ↔ TBR proxy ↔ shielding needs.

  - Treat replacement schedule as economics driver (integrate with lifecycle).



### Shield

- PROCESS doc: `documentation/eng-models/shield.md`

- SHAMS module(s): src/physics/neutronics.py

- SHAMS implementation actions:

  - Maintain transparent neutron attenuation proxy and dpa limit constraints.



### Power requirements

- PROCESS doc: `documentation/eng-models/power-requirements.md`

- SHAMS module(s): src/physics/plant.py

- SHAMS implementation actions:

  - Keep full recirc closure: aux, cryo, pumps, CD, balance-of-plant.

  - Record power breakdown and Sankey diagram provenance.



### Power conversion & heat rejection

- PROCESS doc: `documentation/eng-models/power-conversion-and-heat-dissipation-systems.md`

- SHAMS module(s): src/physics/plant.py, src/engineering/thermal_hydraulics.py

- SHAMS implementation actions:

  - Add explicit efficiency assumptions and coolant ΔT constraints.

  - Expose assumptions in reports for decision-grade review.



### Plant availability

- PROCESS doc: `documentation/eng-models/plant-availability.md`

- SHAMS module(s): src/analysis/availability.py

- SHAMS implementation actions:

  - Make availability a scenario knob; connect to OPEX and LCOE.

  - Record drivers: replacement interval, maintenance time, RAMI proxy.



### Plasma confinement models

- PROCESS doc: `documentation/physics-models/plasma_confinement.md`

- SHAMS module(s): src/physics/hot_ion.py, src/physics/profiles.py

- SHAMS implementation actions:

  - Keep confinement proxy transparent; record which scaling is used.

  - Tie calibration registry to confinement factor with uncertainty.



### Plasma beta limits

- PROCESS doc: `documentation/physics-models/plasma_beta/plasma_beta.md`

- SHAMS module(s): src/constraints/constraints.py, src/analysis/mhd_risk.py

- SHAMS implementation actions:

  - Keep βN, Troyon, and stability margins explicit and constraint-first.



### Plasma geometry

- PROCESS doc: `documentation/physics-models/plasma_geometry.md`

- SHAMS module(s): src/models/inputs.py, src/physics/profiles.py

- SHAMS implementation actions:

  - Ensure consistent geometry conventions (R0,a,kappa,delta) and derived values are recorded.



### Pulsed plant

- PROCESS doc: `documentation/physics-models/pulsed-plant.md`

- SHAMS module(s): src/physics/plant.py, src/analysis/availability.py

- SHAMS implementation actions:

  - Add scenario switching between steady-state vs pulsed.

  - Expose cycle times and their effect on availability and economics.



### Heating & CD (NBI)

- PROCESS doc: `documentation/eng-models/heating_and_current_drive/NBI/nbi_overview.md`

- SHAMS module(s): src/physics/plant.py (power), src/physics/profiles.py (CD proxy)

- SHAMS implementation actions:

  - Keep CD power requirements explicit; track wall-plug efficiency assumptions.



### Heating & CD (EC)

- PROCESS doc: `documentation/eng-models/heating_and_current_drive/RF/ec_overview.md`

- SHAMS module(s): src/physics/plant.py, src/physics/profiles.py

- SHAMS implementation actions:

  - Same as above; treat launcher limits as optional enriched constraint later.



## Notes
- The SHAMS run artifact should capture: **which model variant was used**, **all calibration factors**, **scenario assumptions**, and **dominant blockers** for each case.
