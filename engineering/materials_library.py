"""Back-compat re-export for materials library.

The canonical implementation lives under src.engineering.materials_library.
This shim keeps legacy imports (engineering.materials_library) working.
"""

from src.engineering.materials_library import *  # noqa: F401,F403
