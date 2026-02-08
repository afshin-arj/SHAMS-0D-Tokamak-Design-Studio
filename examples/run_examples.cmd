@echo off
REM v83 Examples runner (Windows)
REM Run from repo root: SHAMS_FUSION_X_v83\

python -m tools.studies.feasible_scan --base examples\base_point.json --var R0 --lo 2.0 --hi 5.0 --n 31 --outdir out_feasible_scan_R0 --topk 5
python -m tools.studies.feasible_pareto --feasible-scan-json out_feasible_scan_R0\feasible_scan.json --objectives R0:min
python -m tools.studies.process_handoff --feasible-scan-json out_feasible_scan_R0\feasible_scan.json --out shams_process_handoff_R0.json

echo Done.
pause

