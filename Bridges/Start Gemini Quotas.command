#!/bin/zsh
# Open yourself in Terminal; Google sign-in and terminal output remain private.
set -eu
cd -- "${0:A:h}"
exec /usr/bin/python3 ./gemini_quota.py \
  --state "$HOME/Library/Application Support/ControlTowerPrivate/gemini-adapter" \
  --output "$HOME/Library/Application Support/ControlTowerPrivate/quota-feed"
