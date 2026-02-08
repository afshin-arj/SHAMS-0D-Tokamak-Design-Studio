# Operating envelope (multi-point)

PROCESS users often require that constraints hold across multiple operating points.
SHAMS provides a lightweight envelope generator (startup / nominal / EoL) and evaluates the worst constraint.

- Generator: `src/envelope/points.py`
- Enable via input: `enable_envelope: true`

CLI:
- `python tools/envelope_check.py --base benchmarks/DEFAULT_BASE.json`

The envelope report includes:
- worst constraint residual across points
- which point was limiting
- feasibility probability when combined with Monte-Carlo
