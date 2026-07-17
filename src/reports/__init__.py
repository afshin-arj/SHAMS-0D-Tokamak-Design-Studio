"""SHAMS report generators (additive; L0-untouched).

Independence Phase 4 reports live here. Generators assemble evidence only —
they never modify Evaluator / hot_ion truth.
"""

from .cite_shams_handoff_pack import (
    PACK_SCHEMA as CITE_SHAMS_HANDOFF_SCHEMA,
    build_cite_shams_handoff_pack,
    write_cite_shams_handoff_pack,
)
from .process_retirement_report import (
    REPORT_SCHEMA,
    build_process_retirement_report,
    render_process_retirement_markdown,
    write_process_retirement_report,
)

__all__ = [
    "REPORT_SCHEMA",
    "CITE_SHAMS_HANDOFF_SCHEMA",
    "build_process_retirement_report",
    "render_process_retirement_markdown",
    "write_process_retirement_report",
    "build_cite_shams_handoff_pack",
    "write_cite_shams_handoff_pack",
]
