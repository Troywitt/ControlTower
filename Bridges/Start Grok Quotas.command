#!/bin/zsh
# Run only in your private Terminal; sign-in and provider output stay there.
set -eu
cd -- "${0:A:h}"
exec /usr/bin/python3 ./grok_quota.py \
  --state "$HOME/Library/Application Support/ControlTowerPrivate/grok-adapter" \
  --output "$HOME/Library/Application Support/ControlTowerPrivate/quota-feed"
