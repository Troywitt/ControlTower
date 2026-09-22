#!/bin/zsh
# User-started dashboard only. Never launches providers or signs in.
set -eu
cd -- "${0:A:h}/.."
app="$PWD/.build/artifacts/review.RlknAq/ControlTower Private.app"
expected="ae19c16b49bca53498937c17c711a5763771bfeb27787ce03de0975db0d58c94"
actual=$(/usr/bin/shasum -a 256 "$app/Contents/MacOS/ControlTowerLocal" | /usr/bin/awk '{print $1}')
if [[ "$actual" != "$expected" ]]; then
  print -u2 'Reviewed dashboard changed or is missing. Rebuild and review before opening.'
  exit 1
fi
/usr/bin/codesign --verify --strict "$app"
/usr/bin/python3 Scripts/security_gate.py --app "$app" --entitlements .build/artifacts/review.RlknAq/entitlements.plist
if [[ "${1:-}" == "--check" ]]; then
  print 'PASS: reviewed dashboard launcher verified; no app opened.'
elif [[ $# -eq 0 ]]; then
  /usr/bin/open "$app"
else
  print -u2 'Usage: Open ControlTower Private.command [--check]'
  exit 2
fi
