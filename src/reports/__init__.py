"""SHAMS report generators (additive; L0-untouched).

Independence Phase 4 reports live here. Generators assemble evidence only —
they never modify Evaluator / hot_ion truth.
"""

from .process_retirement_report import (
    REPORT_SCHEMA,
    build_process_retirement_report,
    render_process_retirement_markdown,
    write_process_retirement_report,
)

__all__ = [
    "REPORT_SCHEMA",
    "build_process_retirement_report",
    "render_process_retirement_markdown",
    "write_process_retirement_report",
]
