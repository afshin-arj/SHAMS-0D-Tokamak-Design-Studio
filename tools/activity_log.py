from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _now_iso(tz_name: str) -> str:
    # Always include timezone offset if possible
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
            return datetime.now(tz).isoformat(timespec="milliseconds")
        except Exception:
            pass
    # Fallback (naive local time)
    return datetime.now().isoformat(timespec="milliseconds")


@dataclass
class ActivityLogger:
    repo_root: Path
    tz_name: str = "Asia/Tehran"
    filename: str = "activity_log_current.log"
    max_lines_in_memory: int = 5000
    lines: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root)
        runs_dir = self.repo_root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        self._path = runs_dir / self.filename
        # Load existing tail (best-effort)
        try:
            if self._path.exists():
                existing = self._path.read_text(encoding="utf-8", errors="replace").splitlines()
                self.lines = existing[-self.max_lines_in_memory :]
        except Exception:
            # Never block UI
            self.lines = []

    @property
    def path(self) -> Path:
        return self._path

    def clear(self) -> None:
        self.lines = []
        try:
            self._path.write_text("", encoding="utf-8")
        except Exception:
            pass

    def _append(self, line: str) -> None:
        self.lines.append(line)
        if len(self.lines) > self.max_lines_in_memory:
            self.lines = self.lines[-self.max_lines_in_memory :]
        try:
            # Ensure directory exists
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception:
            pass

    def log_event(self, mode: str, action: str, payload: Optional[Dict[str, Any]] = None) -> None:
        rec = {
            "ts": _now_iso(self.tz_name),
            "mode": str(mode),
            "action": str(action),
            "payload": payload or {},
        }
        line = f"{rec['ts']} | {rec['mode']} | {rec['action']} | {json.dumps(rec['payload'], ensure_ascii=False)}"
        self._append(line)

    def log_exception(self, mode: str, action: str, exc: BaseException, payload: Optional[Dict[str, Any]] = None) -> None:
        pl = dict(payload or {})
        pl["exception_type"] = type(exc).__name__
        pl["exception_message"] = str(exc)
        pl["traceback"] = traceback.format_exc()
        self.log_event(mode, action, pl)

    def get_text(self, last_n: int = 200) -> str:
        try:
            n = int(last_n)
        except Exception:
            n = 200
        n = max(0, min(n, self.max_lines_in_memory))
        tail = self.lines[-n:] if n > 0 else self.lines
        return "\n".join(tail)


def get_logger(st, repo_root: Path, tz_name: str = "Asia/Tehran") -> ActivityLogger:
    """Return a singleton ActivityLogger stored in streamlit session_state."""
    if "activity_logger" not in st.session_state:
        st.session_state["activity_logger"] = ActivityLogger(repo_root=Path(repo_root), tz_name=tz_name)
    lg: ActivityLogger = st.session_state["activity_logger"]
    # Keep tz updated if the caller changes it
    try:
        lg.tz_name = tz_name
    except Exception:
        pass
    return lg
