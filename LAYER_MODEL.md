# SHAMS Layer Model (v120)

## Layer rules
- Layers may depend on lower layers, never vice versa.
- Layers may read artifacts from lower layers and write new artifacts.
- Layers must never mutate or overwrite lower-layer outputs.

## Current layer mapping (as of v120)
- **L0**: Physics evaluator + constraints + run artifact generation
- **L1**: Authority Pack (v119), citation & governance docs (v120)
- **L2**: Design Handoff Pack (v116)
- **L3**: Mission contexts (planned; schema-first)
- **L4**: Explainability narratives (planned; schema-first)

## UI
A layer is “UI-accessible” if it registers a panel entry via the layer registry.

