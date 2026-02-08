from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

class SQLiteIndex:
    """Tiny optional index for study case metadata (Windows-friendly, stdlib only)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self._init()

    def _init(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS cases (
            case_id INTEGER PRIMARY KEY,
            ok INTEGER,
            iters INTEGER,
            message TEXT,
            artifact_path TEXT
        )""")
        self.conn.commit()

    def add_case(self, case_id: int, ok: bool, iters: int, message: str, artifact_path: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO cases(case_id, ok, iters, message, artifact_path) VALUES (?,?,?,?,?)",
            (case_id, int(ok), int(iters), message, artifact_path),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
