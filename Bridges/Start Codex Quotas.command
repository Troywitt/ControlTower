#!/bin/zsh
# Open this file yourself in Terminal. Sign-in output must remain private.
set -eu
cd -- "${0:A:h}"
exec /usr/bin/python3 ./codex_quota.py \
  --binary /Users/troywitt/.codex/packages/standalone/releases/0.153.4-aarch64-apple-darwin/bin/codex \
  --sha256 b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3 \
  --state "$HOME/Library/Application Support/ControlTowerPrivate/codex-adapter" \
  --output "$HOME/Library/Application Support/ControlTowerPrivate/quota-feed" \
  --login
