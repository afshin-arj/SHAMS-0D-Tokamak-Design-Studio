import json
import subprocess
from pathlib import Path
import sys

def test_benchmarks_write_diff_report():
    root = Path(__file__).resolve().parent.parent
    bench = root / "benchmarks"
    diff_path = bench / "last_diff_report.json"
    if diff_path.exists():
        diff_path.unlink()

    cmd = [sys.executable, str(bench / "run.py"), "--write-diff"]
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    assert proc.returncode in (0,1)
    assert diff_path.exists(), f"Expected diff report at {diff_path}. stdout={proc.stdout} stderr={proc.stderr}"
    rep = json.loads(diff_path.read_text(encoding="utf-8"))
    assert "rows" in rep and isinstance(rep["rows"], list)
    assert "n_failed" in rep
