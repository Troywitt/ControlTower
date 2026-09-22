# UI acceptance: 0.4 review build

Status: synthetic UI PASS; actual Codex/Gemini/Grok account acceptance pending.

Implementation SHA: `cd82b933a68a832586f630918da5770e6dd8e407`.
Artifact: `.build/artifacts/review.vw8Bwv/ControlTower Private.app`.
Version 0.4.0, build 4. Executable SHA-256:
`041f32e29c2b98a13b97d40d5c739dcd4567f73bcecc37692bbd5bb268c102f5`.

Commands in `/Users/troywitt/AI/Code/ControlTower` at that implementation SHA:
- `bash Scripts/test_private.sh`: PASS, 29 Swift tests/5 suites, 28 Python tests,
  source security gate. Log `/tmp/controltower-cd82b93-tests.log`.
- `bash Scripts/build_private.sh`: PASS, strict signature/payload/entitlements
  gate. Log `/tmp/controltower-04-build.log`. Targeted build escalation was used
  for Apple's build tools; app sandbox and system settings were not changed.
- `git diff --check`: PASS.

Native QA used a separately identified, re-signed copy
`com.bodie.controltower.quota-qa04`; only its dedicated synthetic folder was
selected. Its executable hash differs because signing embeds the QA identity.
The release artifact above was not overwritten or launched.

Observed PASS:
- Grok starts disconnected and says live sign-in/parser acceptance is pending.
- Synthetic Weekly42% displays correctly with estimated reset and cache limits.
- Atomic replacement with Weekly61%, age600seconds, displays stale; omitted
  reset removes the prior estimated reset.
- Empty windows remove the previous percentage and display unavailable.
- Disconnect removes reading controls and the snapshot.
- QA quit; app inventory confirmed only the live private dashboard remained.

The shared Gemini/Grok terminal test runs a fake CLI through nested PTYs:
loading, valid output, repeated redraw without timestamp renewal, Ctrl+] exit,
and feed clearing all passed. This caught and fixed the previous version's bad
select() argument. The test must drain the simulated terminal during exit so
macOS terminal restoration can finish. Earlier direct Gemini startup evidence
bypassed the wrapper and did not establish that wrapper's runtime correctness.

Actual Claude acceptance remains the observed 0.2 session. The working live0.2
app was untouched. No actual account feed is substituted with fixture data.
Codex/Gemini/Grok require user-owned sign-in and matching real UI readings.
