# Handoff: ControlTower Private 0.2

## Status
Partial. Manual-token onboarding was an implementation gap, not missing user input. It has been replaced with provider-owned Claude/Codex quota adapters. No real-account onboarding/Keychain persistence is accepted yet. Gemini remains an unmet required feature.

Repo: `/Users/troywitt/AI/Code/ControlTower`; branch `harden/explicit-quota-access`; draft PR https://github.com/Troywitt/ControlTower/pull/1. Origin task `01a0c670-a5f0-7a31-9f26-2b459686ea85`; implementation task `01a0c676-576a-7512-859b-da903fee88b6`. Written 2026-09-22 by Codex GPT-6 Astra. See PROVIDER-SETUP.md then SECURITY.md. Lease acquired before edits; release after final push.

## Implementation
- Claude: bounded statusLine quota-only emitter, atomic 0600 output, preservation of previous command/options, review/rollback patch generator. Does not modify `.claude/`; user applies patch. Official numeric epoch reset contract; not the old direct API's ISO reset contract.
- Codex: user-started terminal helper, signed/hash-pinned official binary, private provider HOME/CODEX_HOME, empty cwd, minimal environment, keyring-only requested, narrow stdio methods, device login, manual quota refresh, no model/reset/credits/commands. Outside the dashboard sandbox, explicitly documented; no system security change or entitlement expansion.
- Dashboard: no credential UI/Keychain implementation/network/process code in product dependency graph; only app sandbox + selected-read-only entitlement. Dedicated quota folder selection supports atomic replacement; checks every five seconds, disconnect revokes scope, missing/invalid data removes success, stale observations labeled after five minutes.
- Gemini: public-source spike found no safe structured headless/ACP quota route. ACP excludes stats; headless slash stats can reach a model request. No adapter run, token extraction or copied client key. Exact sources/boundary in PROVIDER-SETUP.md; no claim of technical impossibility or full completion.
- Original upstream installed app untouched. Historical sources excluded; old manual-token core moved to test-only fixtures. Prior 0.1 UI report is explicitly historical.

## Verification observed
All commands ran in `/Users/troywitt/AI/Code/ControlTower` at implementation SHA `e7227b46ae0812ad3bfaa95faabcce33972d3701`. Later handoff/evidence edits are documentation-only.

| Check | Result | Evidence |
|---|---|---|
| `Scripts/test_private.sh` | PASS | 27 Swift tests / 5 suites; 12 Python tests; source boundary gate. `/tmp/controltower-e7227b4-tests.log` |
| `Scripts/build_private.sh` | PASS | Release build, strict signature and signed artifact payload/entitlement gate. `/tmp/controltower-e7227b4-build.log` |
| Native synthetic UI | PASS, bounded | Separate QA identity copied from this build; selected synthetic folder, Claude25/40%, automatic atomic update45%, stale warning, missing-data clear, Codex15%, both disconnects and Claude setup sheet. See UI-ACCEPTANCE-02.md |
| Official Codex offline schema | PASS, bounded | Temporary isolated HOME/CODEX_HOME, generate-json-schema only. Device login request/response and quota-read methods present; no account operations |
| Actual Claude/Codex sign-in, quota and Keychain reuse | NOT RUN | User-owned next acceptance; no secrets inspected |
| Gemini adapter | BLOCKED | No defensible quota-only headless/ACP export found; exact source evidence in PROVIDER-SETUP.md |

Review artifact (not installed/launched): `.build/artifacts/review.iKiDno/ControlTower Private.app`, version0.2.0 build2; `CTSourceRevision=e7227b46ae0812ad3bfaa95faabcce33972d3701`. Main executable SHA-256 `bfc09b9f37141c7f24b6db9e1abd2d90c0dd48538806c0cb995aba7b4ae01566`. Signed entitlements contain only app-sandbox and files.user-selected.read-only; **no network entitlement**. UI QA used a copy with separate `com.bodie.controltower.quota-qa` identity to avoid interacting with potentially populated old app; that QA app was quit afterwards, confirmed absent in app inventory. Not a live account test.

No real credentials, auth files, populated UI, cookies or Keychain secrets inspected. No `.claude/`, account, certificate, original installed app or system security config modified.

Installed Codex 0.153.4 signer metadata: OpenAI OpCo, LLC (2DC432GLL2); strict Apple requirement PASS; SHA-256 b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3. Exact pinned command is in PROVIDER-SETUP.md. No actual official app-server authentication runtime started.

Review findings addressed: old network code product inclusion removed; command-size preservation boundary rejected before patch generation; login flood capped; setup document supplied. Proposed ISO reset change was not applied because it confused old API schema with documented statusLine numeric epochs.

Failed attempts: CLT sometimes omits Testing macro discovery after manifest changes; explicit bundled plugin load resolves this without changing system toolchain. Scripts/test_private.sh discovers it. First codesign requirement argument lacked the required literal '=' prefix; corrected and verified signer. No security check weakened.

## Remaining acceptance and next user step
1. User runs the exact Claude prepare command in PROVIDER-SETUP.md; reviews/applies statusLine patch themselves. No agent edit to `.claude/` is authorized.
2. After their normal Claude usage, connect dedicated feed folder in new 0.2 artifact; verify observed real percentages and freshness. No raw statusLine/transcript content should be shared.
3. Separately, user owns Codex device sign-in/submission and Keychain prompt. Agent stops UI/terminal inspection during codes/auth. Resume only after explicit completion; read quota labels only. Verify saved-login reuse separately; synthetic success is not account acceptance.
4. Gemini remains partial pending a defensible official quota-export surface or separate integration decision. No substitution with token-count imports is considered completion.

Workspace ownership: all current changes Codex-owned, no stash/reset/clean. Earlier 0.1 review app may still be open; its current UI has not been inspected because user might have interacted. Do not reuse its prior disconnected observation as current evidence. Do not replace original installed ControlTower or silently quit a populated old enrollment dialog.
