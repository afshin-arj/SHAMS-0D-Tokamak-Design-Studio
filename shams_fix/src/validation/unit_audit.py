from __future__ import annotations

from typing import Any, Dict, List


def _num(x: Any) -> float | None:
    try:
        return float(x)
    except Exception:
        return None


def run_unit_audit(outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight, dependency-free sanity + units audit.

    SHAMS does not currently carry a full unit system; this audit is a
    verification *proxy* that catches common regressions (negative powers,
    NaNs, impossible fractions, etc.). It is designed to be CI-gatable and
    artifact-embedded.
    """

    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    # Required numeric KPIs should be finite (plant-level KPIs may be optional)
    required = ["H98", "Q_DT_eqv", "Pfus_DT_adj_MW", "TBR"]
    optional = ["P_net_e_MW"]  # optional unless a plant model is enabled
    for k in required:
        v = outputs.get(k)
        f = _num(v)
        add(f"finite:{k}", (f is not None) and (f == f) and (abs(f) < 1e30), f"value={v}")

    # Optional numeric KPIs: record status but do not fail audit if absent
    for k in optional:
        if k not in outputs or outputs.get(k) is None:
            add(f"finite:{k}", True, "not_computed")
            continue
        v = outputs.get(k)
        f = _num(v)
        add(f"finite:{k}", (f is not None) and (f == f) and (abs(f) < 1e30), f"value={v}")


    # Fractions / ratios sanity
    for k in ["fG", "eta_CD", "eta_e"]:
        if k not in outputs:
            continue
        f = _num(outputs.get(k))
        if f is None:
            add(f"range:{k}", False, f"value={outputs.get(k)}")
        else:
            add(f"range:{k}", 0.0 <= f <= 5.0, f"value={f}")

    # Non-negative power-like quantities
    for k in ["Paux_MW", "Pohm_MW", "P_LH_MW", "P_rad_MW", "P_ohmic_MW"]:
        if k not in outputs:
            continue
        f = _num(outputs.get(k))
        if f is None:
            add(f"nonneg:{k}", False, f"value={outputs.get(k)}")
        else:
            add(f"nonneg:{k}", f >= -1e-9, f"value={f}")

    overall_ok = all(bool(c.get("ok", False)) for c in checks) if checks else True
    return {
        "schema_version": "verification_checks.v1",
        "overall_ok": overall_ok,
        "checks": checks,
    }