"""System Suite overlay status helpers for NiceGUI."""

from __future__ import annotations

from typing import Any, Dict, List

from nicegui import ui


def overlay_status_rows(out: dict) -> tuple[list[dict], list[str]]:
    if not isinstance(out, dict):
        return [], []
    errors = [
        {"key": k, "message": str(out[k])}
        for k in sorted(out)
        if k.endswith("_error") and out.get(k)
    ]
    warnings = [str(w) for w in (out.get("_authority_warnings") or [])]
    return errors, warnings


def render_overlay_status_panel(out: dict) -> None:
    errors, warnings = overlay_status_rows(out)
    if not errors and not warnings:
        return
    if errors:
        ui.badge(f"{len(errors)} overlay error(s)", color="red").props("outline q-mb-xs")
    elif warnings:
        ui.badge(f"{len(warnings)} authority warning(s)", color="orange").props("outline q-mb-xs")
    with ui.expansion("Overlay authority status", icon="warning").classes("w-full q-mb-sm"):
        if errors:
            ui.label("Overlay errors").classes("text-subtitle2 text-negative")
            for row in errors:
                ui.label(f"{row['key']}: {row['message']}").classes("text-caption text-negative")
        if warnings:
            ui.label("Authority warnings").classes("text-subtitle2 text-orange q-mt-sm")
            for w in warnings:
                ui.label(w).classes("text-caption text-orange")


def stamp_label(full_sha: str, *, prefix: str = "Overlay stamp") -> None:
    sha = str(full_sha or "")
    if not sha:
        return
    ui.label(f"{prefix}: {sha[:12]}…").classes("text-caption")
    with ui.expansion("Full overlay stamp", icon="fingerprint").classes("w-full"):
        ui.code(sha, language="text")
