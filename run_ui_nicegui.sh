#!/usr/bin/env bash
# Run SHAMS NiceGUI UI (Linux/macOS)
set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR=".venv"
PY_EXE="$VENV_DIR/bin/python"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found"
  exit 1
fi

if [[ ! -x "$PY_EXE" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

"$PY_EXE" -m pip install --upgrade pip
"$PY_EXE" -m pip install -r requirements.txt
if [[ -f scripts/hygiene_clean.py ]]; then
  "$PY_EXE" scripts/hygiene_clean.py --root "$(pwd)" --report hygiene_clean_report.json || true
fi

echo "Starting SHAMS NiceGUI (http://127.0.0.1:8080; browser opens automatically)..."
exec "$PY_EXE" -u ui_nicegui/launch.py
