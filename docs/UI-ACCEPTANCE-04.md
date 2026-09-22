# UI acceptance: 0.4 review build

Status: synthetic UI PASS; actual Claude/Codex feed and UI comparison PASS. Gemini/Grok account acceptance and Codex saved-login reuse remain pending.

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
The release artifact above was not overwritten or launched during synthetic QA.

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

## Actual Claude and Codex acceptance, 2026-09-22

At adapter SHA `e3ab9ae`, a bounded Python read of only the dedicated
`quota-feed/{claude,codex}.json` files validated their strict schema, percentages,
reset timestamps and observation age. The Codex helper lock was active. No
provider refresh, login retry, credential inspection or helper termination was
performed. The user had reported successful official login and publication.

Native app control then quit version 0.2, launched the release artifact above
after rechecking its version and exact executable hash, and reconnected Claude
and Codex to the same actual quota-only folder through the file picker.
Accessibility inspection confirmed PASS: both cards said Watching quota feed;
Claude Session/Weekly and Codex Primary percentages and resets matched the
validated files. Both observations were over five minutes old by the UI check,
and both correctly displayed Stale. No current allowance or network freshness
is claimed. Personal quota amounts are intentionally omitted from this record.

Only Codex Primary was supplied; no Secondary or window duration was inferred.
This establishes actual authenticated quota publication and dashboard display,
not persisted-login reuse after restart. The active helper was preserved.
Gemini/Grok remain disconnected pending user-owned sign-in and live comparison.
No actual account feed was substituted with fixture data.
