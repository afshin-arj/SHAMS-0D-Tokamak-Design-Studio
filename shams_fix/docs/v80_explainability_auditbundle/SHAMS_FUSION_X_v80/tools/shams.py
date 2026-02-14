#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make repo-root imports work when running `python tools/shams.py ...`.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


# NOTE: imports are intentionally lazy inside command handlers so the CLI
# remains usable even if optional tools/modules are not loaded.


def _cmd_study_run(args: argparse.Namespace) -> int:
    from tools.study_runner import main as run_study_main
    sys.argv = ['study_runner.py', args.spec, '--out', args.out, '--label-prefix', args.label_prefix]
    return int(run_study_main() or 0)


def _cmd_deck_run(args: argparse.Namespace) -> int:
    from tools.run_case_deck import main as run_case_deck_main
    sys.argv = ['run_case_deck.py', args.deck, '--out', args.out]
    return int(run_case_deck_main() or 0)

def _cmd_artifact_summarize(args: argparse.Namespace) -> int:
    # artifact_index already summarizes artifacts into sqlite/json indexes; for a single file we do a lightweight print
    import json
    p = Path(args.artifact)
    data = json.loads(p.read_text(encoding='utf-8'))
    print(f"Artifact: {p}")
    prov = data.get('provenance', {}) or {}
    print(f"  created_unix: {prov.get('created_unix','')}")
    print(f"  git_commit: {prov.get('git_commit','')}")
    c = data.get('constraints', []) or []
    n_fail = sum(1 for x in c if not x.get('passed', True))
    print(f"  constraints: {len(c)} (fails={n_fail})")
    out = data.get('outputs', {}) or {}
    for k in ['Q_DT_eqv','H98','Pfus_DT_adj_MW','q_div_MW_m2','TBR','P_net_e_MW','COE_proxy_USD_per_MWh']:
        if k in out:
            print(f"  {k}: {out.get(k)}")
    return 0

def _cmd_artifact_diff(args: argparse.Namespace) -> int:
    # Severity-gated structural diff
    import json
    from shams_io.structural_diff import structural_diff, classify_severity
    a = json.loads(Path(args.old).read_text(encoding='utf-8'))
    b = json.loads(Path(args.new).read_text(encoding='utf-8'))
    rep = structural_diff(a, b)
    sev = classify_severity(rep)
    print(json.dumps({'severity': sev, 'diff': rep}, indent=2))
    if args.fail_on_breaking and (sev.get('level') == 'breaking'):
        return 2
    return 0

def _cmd_report_build(args: argparse.Namespace) -> int:
    # wraps plot_shams_summary.py
    from tools.plot_shams_summary import main as plot_summary_main
    sys.argv = ['plot_shams_summary.py', '--file', args.artifact, '--out', args.out]
    return int(plot_summary_main() or 0)


def _cmd_envelope(args: argparse.Namespace) -> int:
    from tools.envelope_check import main as envelope_check_main
    sys.argv = ['envelope_check.py', '--spec', args.spec] if False else sys.argv
    return int(envelope_check_main() or 0)


def _cmd_scenario(args: argparse.Namespace) -> int:
    from tools.run_scenarios import main as run_scenarios_main
    # run_scenarios.py expects --point/--scenarios/--outdir; keep this command as a passthrough
    # for backward compatibility with existing workflows.
    return int(run_scenarios_main() or 0)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='shams', description='SHAMS–FUSION-X utilities (artifact-native).')
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('artifact', help='Artifact utilities')
    asub = a.add_subparsers(dest='artifact_cmd', required=True)

    s = asub.add_parser('summarize', help='Summarize a run artifact JSON')
    s.add_argument('artifact')
    s.set_defaults(func=_cmd_artifact_summarize)

    d = asub.add_parser('diff', help='Structural diff (severity-gated)')
    d.add_argument('old')
    d.add_argument('new')
    d.add_argument('--fail-on-breaking', action='store_true')
    d.set_defaults(func=_cmd_artifact_diff)

    r = sub.add_parser('report', help='Report utilities')
    rsub = r.add_subparsers(dest='report_cmd', required=True)
    rb = rsub.add_parser('build', help='Build decision-grade PDF report from artifact')
    rb.add_argument('artifact')
    rb.add_argument('--out', default='shams_summary.pdf')
    rb.set_defaults(func=_cmd_report_build)

    e = sub.add_parser('envelope', help='Operational envelope utilities')
    e.add_argument('spec', help='Envelope spec JSON/YAML')
    e.set_defaults(func=lambda args: int(__import__('tools.envelope_check', fromlist=['main']).main() or 0))

    sc = sub.add_parser('scenario', help='Scenario utilities')
    sc.add_argument('spec', help='Scenario spec JSON/YAML')
    sc.set_defaults(func=lambda args: int(__import__('tools.run_scenarios', fromlist=['main']).main() or 0))

    st = sub.add_parser('study', help='Study utilities')
    st.add_argument('spec', help='Study spec JSON/YAML')
    st.add_argument('--out', default='study_out', help='Output directory')
    st.add_argument('--label-prefix', default='', help='Prefix for per-case labels')
    st.set_defaults(func=_cmd_study_run)

    dk = sub.add_parser('deck', help='Case deck utilities')
    dk.add_argument('deck', help='Case deck YAML/JSON')
    dk.add_argument('--out', default='case_out', help='Output directory')
    dk.set_defaults(func=_cmd_deck_run)

    return p

def main(argv=None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return int(args.func(args))

if __name__ == '__main__':
    raise SystemExit(main())
