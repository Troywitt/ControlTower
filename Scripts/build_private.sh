#!/bin/bash
# Build only. Never installs, launches, kills processes or reads provider credentials.
set -euo pipefail
cd "$(dirname "$0")/.."
export CLANG_MODULE_CACHE_PATH="${TMPDIR:-/tmp}/controltower-clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="${TMPDIR:-/tmp}/controltower-swift-cache"
swift build -c release --disable-sandbox
BIN_DIR=$(swift build -c release --show-bin-path --disable-sandbox)
mkdir -p .build/artifacts
ARTIFACT_DIR=$(mktemp -d "$PWD/.build/artifacts/review.XXXXXX")
APP="$ARTIFACT_DIR/ControlTower Private.app"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN_DIR/ControlTowerLocal" "$APP/Contents/MacOS/ControlTowerLocal"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.bodie.controltower.private</string>
<key>CFBundleName</key><string>ControlTower Private</string>
<key>CFBundleExecutable</key><string>ControlTowerLocal</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSHumanReadableCopyright</key><string>MIT. Original ControlTower contributors; private fork contributors.</string>
</dict></plist>
PLIST
SOURCE_SHA=$(git rev-parse --verify HEAD)
/usr/libexec/PlistBuddy -c "Add :CTSourceRevision string $SOURCE_SHA" "$APP/Contents/Info.plist"
codesign --force --sign - --options runtime --entitlements ControlTower.entitlements "$APP"
codesign --verify --strict "$APP"
codesign -d --entitlements :- "$APP" > "$ARTIFACT_DIR/entitlements.plist"
python3 Scripts/security_gate.py --app "$APP" --entitlements "$ARTIFACT_DIR/entitlements.plist"
printf '%s\n' "$APP" > .build/artifacts/latest-path.txt
printf 'PASS: review build prepared (not installed or launched): %s\n' "$APP"
