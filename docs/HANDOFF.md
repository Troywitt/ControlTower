# Handoff: ControlTower Private 0.3

## Status
- Status: partial. Real Claude quota-to-dashboard acceptance passed. Codex and Gemini account enrollment and actual dashboard readings remain pending.
- Sender: Codex GPT-6 Astra, task 01a0c676-576a-7512-859b-da903fee88b6; origin 01a0c670-a5f0-7a31-9f26-2b459686ea85.
- Written UTC: 2026-09-22.
- Repo: /Users/troywitt/AI/Code/ControlTower, branch harden/explicit-quota-access, changes based on 5da2248. Implementation SHA and artifact to be recorded after build.
- Authoritative setup: PROVIDER-SETUP.md and SECURITY.md. Draft PR: https://github.com/Troywitt/ControlTower/pull/1.
- Replies to: prior 0.2 handoff, retained in git history.

## Read first
1. Do not inspect auth files, Keychain contents, provider terminals, raw statusLine input, transcripts or sign-in codes. User owns browser/Terminal authentication.
2. Check/acquire agent lease before edits; never edit .claude, global CLAUDE.md, Meta or other editors' changes.
3. Compare git status with workspace state. Keep working Claude bridge intact.

## What changed and why
- Fixed Codex startup: create isolated CODEX_HOME before starting official app-server. Added safe cleanup of already-exited child, group-denial handling, nonsecret failure stages and single-writer output lock.
- Added private-terminal Gemini adapter for unmodified official npm CLI 0.60.0. User signs in and enters /model; adapter generates no keystrokes. In-memory bounded terminal rendering exports only Pro/Flash/Flash Lite rows with rounded usage and estimated resets. No raw terminal log. Child home is separate; telemetry, usage reporting and auto-updates off.
- Review fixed Gemini system/parent config discovery and cleanup on terminal loss; existing machine policy stops setup for review.
- Gemini runtime and Node hash pins, app-local npm lockfile, pinned pyte/wcwidth. No global install. /model refreshes quotas in reviewed official code; headless /stats is never used.
- Dashboard supports Gemini while retaining no network/credential/process code and only selected-folder read sandbox access. Gemini labels screen/cache provenance and reset estimates.
- Private launcher files provide user-owned Terminal onboarding. Claude diagnostic is opt-in, disabled after successful observation.

## Verification
All commands below ran in /Users/troywitt/AI/Code/ControlTower on the 0.3 working tree based on 5da2248; final commit/artifact evidence follows separately.

| Check | Result | Command or observation | Evidence |
|---|---|---|---|
| Swift and source gate | PASS | bash Scripts/test_private.sh | 28 Swift tests in 5 suites, source security gate; /tmp/controltower-03-final-tests.log |
| Final Python bridges | PASS | python3 -m unittest discover -s Tests/BridgeTests -v | 22 tests; /tmp/controltower-03-python.log; negative sentinel, parser/ANSI/stale boundary, locks and cancellation |
| Real Codex startup without auth | PASS | scratch launch, initialize, close | Before fix exit1; after fix initialize PASS and child terminated(-15), no auth/model calls |
| Real Gemini startup without auth | PASS, bounded | scratch isolated PTY, no input, then cleanup | Reached trust prompt; no automatic trust or sign-in; process terminated |
| Real Claude quota | PASS | strict dedicated feed read + actual 0.2 native UI | 2026-09-22 observation: actual Session/Weekly percentages and resets matched the UI. Account values omitted from public evidence. Temporary diagnostic marker removed |
| Real Codex/Gemini quota | PENDING | user private sign-in needed | No valid real feeds at last check; do not call complete |
| 0.3 signed artifact/UI | PENDING | build and native UI next | Keep current 0.2 open until replacement is ready |

## Assumptions and unknowns
- Gemini parser is version-specific screen extraction, not a stable quota API. CLI rounds percentages and durations; cached provider values may survive refresh errors. Only observation freshness is claimed.
- Official Gemini manages new credentials in its own home; not claimed Keychain-only. No credential discovery/copying by adapter.
- Codex requests keyring-only storage; persistence/reuse still unverified. No plaintext fallback requested.

## Remaining work
- [ ] User completes fixed Codex launcher; validate actual feed, reset times, UI and disconnect.
- [ ] User completes Gemini private sign-in and opens /model; validate real feed and UI, then disconnect.
- [ ] Build/sign 0.3, verify entitlements and UI; update draft PR with final evidence.
- [ ] Grok SuperGrok consumer allowance: official CLI /usage route found; installation/runtime grammar/sign-in unverified. No installation or misleading support card.
- Failed attempts: Codex missing CODEX_HOME caused exit1; secondary cleanup PermissionError hid it. Both reproduced/fixed/tested. Sandbox codesign check failed but unchanged hash passed strict signature outside sandbox; no security check weakened.
- Blockers: user-owned authentication, no substituted synthetic account readings.
- Next action: await user private sign-in result while finishing build and review.

## Workspace state
- Current changes are Codex-owned; no unrelated edits observed. Narrow staging only. No stash/reset/clean.
- Runtime dependencies live only in ignored .build directories; provider credential homes remain opaque and outside repository.
- Existing 0.2 dashboard watches Claude's dedicated quota feed. Original installed app unchanged.
- Live data: only allowlisted quota JSON reads; temporary field-shape diagnostic disabled after sufficient evidence. No raw provider data copied to docs/GitHub.
- Lease: held during active implementation; release when checkpoint is committed and work stops.
