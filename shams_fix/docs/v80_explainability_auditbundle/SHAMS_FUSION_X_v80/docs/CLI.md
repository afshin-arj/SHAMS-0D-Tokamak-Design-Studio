# SHAMS CLI utilities

Windows:
- `run_cli.cmd --help`

Cross-platform:
- `python tools/shams.py --help`

Key commands:
- `python tools/shams.py artifact summarize path/to/artifact.json`
- `python tools/shams.py artifact diff old.json new.json --fail-on-breaking`
- `python tools/shams.py report build artifact.json --out shams_summary.pdf`
