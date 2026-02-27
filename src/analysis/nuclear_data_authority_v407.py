from __future__ import annotations

"""Nuclear Data Authority Deepening (v407.0.0).

Goal
----
Add a multi-group, dataset-provenanced neutronics screening overlay without
violating SHAMS frozen-truth law.

Hard rules
----------
- Deterministic algebra only.
- No Monte Carlo.
- No spectral iteration.
- No depletion chains.

This authority provides:
- Explicit nuclear dataset provenance + SHA-256 pin
- Multi-group attenuation through the v403 stack (or a minimal fallback)
- TF-case fluence proxy per group + total
- Bounded multi-group TBR proxy (screening only)

Units
-----
- Sigma_removal: 1/m
- Thickness: m
- Flux: n/m^2/s
- Fluence: n/m^2/FPY
"""

import json
import math
from typing import Any, Dict, List, Tuple

from nuclear_data.datasets import get_dataset
from nuclear_data.group_structures import get_group_structure


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _normalize(v: List[float]) -> List[float]:
    s = sum(max(float(x), 0.0) for x in v)
    if s <= 0.0:
        return [1.0 / max(len(v), 1) for _ in v]
    return [max(float(x), 0.0) / s for x in v]


def _parse_stack_layers(nm_stack_json: str) -> List[Dict[str, Any]]:
    """Parse v403 stack JSON into a list of layers."""
    try:
        layers = json.loads(nm_stack_json)
        if isinstance(layers, list):
            out: List[Dict[str, Any]] = []
            for it in layers:
                if not isinstance(it, dict):
                    continue
                mat = str(it.get("material", ""))
                t = _safe_float(it.get("thickness_m", 0.0), 0.0)
                rho = _safe_float(it.get("density_factor", 1.0), 1.0)
                if not mat:
                    continue
                out.append({"material": mat, "thickness_m": max(t, 0.0), "density_factor": max(rho, 0.0)})
            return out
    except Exception:
        pass
    return []


def _fallback_stack(inp: Any) -> List[Dict[str, Any]]:
    # Minimal deterministic fallback: shield + blanket thicknesses as SS316/LiPb.
    t_sh = max(_safe_float(getattr(inp, "t_shield_m", 0.0), 0.0), 0.0)
    t_bl = max(_safe_float(getattr(inp, "t_blanket_m", 0.0), 0.0), 0.0)
    return [
        {"material": "SS316", "thickness_m": t_sh, "density_factor": 1.0},
        {"material": "LiPb", "thickness_m": t_bl, "density_factor": 1.0},
    ]


def _wall_load_to_flux_fw_n_m2_s(neutron_wall_load_MW_m2: float) -> float:
    # Keep consistent with src/physics/neutronics.py
    # 1 MW/m^2 ~ 3.5e19 n/m^2/s at 14 MeV (rough proxy)
    return max(neutron_wall_load_MW_m2, 0.0) * 3.5e19


def evaluate_nuclear_data_authority_v407(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    enabled = bool(getattr(inp, "include_nuclear_data_authority_v407", False))
    res: Dict[str, Any] = {
        "include_nuclear_data_authority_v407": enabled,
        "nuclear_dataset_id_v407": "",
        "nuclear_dataset_sha256_v407": "",
        "group_structure_id_v407": "",
        "group_edges_MeV_v407": [],
        "spectrum_frac_fw_v407": [],
        "attenuation_g_to_tf_v407": [],
        "fluence_g_to_tf_n_m2_per_fpy_v407": [],
        "tf_case_fluence_n_m2_per_fpy_v407": float("nan"),
        "tbr_mg_proxy_v407": float("nan"),
        "nuclear_data_authority_ledger_v407": [],
    }
    if not enabled:
        return res

    dataset_id = str(getattr(inp, "nuclear_dataset_id_v407", "SCREENING_PROXY_V407"))
    gs_id = str(getattr(inp, "nuclear_group_structure_id_v407", "G6_V407"))

    ds = get_dataset(dataset_id)
    gs = get_group_structure(gs_id)

    if ds.group_structure_id != gs.group_structure_id:
        raise ValueError(
            f"Dataset group_structure_id mismatch: dataset {ds.group_structure_id} vs selected {gs.group_structure_id}"
        )

    ng = gs.n_groups
    # Spectrum: prefer v403 3-group fractions if present
    f_fast = _safe_float(getattr(inp, "nm_group_frac_fast_v403", float("nan")))
    f_epi = _safe_float(getattr(inp, "nm_group_frac_epi_v403", float("nan")))
    f_th = _safe_float(getattr(inp, "nm_group_frac_therm_v403", float("nan")))

    if all((x == x) and math.isfinite(x) for x in [f_fast, f_epi, f_th]) and (f_fast + f_epi + f_th) > 0:
        # Map 3-group -> 6-group deterministically.
        # Groups: [14-6],[6-2],[2-0.5] ~ fast ; [0.5-0.1],[0.1-1e-3] ~ epi ; [1e-3-0] ~ thermal
        spec = [f_fast/3.0, f_fast/3.0, f_fast/3.0, f_epi/2.0, f_epi/2.0, f_th]
    else:
        spec = list(ds.spectrum_frac_fw)

    if len(spec) != ng:
        # Last resort: pad/trim
        if len(spec) < ng:
            spec = spec + [0.0]*(ng-len(spec))
        else:
            spec = spec[:ng]
    spec = _normalize(spec)

    # Determine FW neutron wall load from outputs if available, else compute from fusion power.
    nwl = _safe_float(out.get("neutron_wall_load_MW_m2", float("nan")))
    if not (nwl == nwl and math.isfinite(nwl)):
        Pfus_MW = _safe_float(out.get("Pfus_total_MW", out.get("Pfus_MW", float("nan"))))
        A_fw = _safe_float(out.get("A_fw_m2", out.get("A_fw", float("nan"))))
        if not (Pfus_MW == Pfus_MW and math.isfinite(Pfus_MW) and A_fw == A_fw and math.isfinite(A_fw) and A_fw > 0):
            # Fallback: assume 1 MW/m2
            nwl = 1.0
        else:
            nwl = (0.8 * max(Pfus_MW, 0.0)) / max(A_fw, 1e-6)

    nflux_fw = _wall_load_to_flux_fw_n_m2_s(nwl)

    # Stack layers: prefer v403 stack json if present
    layers = _parse_stack_layers(str(getattr(inp, "nm_stack_json_v403", "")))
    if not layers:
        layers = _fallback_stack(inp)

    # Include optional gap to TF-case if present (from v392).
    gap_to_tf = max(_safe_float(getattr(inp, "gap_to_tf_case_m_v392", 0.2), 0.2), 0.0)
    if gap_to_tf > 0:
        layers = list(layers) + [{"material": "Air", "thickness_m": gap_to_tf, "density_factor": 1.0}]

    # Multi-group attenuation
    A_g = [1.0 for _ in range(ng)]
    ledger: List[Dict[str, Any]] = []
    for layer in layers:
        mat = str(layer.get("material", ""))
        t = max(_safe_float(layer.get("thickness_m", 0.0), 0.0), 0.0)
        rho = max(_safe_float(layer.get("density_factor", 1.0), 1.0), 0.0)
        if t <= 0.0:
            continue
        coeffs = ds.sigma_removal_1_m.get(mat)
        if coeffs is None:
            # Unknown material: treat as SS316 proxy to avoid silent zero attenuation.
            coeffs = ds.sigma_removal_1_m.get("SS316", [0.0]*ng)
            mat_used = f"{mat}(mapped->SS316)"
        else:
            mat_used = mat
        if len(coeffs) != ng:
            coeffs = (list(coeffs) + [0.0]*ng)[:ng]
        for i in range(ng):
            Sigma = max(float(coeffs[i]), 0.0) * rho
            A_g[i] *= math.exp(-Sigma * t)
        ledger.append({
            "material": mat_used,
            "thickness_m": t,
            "density_factor": rho,
        })

    # Geometry factor: use existing f_geom_to_tf if present
    f_geom = max(_safe_float(getattr(inp, "f_geom_to_tf", 0.0), 0.0), 0.0)

    fpy_s = 365.25 * 24.0 * 3600.0
    flu_g = []
    for i in range(ng):
        nflux_g_tf = nflux_fw * spec[i] * A_g[i] * f_geom
        flu_g.append(nflux_g_tf * fpy_s)

    tf_flu = float(sum(flu_g))

    # Bounded multi-group TBR proxy: response weight dot spectrum*attenuation
    w = list(ds.tbr_response_weight)
    if len(w) != ng:
        w = (w + [0.0]*ng)[:ng]
    # proxy is scaled to ~O(1) and multiplied by the existing blanket coverage if present
    coverage = max(_safe_float(out.get("blanket_coverage", getattr(inp, "blanket_coverage", 1.0)), 1.0), 0.0)
    tbr_proxy = coverage * float(sum(w[i] * spec[i] * A_g[i] for i in range(ng)))

    res.update({
        "nuclear_dataset_id_v407": ds.dataset_id,
        "nuclear_dataset_sha256_v407": ds.sha256,
        "group_structure_id_v407": gs.group_structure_id,
        "group_edges_MeV_v407": list(gs.edges_MeV),
        "spectrum_frac_fw_v407": list(spec),
        "attenuation_g_to_tf_v407": [float(x) for x in A_g],
        "fluence_g_to_tf_n_m2_per_fpy_v407": [float(x) for x in flu_g],
        "tf_case_fluence_n_m2_per_fpy_v407": tf_flu,
        "tbr_mg_proxy_v407": float(tbr_proxy),
        "nuclear_data_authority_ledger_v407": ledger,
    })

    return res
