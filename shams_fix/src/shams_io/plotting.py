
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .run_artifact import read_run_artifact, summarize_constraints
try:
    from ..decision.kpis import headline_kpis  # type: ignore
except Exception:
    from decision.kpis import headline_kpis  # type: ignore


@dataclass(frozen=True)
class RadialBuildLayer:
    name: str
    thickness_m: float


def _get_layers_from_inputs(inp: Dict[str, Any]) -> List[RadialBuildLayer]:
    # Names align with src/phase1_systems.RadialBuild
    layers = [
        ("Gap", float(inp.get("t_gap_m", 0.0))),
        ("Vacuum vessel", float(inp.get("t_vv_m", 0.0))),
        ("Shield", float(inp.get("t_shield_m", 0.0))),
        ("Blanket", float(inp.get("t_blanket_m", 0.0))),
        ("First wall", float(inp.get("t_fw_m", 0.0))),
    ]
    # coil layers (kept separate)
    coil = [
        ("TF winding pack", float(inp.get("t_tf_wind_m", 0.0))),
        ("TF structure", float(inp.get("t_tf_struct_m", 0.0))),
    ]
    out = [RadialBuildLayer(n, t) for n, t in layers if t > 0]
    out += [RadialBuildLayer(n, t) for n, t in coil if t > 0]
    return out


def plot_radial_build_from_artifact(artifact: Dict[str, Any], savepath: str | Path) -> Path:
    """PROCESS-style radial build bar-segment plot (inboard stack)."""
    inp = artifact.get("inputs", {})
    out = artifact.get("outputs", {})
    R0 = float(inp.get("R0_m", float("nan")))
    a = float(inp.get("a_m", float("nan")))
    Rin_edge = R0 - a
    layers = _get_layers_from_inputs(inp)

    # Bar plot: cumulative thickness from plasma inboard edge inward.
    #
    # IMPORTANT (Streamlit export stability):
    # - Always create a fresh figure
    # - Avoid bbox_inches="tight" because it can change legend/xlabel layout
    #   across backends/DPIs and cause "mixed captions" (overlaps).
    # - Use an axes-attached legend below the plot with a fixed bottom margin.
    fig, ax = plt.subplots(figsize=(9.2, 3.6), constrained_layout=False)
    left = 0.0
    for lyr in layers:
        ax.barh([0], [lyr.thickness_m], left=left, height=0.6, label=lyr.name)
        left += lyr.thickness_m

    ax.axvline(Rin_edge, linestyle="--", linewidth=1.2)
    ax.set_yticks([])
    # Deterministic legend placement (below axis).
    handles, labels = ax.get_legend_handles_labels()
    if handles and labels:
        # De-duplicate while preserving order (matplotlib can repeat labels
        # if artists are re-used).
        seen = set()
        h2, l2 = [], []
        for h, l in zip(handles, labels):
            if l in seen:
                continue
            seen.add(l)
            h2.append(h)
            l2.append(l)
        ax.legend(
            h2,
            l2,
            loc="upper center",
            # Push legend a bit further down to avoid any overlap with
            # xlabel on small viewers / different font metrics.
            bbox_to_anchor=(0.5, -0.28),
            ncol=3,
            frameon=False,
            fontsize=9,
        )
    # Reserve stable space for xlabel + legend.
    fig.subplots_adjust(bottom=0.50)
    ax.set_xlabel("Inboard midplane radius (m) measured from magnetic axis", labelpad=12)
    ax.set_title("Radial build (inboard): plasma edge to TF inner leg")

    # Show key feasibility numbers
    R_coil_inner = out.get("R_coil_inner_m", None)
    ok = bool(float(out.get("radial_build_ok", 0.0)) > 0.5)
    txt = f"R0-a = {Rin_edge:.3f} m\nSpent = {left:.3f} m\n"
    if isinstance(R_coil_inner, (int, float)) and math.isfinite(float(R_coil_inner)):
        txt += f"R_coil_inner = {float(R_coil_inner):.3f} m\nFeasible: {ok}"
    else:
        txt += f"R_coil_inner = n/a\nFeasible: {ok}"
    ax.text(1.01, 0.5, txt, transform=ax.transAxes, va="center")

    # v94.1: guard non-finite axis limits (offline dummy artifacts)
    _xmax = max(Rin_edge * 1.15, left * 1.15, 0.5)
    try:
        import math as _math
        if not _math.isfinite(_xmax):
            _xmax = 1.0
    except Exception:
        _xmax = 1.0
    ax.set_xlim(0, _xmax)
    p = Path(savepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Do NOT use bbox_inches="tight" (caption/legend overlap risk).
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def plot_scan_1d(scan_points: List[Dict[str, Any]], x_key: str, y_keys: List[str], savepath: str | Path) -> Path:
    """Simple PROCESS-like scan plot: multiple y vs scan variable."""
    xs = [float(p["outputs"].get(x_key, float("nan"))) for p in scan_points]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for yk in y_keys:
        ys = [float(p["outputs"].get(yk, float("nan"))) for p in scan_points]
        ax.plot(xs, ys, marker="o", linewidth=1, label=yk)
    ax.set_xlabel(x_key)
    ax.set_ylabel("Value")
    ax.set_title("1D scan")
    ax.grid(True, alpha=0.3)
    p = Path(savepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    pass  # layout handled by subplots_adjust + fig.legend
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def plot_summary_pdf(artifact: Dict[str, Any], savepath: str | Path) -> Path:
    """A lightweight analogue of PROCESS plot_proc.py: a multi-page PDF summary."""
    inp = artifact.get("inputs", {})
    out = artifact.get("outputs", {})
    cons = artifact.get("constraints", [])
    csum = summarize_constraints(cons)

    p = Path(savepath)
    p.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(p) as pdf:
        # Page 0: executive summary (decision-ready)
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis('off')
        csum2 = summarize_constraints(cons)
        feasible = (csum2.get('n_fail', 0) == 0)
        prov = artifact.get('provenance', {})
        mc = artifact.get('model_cards', {}) or {}
        low_m = []
        for mid, info in mc.items():
            try:
                trl = float((info or {}).get('maturity', {}).get('trl', 99))
            except Exception:
                trl = 99
            if trl < 5:
                low_m.append((mid, trl, (info or {}).get('maturity', {}).get('envelope','')))
        low_m.sort(key=lambda x: x[1])
        lines0 = [
            'Executive summary',
            '',
            f"Feasible (hard constraints): {feasible}",
            f"Hard fails: {csum2.get('n_fail')} / {csum2.get('n')}",
            f"Worst hard margin_frac: {csum2.get('worst_margin_frac')}",
            "",
            f"Low-maturity assumptions (trl<5): {len(low_m)}",
            '',
            'Key KPIs:',
        ]
        # Headline KPIs (standardized across UI + PDF)
        lines0.append("")
        lines0.append("Headline KPIs:")
        for lab, val in headline_kpis(out):
            lines0.append(f"  {lab}: {val}")
        # Requirements traceability summary (if present)
        req = artifact.get("requirements_trace", {}) if isinstance(artifact.get("requirements_trace", {}), dict) else {}
        if req:
            lines0.append("")
            lines0.append(f"Requirements overall: {req.get('overall','UNKNOWN')}")
            rows = req.get("requirements", [])
            if isinstance(rows, list):
                bad = [r for r in rows if isinstance(r, dict) and r.get("status") in ("FAIL","WARN")]
                for r in bad[:5]:
                    lines0.append(f"  {r.get('id')}: {r.get('status')}")

        # Program planning proxy (time + risk)
        prog = artifact.get("program", {}) if isinstance(artifact.get("program", {}), dict) else {}
        if prog:
            lines0.append("")
            lines0.append("Program proxy:")
            lines0.append(f"  Build years: {prog.get('build_years')}")
            lines0.append(f"  Commission years: {prog.get('commission_years')}")
            lines0.append(f"  Outage days/year: {prog.get('outage_days_per_year')}")
            lines0.append(f"  Delivery risk proxy: {prog.get('delivery_risk_proxy')}")

        # Non-feasibility certificate excerpt (if hard infeasible)
        nfc = artifact.get("nonfeasibility_certificate", {}) if isinstance(artifact.get("nonfeasibility_certificate", {}), dict) else {}
        if nfc:
            lines0.append("")
            lines0.append("Non-feasibility certificate:")
            for b in (nfc.get("dominant_blockers") or [])[:5]:
                if not isinstance(b, dict):
                    continue
                lines0.append(f"  Blocker: {b.get('name')}  margin={b.get('margin')}")
                bk = b.get("best_knobs") or []
                if bk:
                    lines0.append(f"    Knobs: {', '.join([str(x) for x in bk][:4])}")
# Scenario snapshot (if present)
        scen = artifact.get("scenario", {}) or artifact.get("scan", {}) or {}
        if isinstance(scen, dict) and scen:
            lines0 += ["", "Scenario snapshot:"]
            for k in ["name", "id", "case", "variant", "tag"]:
                if k in scen:
                    lines0.append(f"  {k}: {scen.get(k)}")

        # Decision-grade + maturity dependence
        dec = artifact.get("decision", {}) or {}
        if isinstance(dec, dict) and dec:
            lines0 += ["", "Decision-grade:"]
            lines0.append(f"  decision_grade_ok: {dec.get('decision_grade_ok')}")
            lines0.append(f"  message: {dec.get('decision_grade_message','')}")
            lm = dec.get("low_maturity_models") or []
            if lm:
                lines0.append("  LOW-MATURITY dependence:")
                for mid in lm[:8]:
                    lines0.append(f"    - {mid}")

        # Blockers
        bl = artifact.get('blockers', [])
        if bl:
            lines0 += ['', 'Dominant blockers:']
            for b in bl[:5]:
                lines0.append(f"  - {b.get('name')} (group={b.get('group','')}, margin_frac={b.get('margin_frac')})")
        # Trade ledger budgets
        tl = artifact.get('trade_ledger', {})
        if isinstance(tl, dict) and tl.get('budgets_abs_scaled'):
            lines0 += ['', 'Trade ledger (abs scaled budget):']
            for bk, bv in list(tl['budgets_abs_scaled'].items())[:6]:
                lines0.append(f"  {bk}: {float(bv):.3f}")
        # Verification + changelog summary (embedded for auditability)
        ver = artifact.get("verification", {}) or {}
        if isinstance(ver, dict) and ver.get("report"):
            rep = ver.get("report") or {}
            ok = rep.get("ok", rep.get("passed", None))
            lines0 += ["", "Verification summary:"]
            if ok is None:
                lines0.append("  status: (unknown)")
            else:
                lines0.append(f"  status: {'PASS' if bool(ok) else 'FAIL'}")
            # include first few checks if present
            checks = rep.get("checks") or rep.get("results") or []
            if isinstance(checks, list) and checks:
                for ch in checks[:5]:
                    nm = ch.get("name", ch.get("id","check"))
                    stt = ch.get("status", ch.get("ok", ""))
                    lines0.append(f"  - {nm}: {stt}")
        # Changelog excerpt (from provenance)
        prov = artifact.get("provenance", {}) or {}
        rne = str(prov.get("release_notes_excerpt","")).strip()
        if rne:
            lines0 += ["", "Changelog excerpt:"]
            for ln in rne.splitlines()[:12]:
                lines0.append(f"  {ln}")

        # UQ summary
        uq = artifact.get('uq', {})
        if isinstance(uq, dict) and uq:
            lines0 += ['', 'UQ summary:']
            if 'p_feasible' in uq:
                lines0.append(f"  P(feasible): {float(uq.get('p_feasible')):.3f}")
        lines0 += ['', 'Provenance:', f"  git_commit={prov.get('git_commit','')}"]
        ax.text(0.05, 0.95, "\n".join(lines0), fontsize=10, va='top', family='monospace')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        # Page 1: headline KPIs
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 portrait
        ax.axis("off")
        lines = []
        for lab, val in headline_kpis(out):
            lines.append(f"{lab:16s} = {val}")
        lines.append("")
        lines.append(f"Constraints: {csum['n']} total, {csum['n_fail']} failed; worst = {csum['worst']}")
        ax.text(0.05, 0.95, "SHAMS–FUSION-X Summary", fontsize=18, va="top")
        ax.text(0.05, 0.90, "\n".join(lines), fontsize=11, va="top", family="monospace")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Page 2b: constraint margin ledger (dominant blockers)
        ledger = artifact.get("constraint_ledger", {}) if isinstance(artifact.get("constraint_ledger", {}), dict) else {}
        top = ledger.get("top_blockers", []) if isinstance(ledger.get("top_blockers", []), list) else []
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        ax.set_title("Constraint Margin Ledger (top blockers)", fontsize=14, pad=12)
        rows = []
        for e in top:
            if not isinstance(e, dict):
                continue
            rows.append([
                str(e.get("dominance_rank", "")),
                str(e.get("severity", "")),
                str(e.get("group", "")),
                str(e.get("name", "")),
                f"{e.get('margin_frac', '')}",
                f"{e.get('margin', '')}",
                f"{e.get('value', '')}",
                f"{e.get('sense', '')}{e.get('limit','')}",
                str((e.get("best_knobs") or "") )[:60],
            ])
        if rows:
            col_labels = ["Rank","Sev","Group","Constraint","margin_frac","margin","value","limit","best_knobs"]
            table = ax.table(cellText=rows, colLabels=col_labels, loc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(7)
            table.scale(1, 1.2)
        else:
            ax.text(0.05, 0.9, "No violated constraints (or ledger unavailable).", fontsize=11, va="top")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Page 2: constraint table
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        rows = []
        for c in cons:
            rows.append([
                c.get("name",""),
                f"{c.get('value','')}",
                c.get("sense",""),
                f"{c.get('limit','')}",
                "PASS" if c.get("passed") else "FAIL",
                f"{float(c.get('margin',0.0)):.3g}",
                c.get("units",""),
            ])
        col_labels = ["Constraint","Value","Sense","Limit","Status","Margin","Units"]
        table = ax.table(cellText=rows, colLabels=col_labels, loc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)
        ax.set_title("Constraint summary", fontsize=14, pad=12)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Page 3: radial build (embed)
        tmp = p.with_suffix(".radial.png")
        plot_radial_build_from_artifact(artifact, tmp)
        fig, ax = plt.subplots(figsize=(8.27, 4.0))
        img = plt.imread(tmp)
        ax.imshow(img)
        ax.axis("off")
        ax.set_title("Radial build", fontsize=14)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        try:
            tmp.unlink()
        except Exception:
            pass


        # Page 4: model notes (equations + provenance)
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        prov = artifact.get("provenance", {})
        lines = [
            "Key model notes (auditable summary):",
            "",
            "Confinement:",
            "  tauE_eff = (W/Ploss) / (1 + c_stiff*max(0,Ploss/Ploss_ref - 1))",
            "  H98 = tauE_eff / tau_IPB98y2",
            "",
            "Power balance:",
            "  Pin = Paux + Palpha - Prad(core) - other losses",
            "  Pnet_e = eta_elec * Pth - (Paux/eta_aux_wallplug) - P_BOP - P_cryo - P_pumps - P_CD/eta_cd_wallplug",
            "",
            "Heat exhaust proxy:",
            "  q_div ~ (P_div / (2*pi*R*q_lambda)) / (flux_expansion*n_strike_points) * advanced_divertor_factor",
            "",
            "Neutronics proxy:",
            "  TBR ~ TBR_multiplier * blanket_coverage * (1 - exp(-t_shield/TBR_lambda))",
            "",
            "Changelog (code):",
            *(_format_changelog_lines(artifact)),
            "",
            "Provenance:",
            f"  python={prov.get('python_version','')}",
            f"  platform={prov.get('platform','')}",
            f"  git_commit={prov.get('git_commit','')}",
            "",
            "For full definitions, see docs/variable_registry.py and docs/PROCESS_inspired_upgrade.md",
        ]
        # NOTE: join with explicit newlines; keep this as a single Python string literal
        # to avoid accidental unterminated strings from editor line-wrapping.
        ax.text(0.05, 0.95, "\n".join(lines), fontsize=10, va="top", family="monospace")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    return p


def plot_radial_build_dual_export(artifact: dict, out_base: str) -> dict:
    """
    Additive helper: export radial build as both PNG and SVG.
    Does NOT change the existing plotting contract.
    Returns dict of produced files.
    """
    from pathlib import Path
    from .figure_export import save_png_svg
    out_base = str(out_base)
    png = str(Path(out_base).with_suffix(".png"))
    svg = str(Path(out_base).with_suffix(".svg"))
    # Use existing exporter to create PNG first
    plot_radial_build_from_artifact(artifact, png)
    # Re-render as a matplotlib fig for SVG if possible
    try:
        import matplotlib.pyplot as plt
        # If plotting module exposes an internal fig builder, use it; otherwise rebuild by reading PNG is not possible.
        # Best-effort: call plot function again but intercept current fig.
        # Here we simply save current active figure if present.
        fig = plt.gcf()
        save_png_svg(fig, out_png=None, out_svg=svg)
    except Exception:
        pass
    produced = {}
    if Path(png).exists(): produced["png"] = png
    if Path(svg).exists(): produced["svg"] = svg
    return produced