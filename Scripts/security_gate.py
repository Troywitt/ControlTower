#!/usr/bin/env python3
"""Deterministic build boundary check; defense-in-depth, not a malware proof."""
import argparse, pathlib, plistlib, re, subprocess
root = pathlib.Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--app'); p.add_argument('--entitlements')
a = p.parse_args()
manifest = (root/'Package.swift').read_text()
assert 'dependencies: []' in manifest
assert '.package(' not in manifest and 'Sparkle' not in manifest
assert re.findall(r'\.target\(name: "([^"]+)"', manifest) == ['LocalUsageCore']
assert re.findall(r'\.executableTarget\(name: "([^"]+)"', manifest) == ['ControlTowerLocal']
active = list((root/'Sources/LocalUsageCore').glob('*.swift')) + list((root/'Sources/ControlTowerLocal').glob('*.swift'))
text = '\n'.join(f.read_text() for f in active)
for forbidden in ['Process(', 'ProcessInfo.', 'URLSession.shared', 'BrowserCookie', 'Claude Code-credentials', 'auth.json', '.credentials.json', 'SecItemCopyMatching']:
    matches = [f for f in active if forbidden in f.read_text()]
    if forbidden == 'SecItemCopyMatching':
        assert [f.name for f in matches] == ['KeychainVault.swift']
    else:
        assert not matches, (forbidden, matches)
assert not re.search(r'\b(print|debugPrint|NSLog|os_log)\s*\(|\blogger\.', text)
urls = set(re.findall(r'https?://[^"\s]+', text))
assert urls == {'https://api.anthropic.com/api/oauth/usage','https://chatgpt.com/backend-api/wham/usage','https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota'}, urls
expected = {'com.apple.security.app-sandbox': True, 'com.apple.security.files.user-selected.read-only': True, 'com.apple.security.network.client': True}
assert plistlib.loads((root/'ControlTower.entitlements').read_bytes()) == expected
if a.app:
    app = pathlib.Path(a.app)
    assert plistlib.loads(pathlib.Path(a.entitlements).read_bytes()) == expected
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    assert info['CFBundleIdentifier'] == 'com.bodie.controltower.private'
    assert not any(k.startswith('SU') or k.startswith('NSAppTransportSecurity') for k in info)
    files = [str(f.relative_to(app)) for f in app.rglob('*') if f.is_file()]
    assert set(files) == {'Contents/Info.plist','Contents/MacOS/ControlTowerLocal','Contents/_CodeSignature/CodeResources'}, files
    binary = app/'Contents/MacOS/ControlTowerLocal'
    libs = subprocess.check_output(['otool','-L',str(binary)], text=True)
    assert 'Sparkle' not in libs and '@rpath' not in libs, libs
    for line in libs.splitlines()[1:]:
        assert line.strip().startswith(('/System/Library/','/usr/lib/')), line
print('PASS: active source, dependencies, exact endpoints, identity and entitlement boundary' + ('; signed artifact verified' if a.app else ''))
