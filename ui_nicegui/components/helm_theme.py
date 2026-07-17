"""Dark-drawer theme for Helm Console — readable text on slate background."""
from __future__ import annotations

from nicegui import ui

HELM_DRAWER_CLASS = "helm-drawer shams-helm-drawer"

_HELM_CSS = """
:root {
  --shams-drawer-width: 340px;
}
body.shams-drawer-resizing {
  cursor: col-resize !important;
  user-select: none !important;
}
body.shams-drawer-resizing * {
  cursor: col-resize !important;
}
.shams-left-drawer {
  width: var(--shams-drawer-width) !important;
  max-width: var(--shams-drawer-width) !important;
}
.shams-drawer-resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 10px;
  height: 100%;
  cursor: col-resize;
  z-index: 3200;
  background: transparent;
  touch-action: none;
  pointer-events: auto;
}
.shams-drawer-resize-handle:hover,
body.shams-drawer-resizing .shams-drawer-resize-handle {
  background: rgba(96, 165, 250, 0.35);
}
.shams-drawer-body {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
}
.shams-helm-scroll {
  width: 100%;
  max-width: var(--shams-drawer-width);
}
.shams-helm-drawer {
  color: #e2e8f0;
}
.shams-helm-drawer .text-h6,
.shams-helm-drawer .text-subtitle2,
.shams-helm-drawer .text-body2,
.shams-helm-drawer .text-weight-bold,
.shams-helm-drawer .q-expansion-item__label,
.shams-helm-drawer .q-item__label,
.shams-helm-drawer label,
.shams-helm-drawer p,
.shams-helm-drawer li,
.shams-helm-drawer .q-markdown {
  color: #f1f5f9 !important;
}
.shams-helm-drawer .text-caption,
.shams-helm-drawer .text-grey,
.shams-helm-drawer .text-grey-4,
.shams-helm-drawer .text-grey-5 {
  color: #94a3b8 !important;
}
.shams-helm-drawer .text-orange {
  color: #fdba74 !important;
}
.shams-helm-drawer .text-green {
  color: #86efac !important;
}
.shams-helm-drawer .text-red {
  color: #fca5a5 !important;
}
.shams-helm-drawer .q-btn--flat {
  color: #e2e8f0 !important;
}
.shams-helm-drawer .q-btn--flat.bg-slate-700 {
  color: #ffffff !important;
  background: #334155 !important;
}
.shams-helm-drawer .q-field__label,
.shams-helm-drawer .q-field__native,
.shams-helm-drawer .q-field__input,
.shams-helm-drawer .q-field__prefix,
.shams-helm-drawer .q-field__suffix {
  color: #f8fafc !important;
}
.shams-helm-drawer .q-field--outlined .q-field__control:before {
  border-color: #64748b !important;
}
.shams-helm-drawer .q-field--outlined .q-field__control {
  background: rgba(15, 23, 42, 0.35);
}
.shams-helm-drawer .q-tab {
  color: #94a3b8 !important;
}
.shams-helm-drawer .q-tab--active {
  color: #f8fafc !important;
}
.shams-helm-drawer .q-tabs__content {
  border-color: #475569 !important;
}
.shams-helm-drawer .q-separator {
  background: #475569 !important;
}
.shams-helm-drawer .q-banner {
  background: #1e3a5f !important;
  color: #e0f2fe !important;
}
.shams-helm-drawer .q-textarea .q-field__native,
.shams-helm-drawer .q-textarea .q-field__input {
  color: #0f172a !important;
  background: #f8fafc !important;
}
.shams-helm-drawer .q-checkbox__label {
  color: #e2e8f0 !important;
}
.shams-helm-drawer .q-toggle__label {
  color: #e2e8f0 !important;
}
.shams-helm-drawer pre,
.shams-helm-drawer code {
  color: #e2e8f0 !important;
  background: #0f172a !important;
}
.shams-helm-drawer .helm-info-banner {
  background: #1e3a5f;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  padding: 8px 10px;
  color: #e0f2fe;
  font-size: 12px;
}
.shams-helm-drawer .helm-phase-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  min-width: 26px !important;
  min-height: 26px !important;
  padding: 0 !important;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: #334155;
  color: #94a3b8;
  border: 1px solid #475569;
  cursor: pointer;
}
.shams-helm-drawer .helm-phase-pill:hover {
  border-color: #60a5fa;
  color: #e2e8f0;
}
.shams-helm-drawer .helm-phase-active {
  background: #2563eb;
  color: #fff;
  border-color: #60a5fa;
}
.shams-helm-drawer .helm-phase-done {
  background: #14532d;
  color: #86efac;
  border-color: #22c55e;
}
.shams-helm-drawer .helm-deck-hint {
  background: rgba(15, 23, 42, 0.55);
  border-left: 3px solid #3b82f6;
  padding: 6px 8px;
  border-radius: 4px;
}
.shams-helm-drawer .helm-deck-btn-active {
  background: #334155 !important;
  color: #ffffff !important;
  font-weight: 600;
}
.shams-helm-drawer .helm-nav-group .q-expansion-item__container {
  border: 1px solid #475569;
  border-radius: 6px;
  margin-bottom: 4px;
}

/* --- Drawer clipping: keep sidebar content inside the left panel --- */
.shams-left-drawer,
.shams-left-drawer .q-drawer__content,
.shams-helm-scroll,
.shams-helm-scroll .scroll,
.shams-helm-scroll .q-scrollarea__container,
.shams-helm-scroll .q-scrollarea__content,
.shams-helm-inner {
  overflow-x: hidden !important;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.shams-left-drawer {
  z-index: 3000;
}
.shams-helm-drawer .q-expansion-item,
.shams-helm-drawer .q-expansion-item__container,
.shams-helm-drawer .q-expansion-item__content {
  max-width: 100%;
  overflow-x: hidden;
}
.shams-helm-drawer .q-expansion-item__content-inner {
  max-width: 100%;
  overflow-x: hidden;
  padding-right: 4px;
}
.shams-helm-drawer .q-field,
.shams-helm-drawer .q-btn,
.shams-helm-drawer .q-select,
.shams-helm-drawer .q-item,
.shams-helm-drawer .q-markdown,
.shams-helm-drawer .helm-deck-hint {
  max-width: 100%;
  min-width: 0;
}
.shams-helm-drawer pre,
.shams-helm-drawer code,
.shams-helm-drawer .q-field__native,
.shams-helm-drawer .q-field__input {
  max-width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
.shams-helm-drawer .q-btn--flat {
  text-align: left;
  justify-content: flex-start;
}
"""


def inject_helm_drawer_theme() -> None:
    """Register Helm drawer CSS once per app."""
    ui.add_css(_HELM_CSS)


def helm_dark_props(*extra: str) -> str:
    """Quasar props for readable controls on dark drawer."""
    parts = ["dark", "outlined", "dense"]
    for x in extra:
        if x:
            parts.append(str(x))
    return " ".join(parts)
