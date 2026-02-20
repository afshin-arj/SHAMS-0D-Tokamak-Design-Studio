# Neutronics & Activation Authority v390 example

This folder provides a minimal example input enabling the **v390 Neutronics & Activation Authority 3.0**.

Run:
- Open SHAMS UI
- Load `neutronics_activation_demo.json` in **🧭 Point Designer**
- Enable **☢️ Neutronics & Activation Authority — v390.0.0**
- Evaluate point
- Inspect outputs and **Systems Mode → certifications → neutronics_activation_v390**

Notes:
- This is a deterministic, algebraic **screening** envelope (no MC transport, no activation codes).
- The shielding margin uses an **effective thickness** (blanket + shield + 0.5×VV) vs a regime-binned requirement.
- First-wall DPA-lite is driven by neutron wall load (shielding does not mitigate FW damage in this envelope).
