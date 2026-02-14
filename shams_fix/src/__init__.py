"""SHAMS source package.

This file makes `src` an importable Python package so that lightweight proxy
modules at the repository root (e.g. `physics/*`, `solvers/*`) can re-export
implementations from `src.*` reliably.

It is intentionally minimal.
"""
