"""Resizable / collapsible Helm drawer — width persistence and drag handle."""
from __future__ import annotations

from nicegui import ui

HELM_DRAWER_WIDTH_DEFAULT = 340
HELM_DRAWER_WIDTH_MIN = 260
HELM_DRAWER_WIDTH_MAX = 560

# Single-line script for ui.run_javascript (must not use add_head_html — raw JS renders as text).
_DRAWER_RESIZE_JS = (
    "(function(){"
    "if(window.__shamsDrawerResizeInit)return;"
    "window.__shamsDrawerResizeInit=true;"
    f"const MIN={HELM_DRAWER_WIDTH_MIN},MAX={HELM_DRAWER_WIDTH_MAX},DEFAULT_W={HELM_DRAWER_WIDTH_DEFAULT};"
    "const KEY='shams_helm_drawer_width';"
    "function clamp(w){return Math.max(MIN,Math.min(MAX,w));}"
    "function applyWidth(w){"
    "const px=clamp(w)+'px';"
    "document.documentElement.style.setProperty('--shams-drawer-width',px);"
    "document.querySelectorAll('.shams-left-drawer').forEach(el=>{el.style.width=px;el.style.maxWidth=px;});"
    "document.querySelectorAll('.shams-helm-scroll').forEach(el=>{el.style.maxWidth=px;});"
    "}"
    "window.shamsApplyDrawerWidth=applyWidth;"
    "let stored=parseInt(localStorage.getItem(KEY)||'',10);"
    "if(!Number.isFinite(stored))stored=DEFAULT_W;"
    "applyWidth(stored);"
    "let dragging=false,startX=0,startW=0;"
    "function onMove(ev){"
    "if(!dragging)return;"
    "applyWidth(startW+(ev.clientX-startX));"
    "ev.preventDefault();"
    "}"
    "function onUp(){"
    "if(!dragging)return;"
    "dragging=false;"
    "document.body.classList.remove('shams-drawer-resizing');"
    "const raw=getComputedStyle(document.documentElement).getPropertyValue('--shams-drawer-width');"
    "const w=parseInt(raw,10);"
    "if(Number.isFinite(w))localStorage.setItem(KEY,String(w));"
    "window.removeEventListener('mousemove',onMove);"
    "window.removeEventListener('mouseup',onUp);"
    "}"
    "document.addEventListener('mousedown',ev=>{"
    "const handle=ev.target.closest('.shams-drawer-resize-handle');"
    "if(!handle)return;"
    "const drawer=document.querySelector('.shams-left-drawer');"
    "if(!drawer||drawer.classList.contains('q-drawer--hidden'))return;"
    "dragging=true;startX=ev.clientX;startW=drawer.getBoundingClientRect().width;"
    "document.body.classList.add('shams-drawer-resizing');"
    "window.addEventListener('mousemove',onMove);"
    "window.addEventListener('mouseup',onUp);"
    "ev.preventDefault();"
    "ev.stopPropagation();"
    "},{capture:true});"
    "})();"
)


def inject_drawer_resize_script() -> None:
    """Run drawer resize logic on the connected client (after DOM is ready)."""
    ui.timer(0.15, lambda: ui.run_javascript(_DRAWER_RESIZE_JS), once=True)


def render_drawer_resize_handle() -> None:
    """Right-edge drag handle — must sit above scroll content."""
    ui.element("div").classes("shams-drawer-resize-handle").props(
        'title="Drag to resize sidebar"'
    )


def toggle_helm_drawer(session) -> None:
    session.helm_drawer_open = not bool(getattr(session, "helm_drawer_open", True))
