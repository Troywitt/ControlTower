#!/bin/bash
# App-local dependencies only. No provider execution or global installation.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .build/gemini-runtime
cp Bridges/gemini-package-lock.json .build/gemini-runtime/package-lock.json
printf '%s\n' '{"dependencies":{"@google/gemini-cli":"0.60.0"}}' > .build/gemini-runtime/package.json
npm ci --prefix .build/gemini-runtime --ignore-scripts --no-audit --no-fund
python3 -m pip install --target .build/gemini-python --disable-pip-version-check pyte==0.8.2 wcwidth==0.2.13
python3 - <<'PY'
import sys
sys.path.insert(0, 'Bridges')
from gemini_quota import verify_runtime
verify_runtime()
print('PASS: local runtime matches reviewed pins')
PY
