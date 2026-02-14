from __future__ import annotations

from typing import Any, Dict, List


def default_model_registry() -> Dict[str, Any]:
    """Return a transparent list of model options.

    This is SHAMS' PROCESS-inspired analogue to selecting model "switches",
    but kept explicit, explainable, and maturity-tagged.
    
    NOTE: This is a starter registry. As SHAMS adds alternative submodels,
    new options can be appended here without changing existing IDs.
    """

    options = {
        "confinement": [
            {
                "id": "H98_proxy_v1",
                "description": "Transparent H98 proxy computed from internal power balance + scaling placeholder.",
                "maturity": "low",
                "validity": "Exploration proxy; do not treat as predictive.",
            }
        ],
        "bootstrap": [
            {
                "id": "bootstrap_proxy_v1",
                "description": "Simple bootstrap current fraction proxy.",
                "maturity": "low",
                "validity": "Proxy; validate against higher-fidelity tools before decision-grade use.",
            }
        ],
        "economics": [
            {
                "id": "coe_proxy_v1",
                "description": "Soft economics proxy (post-feasibility only).",
                "maturity": "exploratory",
                "validity": "Not for procurement/capex decisions; use for trade-space intuition.",
            }
        ],
    }

    return {"schema_version": "model_registry.v1", "options": options}


def selected_model_set(outputs: Dict[str, Any] | None = None, *, overrides: Dict[str, str] | None = None) -> Dict[str, Any]:
    """Determine which model options were used for this run.

    Today, SHAMS is mostly single-path; this function provides the stable
    interface so future upgrades can add choices without breaking artifacts.
    """
    overrides = overrides or {}
    selected = {
        "confinement": overrides.get("confinement", "H98_proxy_v1"),
        "bootstrap": overrides.get("bootstrap", "bootstrap_proxy_v1"),
        "economics": overrides.get("economics", "coe_proxy_v1"),
    }
    return {"schema_version": "model_set.v1", "selected": selected}
