from __future__ import annotations

"""Plant Sankey-grade power ledger authority v419 — extend v408 plant bookkeeping.

Purpose
-------
MATCH-as-overlay deepening of PROCESS-class *power-requirements* coverage:
explicit source→sink thermal/electric flows, recirculating load breakdown,
conservation residual checks, and PROXY-labeled Sankey node/link tables —
without putting plant power iteration / solvers into L0.

Extends the CD-mix plant electric ledger (v408) and the algebraic plant
closure already computed in ``physics/plant.py`` / ``hot_ion_point``.

Hard laws
---------
- Algebraic, single-pass, deterministic. No solvers, no iteration, no smoothing.
- Does **not** mutate L0 truth equations; governance overlay only.
- Reads already-computed plant / plasma power outputs from ``hot_ion_point``.
- Screening / proxy tier — not a detailed Brayton/Rankine or BOP simulator.
- No invented PROCESS MFILE reference numbers.
- Pe_net / COE display must still respect ``plant_kpi_honesty.v1`` watermark.

Inputs (expected)
-----------------
From ``inp``:
- include_plant_sankey_ledger_authority_v419
- optional: P_tritium_plant_MW (NaN → 0), plant_sankey_conservation_tol_MW_v419,
  plant_sankey_f_recirc_max_v419, plant_sankey_Pe_net_min_MW_v419
- plant closure knobs already used by L0: eta_*, P_balance_of_plant_MW,
  P_pumps_MW, P_cryo_20K_MW, cryo_COP, blanket_energy_mult, …

From ``out`` (already computed):
- Pfus_total_MW / P_fus_MW, Palpha_MW, Prad_core_MW, P_SOL_MW
- Pth_total_MW, P_e_gross_MW, P_recirc_MW, P_e_net_MW, Qe
- P_cryo_MW, P_aux_total_el_MW, P_cd_launch_MW, P_tf_ohmic_MW, …

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, List, Optional, Tuple


AUTHORITY_ID = "plant_sankey_ledger_authority_v419"
OVERLAY_VERSION = "v419.0.0"
SCREENING_TIER = "proxy"

# Default absolute residual tolerance for conservation checks [MW].
_DEFAULT_TOL_MW = 1e-3


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def _pick(out: Dict[str, Any], *keys: str, default: float = float("nan")) -> float:
    for k in keys:
        if k in out:
            v = _f(out.get(k))
            if _finite(v):
                return v
    return float(default)


def _flow(
    source: str,
    sink: str,
    value_MW: float,
    *,
    kind: str,
    provenance: str,
) -> Dict[str, Any]:
    return {
        "source": str(source),
        "sink": str(sink),
        "value_MW": float(value_MW) if _finite(value_MW) else float("nan"),
        "kind": str(kind),
        "units": "MW",
        "provenance": str(provenance),
        "screening_tier": SCREENING_TIER,
    }


def _node(node_id: str, label: str, role: str) -> Dict[str, str]:
    return {"id": node_id, "label": label, "role": role, "units": "MW"}


def _residual(name: str, left_MW: float, right_MW: float, tol_MW: float) -> Dict[str, Any]:
    ok = False
    resid = float("nan")
    if _finite(left_MW) and _finite(right_MW):
        resid = left_MW - right_MW
        ok = abs(resid) <= max(tol_MW, 0.0)
    elif not _finite(left_MW) and not _finite(right_MW):
        ok = True
        resid = 0.0
    return {
        "name": name,
        "left_MW": float(left_MW) if _finite(left_MW) else float("nan"),
        "right_MW": float(right_MW) if _finite(right_MW) else float("nan"),
        "residual_MW": float(resid) if _finite(resid) else float("nan"),
        "tol_MW": float(tol_MW),
        "ok": bool(ok),
        "units": "MW",
    }


def _component_loads(out: Dict[str, Any], inp: Any) -> Dict[str, float]:
    """Decompose recirculating electric draws [MW(e)] from L0 / inputs."""
    eta_aux = _f(getattr(inp, "eta_aux_wallplug", 0.40), 0.40)
    if not _finite(eta_aux) or eta_aux <= 0.0:
        eta_aux = 0.40
    eta_cd = _f(
        out.get("eta_cd_wallplug_used", getattr(inp, "eta_cd_wallplug", 0.33)),
        0.33,
    )
    if not _finite(eta_cd) or eta_cd <= 0.0:
        eta_cd = 0.33
    eta_tf = _f(getattr(inp, "eta_tf_wallplug", 0.95), 0.95)
    if not _finite(eta_tf) or eta_tf <= 0.0:
        eta_tf = 0.95

    Paux_th = _f(getattr(inp, "Paux_MW", out.get("Paux_MW", 0.0)), 0.0)
    Pcd_launch = _f(out.get("P_cd_launch_MW"), 0.0)
    P_tf_ohmic = _f(out.get("P_tf_ohmic_MW"), 0.0)

    P_hcd_el = max(Paux_th, 0.0) / eta_aux + max(Pcd_launch, 0.0) / eta_cd
    P_tf_el = max(P_tf_ohmic, 0.0) / eta_tf

    P_cryo = _pick(out, "P_cryo_MW")
    if not _finite(P_cryo):
        cop = _f(getattr(inp, "cryo_COP", float("nan")))
        p20 = _f(getattr(inp, "P_cryo_20K_MW", float("nan")))
        if _finite(cop) and cop > 0.0 and _finite(p20) and p20 >= 0.0:
            P_cryo = p20 / cop
        else:
            P_cryo = 0.0

    P_pumps = _f(getattr(inp, "P_pumps_MW", out.get("P_pumps_MW", 0.0)), 0.0)
    if not _finite(P_pumps):
        P_pumps = 0.0

    P_bop = _f(getattr(inp, "P_balance_of_plant_MW", 20.0), 20.0)
    if not _finite(P_bop):
        P_bop = 0.0

    P_tritium = _f(getattr(inp, "P_tritium_plant_MW", float("nan")))
    tritium_assumed = False
    if not _finite(P_tritium):
        P_tritium = 0.0
        tritium_assumed = True

    return {
        "P_hcd_el_MW": float(P_hcd_el),
        "P_tf_el_MW": float(P_tf_el),
        "P_cryo_el_MW": float(P_cryo) if _finite(P_cryo) else 0.0,
        "P_pumps_el_MW": float(max(P_pumps, 0.0)),
        "P_bop_el_MW": float(max(P_bop, 0.0)),
        "P_tritium_el_MW": float(max(P_tritium, 0.0)),
        "P_aux_th_MW": float(max(Paux_th, 0.0)),
        "P_cd_launch_MW": float(max(Pcd_launch, 0.0)),
        "P_tf_ohmic_MW": float(max(P_tf_ohmic, 0.0)),
        "eta_aux_wallplug": float(eta_aux),
        "eta_cd_wallplug": float(eta_cd),
        "eta_tf_wallplug": float(eta_tf),
        "tritium_load_assumed_zero": float(1.0 if tritium_assumed else 0.0),
    }


def compute(inp: Any, out: Dict[str, Any]) -> Dict[str, Any]:
    tol = _f(getattr(inp, "plant_sankey_conservation_tol_MW_v419", float("nan")))
    if not _finite(tol) or tol < 0.0:
        tol = _DEFAULT_TOL_MW

    f_recirc_max = _f(getattr(inp, "plant_sankey_f_recirc_max_v419", float("nan")))
    Pe_net_min = _f(getattr(inp, "plant_sankey_Pe_net_min_MW_v419", float("nan")))

    Pfus = _pick(out, "Pfus_total_MW", "P_fus_MW", "Pfus_MW", "P_fusion_MW", default=0.0)
    Palpha = _pick(out, "Palpha_MW", "P_alpha_MW")
    if not _finite(Palpha):
        # DT convention proxy when alpha not stamped
        Palpha = 0.2 * max(Pfus, 0.0)
    Pn = _pick(out, "P_n_MW", "Pneu_MW", "P_neutron_MW")
    if not _finite(Pn):
        Pn = max(Pfus - Palpha, 0.0)

    Paux_th = _f(getattr(inp, "Paux_MW", out.get("Paux_MW", 0.0)), 0.0)
    Prad = _pick(out, "Prad_core_MW", "Prad_MW", "P_rad_core_MW", default=0.0)
    Psol = _pick(out, "P_SOL_MW", "Psol_MW", "P_sol_MW", default=0.0)

    Pth = _pick(out, "Pth_total_MW", "Pth_MW", "P_th_MW")
    if not _finite(Pth):
        mult = _f(getattr(inp, "blanket_energy_mult", 1.0), 1.0)
        Pth = max(mult, 0.0) * max(Pfus, 0.0)

    Pe_gross = _pick(out, "P_e_gross_MW", "Pe_gross_MW", "P_gross_e_MW")
    Precirc_l0 = _pick(out, "P_recirc_MW", "Precirc_MW", "P_e_recirc_MW")
    Pe_net = _pick(out, "P_e_net_MW", "Pe_net_MW", "P_net_e_MW")
    Qe = _pick(out, "Qe", "Q_eng")

    eta_elec = float("nan")
    if _finite(Pe_gross) and _finite(Pth) and Pth > 1e-12:
        eta_elec = Pe_gross / Pth

    comps = _component_loads(out, inp)
    Precirc_sum_declared = (
        comps["P_hcd_el_MW"]
        + comps["P_tf_el_MW"]
        + comps["P_cryo_el_MW"]
        + comps["P_pumps_el_MW"]
        + comps["P_bop_el_MW"]
        + comps["P_tritium_el_MW"]
    )

    # Prefer L0 Precirc for net electric identity; reconcile Sankey recirc
    # breakdown so component flows sum to L0 Precirc (pumping absorbs residual
    # when coolant-pump model differs from inp.P_pumps_MW).
    Precirc_use = Precirc_l0 if _finite(Precirc_l0) else Precirc_sum_declared
    pumps_reconciled = False
    if _finite(Precirc_l0):
        other = (
            comps["P_hcd_el_MW"]
            + comps["P_tf_el_MW"]
            + comps["P_cryo_el_MW"]
            + comps["P_bop_el_MW"]
            + comps["P_tritium_el_MW"]
        )
        pumps_implied = Precirc_l0 - other
        if _finite(pumps_implied) and abs(pumps_implied - comps["P_pumps_el_MW"]) > 1e-6:
            comps["P_pumps_el_MW"] = float(max(pumps_implied, 0.0))
            pumps_reconciled = True
    Precirc_sum = (
        comps["P_hcd_el_MW"]
        + comps["P_tf_el_MW"]
        + comps["P_cryo_el_MW"]
        + comps["P_pumps_el_MW"]
        + comps["P_bop_el_MW"]
        + comps["P_tritium_el_MW"]
    )

    if not _finite(Pe_net) and _finite(Pe_gross) and _finite(Precirc_use):
        Pe_net = Pe_gross - Precirc_use

    f_recirc = float("nan")
    if _finite(Pe_gross) and Pe_gross > 1e-9 and _finite(Precirc_use):
        f_recirc = Precirc_use / Pe_gross

    Pin = max(Paux_th, 0.0) + max(Palpha, 0.0)

    flows: List[Dict[str, Any]] = []
    # Thermal / plasma partition
    flows.append(_flow("fusion", "alpha_plasma", Palpha, kind="thermal", provenance="L0 Palpha or 0.2·Pfus PROXY"))
    flows.append(_flow("fusion", "neutrons_blanket", Pn, kind="thermal", provenance="L0 Pn or Pfus−Pα PROXY"))
    flows.append(_flow("aux_heating", "plasma_input", max(Paux_th, 0.0), kind="thermal", provenance="inp.Paux_MW"))
    flows.append(_flow("alpha_plasma", "plasma_input", Palpha, kind="thermal", provenance="alpha heating"))
    flows.append(_flow("plasma_input", "core_radiation", max(Prad, 0.0), kind="thermal", provenance="L0 Prad_core"))
    flows.append(_flow("plasma_input", "divertor_SOL", max(Psol, 0.0), kind="thermal", provenance="L0 P_SOL"))
    flows.append(
        _flow(
            "neutrons_blanket",
            "thermal_blanket",
            max(Pth, 0.0),
            kind="thermal",
            provenance="L0 Pth / blanket_mult·Pfus",
        )
    )
    # Electric conversion + recirculating
    flows.append(
        _flow(
            "thermal_blanket",
            "gross_electric",
            max(Pe_gross, 0.0) if _finite(Pe_gross) else float("nan"),
            kind="electric",
            provenance="L0 η_elec·Pth",
        )
    )
    flows.append(
        _flow(
            "gross_electric",
            "recirc_HCD",
            comps["P_hcd_el_MW"],
            kind="electric",
            provenance="Paux/η_aux + Pcd/η_cd wallplug",
        )
    )
    flows.append(
        _flow(
            "gross_electric",
            "recirc_cryo",
            comps["P_cryo_el_MW"],
            kind="electric",
            provenance="P_cryo_20K / COP",
        )
    )
    flows.append(
        _flow(
            "gross_electric",
            "recirc_pumping",
            comps["P_pumps_el_MW"],
            kind="electric",
            provenance="inp.P_pumps_MW" + (" (reconciled to L0 Precirc)" if pumps_reconciled else ""),
        )
    )
    flows.append(
        _flow(
            "gross_electric",
            "recirc_tritium",
            comps["P_tritium_el_MW"],
            kind="electric",
            provenance="inp.P_tritium_plant_MW (0 if unset)",
        )
    )
    flows.append(
        _flow(
            "gross_electric",
            "recirc_BOP",
            comps["P_bop_el_MW"],
            kind="electric",
            provenance="inp.P_balance_of_plant_MW",
        )
    )
    if comps["P_tf_el_MW"] > 0.0:
        flows.append(
            _flow(
                "gross_electric",
                "recirc_TF_ohmic",
                comps["P_tf_el_MW"],
                kind="electric",
                provenance="P_tf_ohmic / η_tf",
            )
        )
    flows.append(
        _flow(
            "gross_electric",
            "net_electric",
            Pe_net if _finite(Pe_net) else float("nan"),
            kind="electric",
            provenance="L0 Pe_gross − Precirc (watermark via plant_kpi_honesty.v1)",
        )
    )

    nodes = [
        _node("fusion", "Fusion", "source"),
        _node("aux_heating", "Aux heating", "source"),
        _node("alpha_plasma", "Alpha → plasma", "transfer"),
        _node("neutrons_blanket", "Neutrons → blanket", "transfer"),
        _node("plasma_input", "Plasma input", "transfer"),
        _node("core_radiation", "Core radiation", "sink"),
        _node("divertor_SOL", "SOL / divertor", "sink"),
        _node("thermal_blanket", "Blanket / thermal", "transfer"),
        _node("gross_electric", "Gross electric", "transfer"),
        _node("recirc_HCD", "Recirc — HCD", "sink"),
        _node("recirc_cryo", "Recirc — cryo", "sink"),
        _node("recirc_pumping", "Recirc — pumping", "sink"),
        _node("recirc_tritium", "Recirc — tritium plant", "sink"),
        _node("recirc_BOP", "Recirc — BOP", "sink"),
        _node("recirc_TF_ohmic", "Recirc — TF ohmic", "sink"),
        _node("net_electric", "Net electric", "sink"),
    ]

    # Fusion α+n partition is informational when alpha-loss / DT-adj differ from Pfus.
    fusion_check = _residual("fusion_partition", Pfus, Palpha + Pn, max(tol, 0.05 * max(abs(Pfus), 1.0)))
    fusion_check["informational"] = True
    checks = [
        fusion_check,
        _residual("plasma_power", Pin, max(Prad, 0.0) + max(Psol, 0.0), tol),
        _residual("electric_identity", Pe_gross, Precirc_use + Pe_net, tol),
        _residual("recirc_component_sum", Precirc_use, Precirc_sum, max(tol, 1e-2)),
    ]
    # Gate conservation_ok on bookkeeping identities only (not fusion α/n split).
    conservation_ok = all(
        bool(c.get("ok")) for c in checks if not c.get("informational")
    )

    # Plotly-ready Sankey kwargs (MW); filter non-positive / non-finite
    label_order = [n["label"] for n in nodes]
    id_to_label = {n["id"]: n["label"] for n in nodes}
    idx = {lab: i for i, lab in enumerate(label_order)}
    link_src: List[int] = []
    link_tgt: List[int] = []
    link_val: List[float] = []
    for fl in flows:
        v = _f(fl.get("value_MW"))
        if not _finite(v) or v <= 0.0:
            continue
        s = id_to_label.get(str(fl["source"]))
        t = id_to_label.get(str(fl["sink"]))
        if s is None or t is None:
            continue
        link_src.append(idx[s])
        link_tgt.append(idx[t])
        link_val.append(float(v))

    sankey_kwargs = {
        "arrangement": "snap",
        "valueformat": ".2f",
        "valuesuffix": " MW",
        "node": {"label": label_order, "pad": 12, "thickness": 14},
        "link": {"source": link_src, "target": link_tgt, "value": link_val},
    }

    dominant = "none"
    if _finite(f_recirc) and f_recirc > 1.0:
        dominant = "recirc_exceeds_gross"
    elif _finite(Pe_net) and Pe_net < 0.0:
        dominant = "negative_Pe_net"
    elif not conservation_ok:
        bad = [c["name"] for c in checks if not c.get("ok")]
        dominant = bad[0] if bad else "conservation"
    elif comps["P_hcd_el_MW"] >= max(
        comps["P_cryo_el_MW"],
        comps["P_pumps_el_MW"],
        comps["P_bop_el_MW"],
        comps["P_tritium_el_MW"],
        comps["P_tf_el_MW"],
    ):
        dominant = "HCD"
    else:
        # Largest recirc sink
        sinks = [
            ("cryo", comps["P_cryo_el_MW"]),
            ("pumping", comps["P_pumps_el_MW"]),
            ("BOP", comps["P_bop_el_MW"]),
            ("tritium", comps["P_tritium_el_MW"]),
            ("TF_ohmic", comps["P_tf_el_MW"]),
            ("HCD", comps["P_hcd_el_MW"]),
        ]
        dominant = max(sinks, key=lambda kv: kv[1])[0]

    system_tier = "comfortable"
    if not conservation_ok or (_finite(Pe_net) and Pe_net < 0.0):
        system_tier = "deficit"
    elif _finite(f_recirc) and f_recirc > 0.7:
        system_tier = "near_limit"
    elif _finite(f_recirc_max) and _finite(f_recirc) and f_recirc > f_recirc_max:
        system_tier = "deficit"

    flow_table = [
        {
            "source": fl["source"],
            "sink": fl["sink"],
            "value_MW": fl["value_MW"],
            "kind": fl["kind"],
            "tier": "PROXY",
            "provenance": fl["provenance"],
        }
        for fl in flows
        if _finite(_f(fl.get("value_MW"))) and _f(fl.get("value_MW")) > 0.0
    ]

    patch: Dict[str, Any] = {
        "plant_v419_enabled": True,
        "plant_v419_authority_id": AUTHORITY_ID,
        "plant_v419_overlay_version": OVERLAY_VERSION,
        "plant_v419_screening_tier": SCREENING_TIER,
        "plant_v419_extends": "cd_mix_plant_ledger_v408 + physics.plant_power_closure",
        "plant_v419_provenance": (
            "algebraic Sankey-grade plant power ledger from L0 plant closure + "
            "recirc component breakdown; PROXY screening; not PROCESS MFILE parity; "
            "Pe_net display must use plant_kpi_honesty.v1 watermark"
        ),
        "plant_v419_requires_kpi_honesty_watermark": True,
        "plant_v419_kpi_honesty_schema": "plant_kpi_honesty.v1",
        "plant_v419_Pfus_MW": float(Pfus),
        "plant_v419_Palpha_MW": float(Palpha),
        "plant_v419_Pn_MW": float(Pn),
        "plant_v419_Paux_th_MW": float(max(Paux_th, 0.0)),
        "plant_v419_Pin_MW": float(Pin),
        "plant_v419_Prad_core_MW": float(Prad) if _finite(Prad) else float("nan"),
        "plant_v419_Psol_MW": float(Psol) if _finite(Psol) else float("nan"),
        "plant_v419_Pth_MW": float(Pth) if _finite(Pth) else float("nan"),
        "plant_v419_eta_elec": float(eta_elec) if _finite(eta_elec) else float("nan"),
        "plant_v419_Pe_gross_MW": float(Pe_gross) if _finite(Pe_gross) else float("nan"),
        "plant_v419_Precirc_MW": float(Precirc_use) if _finite(Precirc_use) else float("nan"),
        "plant_v419_Precirc_sum_MW": float(Precirc_sum),
        "plant_v419_Pe_net_MW": float(Pe_net) if _finite(Pe_net) else float("nan"),
        "plant_v419_Qe": float(Qe) if _finite(Qe) else float("nan"),
        "plant_v419_f_recirc": float(f_recirc) if _finite(f_recirc) else float("nan"),
        "plant_v419_P_hcd_el_MW": comps["P_hcd_el_MW"],
        "plant_v419_P_cryo_el_MW": comps["P_cryo_el_MW"],
        "plant_v419_P_pumps_el_MW": comps["P_pumps_el_MW"],
        "plant_v419_P_tritium_el_MW": comps["P_tritium_el_MW"],
        "plant_v419_P_bop_el_MW": comps["P_bop_el_MW"],
        "plant_v419_P_tf_el_MW": comps["P_tf_el_MW"],
        "plant_v419_pumps_reconciled_to_L0": bool(pumps_reconciled),
        "plant_v419_tritium_load_assumed_zero": bool(comps["tritium_load_assumed_zero"] > 0.5),
        "plant_v419_conservation_ok": bool(conservation_ok),
        "plant_v419_conservation_tol_MW": float(tol),
        "plant_v419_conservation_checks": checks,
        "plant_v419_system_tier": str(system_tier),
        "plant_v419_dominant_aspect": str(dominant),
        "plant_v419_flow_ledger": flows,
        "plant_v419_flow_table": flow_table,
        "plant_v419_nodes": nodes,
        "plant_v419_sankey_kwargs": sankey_kwargs,
        "plant_v419_n_flows": int(len(flow_table)),
        # Optional caps echoed for constraint layer (NaN disables)
        "plant_sankey_conservation_tol_MW_v419": float(tol),
        "plant_sankey_f_recirc_max_v419": float(f_recirc_max),
        "plant_sankey_Pe_net_min_MW_v419": float(Pe_net_min),
        "plant_v419_units": {
            "power": "MW",
            "electric": "MW(e)",
            "thermal": "MW(th)",
            "efficiency": "dimensionless",
            "f_recirc": "Precirc / Pe_gross",
        },
        "plant_v419_narrative": (
            f"Pe_net={Pe_net:.4g} MW; f_recirc={f_recirc:.4g}; "
            f"conservation_ok={conservation_ok}; dominant={dominant}; "
            f"tier={system_tier}; PROXY Sankey plant ledger "
            f"(watermark Pe_net via plant_kpi_honesty.v1)"
            if _finite(Pe_net) and _finite(f_recirc)
            else f"dominant={dominant}; tier={system_tier}; PROXY Sankey plant ledger"
        ),
    }
    return patch


def evaluate_plant_sankey_ledger_authority_v419(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Deterministic Sankey-grade plant ledger overlay. Does not re-solve physics.

    When disabled, returns ``{}`` so default evaluator outputs (and goldens) are
    unchanged — L0 numeric truth and artifact key sets stay frozen.
    """
    enabled = bool(getattr(inp, "include_plant_sankey_ledger_authority_v419", False))
    if not enabled:
        return {}
    patch = compute(inp, out)
    patch["include_plant_sankey_ledger_authority_v419"] = True
    return patch


def build_sankey_kwargs_from_outputs(out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Prefer stamped v419 sankey kwargs when overlay enabled."""
    if not bool(out.get("plant_v419_enabled", False)):
        return None
    kw = out.get("plant_v419_sankey_kwargs")
    return dict(kw) if isinstance(kw, dict) else None
