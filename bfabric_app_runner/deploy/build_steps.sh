#!/bin/bash
set -euxo pipefail
TARGET_DIR="${1:-dist}"
TARGET_NAME="${2:-app_runner}"
rm -rf /work/venv
python -m venv /work/venv
source /work/venv/bin/activate
uv pip install .
uv pip install pyinstaller
pyinstaller -y --onedir --name "${TARGET_NAME}" --distpath "${TARGET_DIR}" src/bfabric_app_runner/cli/__main__.py
deactivate
