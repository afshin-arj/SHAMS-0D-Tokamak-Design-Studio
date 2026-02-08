#!/usr/bin/env python
from __future__ import annotations

import json
import getpass
import time
import hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    diff = repo / 'benchmarks' / 'last_diff_report.json'
    if not diff.exists():
        print('Missing benchmarks/last_diff_report.json. Run python benchmarks/run.py first.')
        return 2
    diff_hash = sha256_file(diff)
    user = getpass.getuser()
    approval = {
        'type': 'breaking_change_approval',
        'created_unix': time.time(),
        'user': user,
        'diff_report_path': str(diff.as_posix()),
        'diff_report_sha256': diff_hash,
        'statement': 'I acknowledge the BREAKING structural diffs and approve updating golden artifacts / schema.',
    }
    # Self-hash (tamper-evident)
    blob = json.dumps(approval, sort_keys=True).encode('utf-8')
    approval['approval_sha256'] = hashlib.sha256(blob).hexdigest()
    outp = repo / 'benchmarks' / 'breaking_approval.json'
    outp.write_text(json.dumps(approval, indent=2, sort_keys=True), encoding='utf-8')
    print(f'Wrote {outp} with diff_report_sha256={diff_hash}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
