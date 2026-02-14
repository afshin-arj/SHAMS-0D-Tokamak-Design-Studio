# Reference curves and trend expectations (qualitative)

This document records *qualitative* expectations used by SHAMS trend tests.

SHAMS is not intended to numerically reproduce UKAEA PROCESS outputs, but it is intended to
behave like a coherent systems model: as key knobs change, *trends* should match physical intuition.

Examples (in the regime where the point model assumptions remain valid):
- Increasing toroidal field **Bt** (holding geometry and profiles fixed) should generally increase fusion power.
- Increasing major radius **R0** at fixed Bt and aspect ratio typically increases volume and Pfus, but may change engineering margins.
- Increasing radiated power fraction should reduce divertor heat flux proxy (q_div) while reducing net power.

These expectations are encoded in `tests/test_trends_reference.py` as simple sign checks with generous tolerances.
