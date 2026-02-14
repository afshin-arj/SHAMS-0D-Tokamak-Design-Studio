import subprocess
import sys
import os

def test_verification_harness():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    cmd = [sys.executable, os.path.join(repo_root, "verification", "run_verification.py")]
    p = subprocess.run(cmd, cwd=repo_root)
    assert p.returncode == 0
