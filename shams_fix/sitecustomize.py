"""SHAMS global Python runtime hygiene.

Python automatically imports `sitecustomize` if it is importable on sys.path.
We use it to enforce the permanent repository hygiene rule:

  - Do not write bytecode caches (__pycache__ / *.pyc)

This is UI/CLI safe and does not affect physics truth. It only avoids creating
unwanted files in the working tree.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import sys


sys.dont_write_bytecode = True
