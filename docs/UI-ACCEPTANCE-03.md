# UI acceptance: 0.3 review build

Status: synthetic UI complete; Codex/Gemini real-account acceptance pending.

Source: `7bb58462a8b20652f6c78282aa1f60b5bd95bf03`.
Artifact: `.build/artifacts/review.JouxPz/ControlTower Private.app`.
Executable SHA-256: `3840ba94a2e760b24509d733cf45e397c2025cf4f370d25fb928ef9c2f0e391c`.
Version: 0.3.0, build 3. Strict signature and payload check passed; entitlements
remain only app-sandbox and user-selected read-only files. No network entitlement.

Commands in `/Users/troywitt/AI/Code/ControlTower` at the above SHA:
- `bash Scripts/test_private.sh`: PASS, 28 Swift tests/5 suites, 22 Python tests,
  source security gate. Log `/tmp/controltower-7bb5846-tests.log`.
- `bash Scripts/build_private.sh`: PASS after targeted sandbox escalation for
  Apple's dsymutil. Initial sandbox build failed with Operation not permitted;
  no app entitlement or system permission changed. Log `/tmp/controltower-03-build.log`.

Native QA used a separately identified copy, `com.bodie.controltower.quota-qa03`,
with the same executable and entitlements. Only its dedicated synthetic feed
folder was selected. No fixtures were written into the live quota folder.

Observed PASS:
- Gemini connects and displays synthetic Pro33% and Flash0% with estimated-reset
  and provider-cache provenance labels.
- An atomic replacement with Pro45% and observation age600seconds displays the
  stale warning.
- Empty windows clear the prior percentage and display unavailable.
- Disconnect removes the snapshot and polling controls.
- QA app quit afterwards. Working live0.2 Claude dashboard was not changed.

Earlier actual Claude acceptance remains valid for the observed0.2 session;
Codex and Gemini require user-owned sign-in, actual quota feeds, and matching
UI values before they can be called accepted. No device codes, tokens, auth
files, raw terminal output or provider identity were inspected in this QA.
