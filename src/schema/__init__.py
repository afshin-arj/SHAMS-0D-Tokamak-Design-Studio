"""SHAMS data schema (L0).

Pure data containers shared across the codebase: input specifications and
constraint records, with no domain/physics logic and no dependencies on other
SHAMS packages. Extracted in Tier-3 Batch B1 to separate schema from logic.

Public members are re-exported from their original locations (e.g.
``models.inputs`` / ``constraints.system``) via thin shims for backward
compatibility, so existing imports keep working unchanged.
"""
