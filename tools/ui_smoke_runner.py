from __future__ import annotations
"""UI Smoke Runner (v126)

Headless smoke checks for SHAMS UI modules without requiring a Streamlit server.
It monkeypatches a minimal 'streamlit' stub to import and execute panel functions.

This is a smoke test (import/render exceptions), not exhaustive integration testing.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
import json, time, sys, traceback, types, io

class _AttrDict(dict):
    """Dict that also supports attribute-style access (like Streamlit session_state)."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v

@dataclass
class PanelResult:
    name: str
    ok: bool
    error: Optional[str] = None
    traceback: Optional[str] = None

class _NullCtx:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class StreamlitStub:
    """A forgiving Streamlit stub implementing commonly used APIs as no-ops."""

    def __init__(self, button_truth: Optional[Dict[str, bool]] = None):
        self.session_state = _AttrDict()
        self._button_truth = button_truth or {}
        self.sidebar = self

    # allow `with st.sidebar:` and `with col:`
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

    # config / cache decorators
    def set_page_config(self, *a, **k): return None
    def cache_data(self, *a, **k):
        def deco(fn): return fn
        return deco
    def cache_resource(self, *a, **k):
        def deco(fn): return fn
        return deco

    # basic writes
    def title(self, *a, **k): return None
    def header(self, *a, **k): return None
    def subheader(self, *a, **k): return None
    def caption(self, *a, **k): return None
    def markdown(self, *a, **k): return None
    def write(self, *a, **k): return None
    def text(self, *a, **k): return None
    def code(self, *a, **k): return None
    def json(self, *a, **k): return None
    def dataframe(self, *a, **k): return None
    def table(self, *a, **k): return None
    def info(self, *a, **k): return None
    def warning(self, *a, **k): return None
    def error(self, *a, **k): return None
    def success(self, *a, **k): return None
    def divider(self, *a, **k): return None
    def stop(self):
        # In Streamlit, this raises StopException; here we just no-op.
        return None

    # layout / containers
    def columns(self, n, *a, **k):
        # Streamlit accepts int or a list of ratios
        if isinstance(n, (list, tuple)):
            n = len(n)
        return [self for _ in range(int(n))]
    def expander(self, *a, **k):
        return _NullCtx()
    def container(self, *a, **k):
        return _NullCtx()
    def spinner(self, *a, **k):
        return _NullCtx()
    def tabs(self, labels, *a, **k):
        return [self for _ in (labels or [])]
    def form(self, *a, **k):
        return _NullCtx()
    def form_submit_button(self, *a, **k):
        return False

    # small display helpers
    def metric(self, *a, **k): return None
    def progress(self, *a, **k): return None
    def pyplot(self, *a, **k): return None
    def image(self, *a, **k): return None
    def plotly_chart(self, *a, **k): return None

    # inputs
    def selectbox(self, label: str, options: List[Any], index: int = 0, key: Optional[str] = None, **k):
        if not options:
            return None
        try:
            return options[index]
        except Exception:
            return options[0]
    def multiselect(self, label: str, options: List[Any], default=None, key: Optional[str] = None, **k):
        if default is None:
            return []
        return list(default)
    def toggle(self, label: str, value: bool = False, key: Optional[str] = None, **k):
        return bool(value)
    def checkbox(self, label: str, value: bool = False, key: Optional[str] = None, **k):
        return bool(value)
    def radio(self, label: str, options: List[Any], index: int = 0, key: Optional[str] = None, **k):
        return self.selectbox(label, options, index=index, key=key)
    def number_input(self, label: str, value: float = 0.0, key: Optional[str] = None, **k):
        return value
    def slider(self, label: str, min_value=None, max_value=None, value=None, step=None, key: Optional[str] = None, **k):
        return value
    def text_input(self, label: str, value: str = "", key: Optional[str] = None, **k):
        return value
    def text_area(self, label: str, value: str = "", key: Optional[str] = None, **k):
        return value
    def file_uploader(self, *a, **k):
        # Provide a minimal JSON payload when uploader expects json, so app import can proceed.
        t = k.get('type') or []
        if isinstance(t, (list, tuple)) and 'json' in t:
            return io.StringIO('{"points": []}')
        return None
    def download_button(self, *a, **k): return None

    # button: scenario-controlled
    def button(self, label: str, key: Optional[str] = None, **k):
        if key and key in self._button_truth:
            return bool(self._button_truth[key])
        return False

    def __getattr__(self, name: str):
        # fallback for unimplemented APIs: return no-op callable
        def _noop(*a, **k):
            return None
        return _noop

def _install_streamlit_stub(stub: StreamlitStub) -> None:
    mod = types.SimpleNamespace()
    for name in dir(stub):
        if name.startswith("_"):
            continue
        setattr(mod, name, getattr(stub, name))
    mod.session_state = stub.session_state
    mod.sidebar = stub.sidebar
    sys.modules["streamlit"] = mod  # type: ignore

def discover_panels(app_module: Any) -> List[str]:
    out: List[str] = []
    for name, val in vars(app_module).items():
        if callable(val) and name.startswith("_v") and name.endswith("_panel"):
            out.append(name)
    return sorted(out)

def run_smoke(*, outdir: str = "out_ui_smoke_v126", scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
    scenarios = scenarios or ["render_all", "paper_pack"]
    outp = Path(outdir); outp.mkdir(parents=True, exist_ok=True)

    button_truth: Dict[str, bool] = {}
    if "paper_pack" in scenarios:
        button_truth["v125_run"] = True

    stub = StreamlitStub(button_truth=button_truth)
    _install_streamlit_stub(stub)

    started = time.time()
    meta: Dict[str, Any] = {
        "kind": "shams_ui_smoke_report",
        "version": "v126",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenarios": scenarios,
        "results": [],
        "notes": [],
    }

    try:
        from ui import app as ui_app  # type: ignore
    except Exception as e:
        tb = traceback.format_exc()
        meta["results"].append({"name": "IMPORT_ui.app", "ok": False, "error": repr(e), "traceback": tb})
        (outp / "ui_smoke_report.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
        (outp / "UI_SMOKE_REPORT.md").write_text(f"# UI Smoke Report (v126)\n\nIMPORT FAILED\n\n```\n{tb}\n```\n", encoding="utf-8")
        return meta

    panels = discover_panels(ui_app)
    meta["panels_discovered"] = panels

    def _run_panel(fname: str) -> PanelResult:
        fn = getattr(ui_app, fname)
        try:
            fn()
            return PanelResult(fname, True)
        except Exception as e:
            return PanelResult(fname, False, error=repr(e), traceback=traceback.format_exc())

    if "render_all" in scenarios:
        for p in panels:
            r = _run_panel(p)
            meta["results"].append({"name": r.name, "ok": r.ok, "error": r.error, "traceback": r.traceback})

    if "paper_pack" in scenarios and "_v125_paper_pack_panel" in panels and "render_all" not in scenarios:
        r = _run_panel("_v125_paper_pack_panel")
        meta["results"].append({"name": r.name, "ok": r.ok, "error": r.error, "traceback": r.traceback})

    elapsed = time.time() - started
    meta["elapsed_s"] = elapsed

    ok_n = sum(1 for r in meta["results"] if r.get("ok"))
    bad = [r for r in meta["results"] if not r.get("ok")]
    meta["summary"] = {"total": len(meta["results"]), "ok": ok_n, "failed": len(bad)}

    (outp / "ui_smoke_report.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    md = ["# UI Smoke Report (v126)", ""]
    md.append(f"Generated UTC: {meta['created_utc']}")
    md.append(f"Scenarios: {', '.join(scenarios)}")
    md.append(f"Elapsed: {elapsed:.2f} s")
    md.append("")
    md.append(f"## Summary\n- Total: {meta['summary']['total']}\n- OK: {meta['summary']['ok']}\n- Failed: {meta['summary']['failed']}")
    if bad:
        md.append("\n## Failures")
        for r in bad[:25]:
            md.append(f"### {r['name']}\n- Error: {r.get('error')}\n\n```\n{(r.get('traceback') or '')[:4000]}\n```\n")
    else:
        md.append("\n✅ No failures detected in smoke scenarios.")

    (outp / "UI_SMOKE_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return meta
