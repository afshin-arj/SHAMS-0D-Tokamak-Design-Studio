#!/usr/bin/env bash
set -euo pipefail

# SHAMS / Tokamak 0-D Design Studio — Streamlit UI launcher
# Author: © 2026 Afshin Arjhangmehr

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PY_BIN="${VENV_DIR}/bin/python"

# Prevent __pycache__ creation (repo hygiene law)
export PYTHONDONTWRITEBYTECODE=1

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${PY_BIN}" -m pip install --upgrade pip
"${PY_BIN}" -m pip install -r "${ROOT_DIR}/requirements.txt"

# Hygiene enforcement (caches/pyc) — does not affect physics truth.
"${PY_BIN}" "${ROOT_DIR}/scripts/hygiene_clean.py" --root "${ROOT_DIR}" --report "${ROOT_DIR}/hygiene_clean_report.json" || true

cd "${ROOT_DIR}"
exec "${PY_BIN}" -m streamlit run ui/app.py
