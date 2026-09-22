# Claude and Codex closeout: 0.4.1

Current scope is Claude and Codex only. Other providers are deferred, with prior code and user sessions preserved.

Implementation SHA: `c87dacc9e8baa42bdec92ca362f51fb2a7e1befd`.
Artifact: `.build/artifacts/review.RlknAq/ControlTower Private.app`.
Version0.4.1, build5; executable SHA-256:
`ae19c16b49bca53498937c17c711a5763771bfeb27787ce03de0975db0d58c94`.
User launcher: `Bridges/Open ControlTower Private.command`.

Verification commands ran in `/Users/troywitt/AI/Code/ControlTower`:
- PASS `bash Scripts/test_private.sh`:29Swift tests/5suites,39Python tests and source boundary gate. Log `/tmp/controltower-claude-codex-closeout-tests.log`.
- PASS `bash Scripts/build_private.sh`: release build, strict code signature, payload and two-entitlement gate. Log `/tmp/controltower-041-build.log`. Initial sandboxed dsymutil failed; targeted Apple build-tool escalation passed without changing the app sandbox.
- PASS `zsh 'Bridges/Open ControlTower Private.command' --check`: exact binary hash, strict signature and security gate; no app opened by this check. Native app control separately opened the exact verified artifact.
- PASS actual Codex saved-login reuse: with no current helper lock owner, a bounded Python check held the singleton lock, verified the pinned official binary, called only initialize and account/rateLimits/read with the existing private CODEX_HOME, validated nonempty quota schema, and closed its owned process. No login, credential inspection, parallel writer or live feed write. This establishes reuse on this run, not indefinite credential validity.
- PASS strict sanitized file validation of existing Claude and Codex feeds. Both were old, with correct stale status in version0.4 before switch. Codex's missing helper was identified through lock metadata only. A stopped helper can leave an old snapshot after abnormal exit; it is never described as fresh.

Version0.4.1 adds on-card manual refresh guidance and replaces the old --login setup text with Resume/Start launcher instructions. Existing Primary/Secondary semantics remain unchanged; no undocumented window duration is inferred. Personal quota values are omitted from public evidence.

Actual0.4.1 Claude connection and matching stale values were verified through native accessibility. Codex reconnection is awaiting completion of its active user-controlled folder chooser; do not mark it complete until observed.
