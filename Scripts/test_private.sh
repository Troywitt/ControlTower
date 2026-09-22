#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CLANG_MODULE_CACHE_PATH="${TMPDIR:-/tmp}/controltower-clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="${TMPDIR:-/tmp}/controltower-swift-cache"
SWIFT_BIN=$(xcrun --find swift)
TESTING_PLUGIN="$(dirname "$SWIFT_BIN")/../lib/swift/host/plugins/testing/libTestingMacros.dylib"
EXTRA=()
# Some CLT SwiftPM builds omit automatic discovery of their bundled Testing macro.
if [ -f "$TESTING_PLUGIN" ]; then
  EXTRA=(-Xswiftc -load-plugin-library -Xswiftc "$TESTING_PLUGIN")
fi
swift test --disable-sandbox "${EXTRA[@]}"
python3 -m unittest discover -s Tests/BridgeTests -v
python3 Scripts/security_gate.py
