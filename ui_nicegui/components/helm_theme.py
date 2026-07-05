"""Dark-drawer theme for Helm Console — readable text on slate background."""
from __future__ import annotations

from nicegui import ui

HELM_DRAWER_CLASS = "helm-drawer shams-helm-drawer"

_HELM_CSS = """
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
