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

## Verification in progress
Working-tree synthetic results observed: 27 Swift tests / 5 suites passed using explicit bundled Testing macro; 12 Python bridge tests passed; source gate passes. Final commit SHA, release artifact and exact verification evidence will be recorded after committing/building. No real credentials, auth files, populated UI, cookies or Keychain secrets inspected. Codex offline schema generator ran with temporary isolated HOME/CODEX_HOME only; confirms device-login/quota methods without account calls.

Installed Codex 0.153.4 signer metadata: OpenAI OpCo, LLC (2DC432GLL2); strict Apple requirement PASS; SHA-256 b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3. Exact pinned command is in PROVIDER-SETUP.md. No actual official app-server authentication runtime started.

Review findings addressed: old network code product inclusion removed; command-size preservation boundary rejected before patch generation; login flood capped; setup document supplied. Proposed ISO reset change was not applied because it confused old API schema with documented statusLine numeric epochs.

Failed attempts: CLT sometimes omits Testing macro discovery after manifest changes; explicit bundled plugin load resolves this without changing system toolchain. Scripts/test_private.sh discovers it. First codesign requirement argument lacked the required literal '=' prefix; corrected and verified signer. No security check weakened.

## Remaining acceptance and next user step
1. User runs the exact Claude prepare command in PROVIDER-SETUP.md; reviews/applies statusLine patch themselves. No agent edit to `.claude/` is authorized.
2. After their normal Claude usage, connect dedicated feed folder in new 0.2 artifact; verify observed real percentages and freshness. No raw statusLine/transcript content should be shared.
3. Separately, user owns Codex device sign-in/submission and Keychain prompt. Agent stops UI/terminal inspection during codes/auth. Resume only after explicit completion; read quota labels only. Verify saved-login reuse separately; synthetic success is not account acceptance.
4. Gemini remains partial pending a defensible official quota-export surface or separate integration decision. No substitution with token-count imports is considered completion.

Workspace ownership: all current changes Codex-owned, no stash/reset/clean. Earlier 0.1 review app may still be open; its current UI has not been inspected because user might have interacted. Do not reuse its prior disconnected observation as current evidence. Do not replace original installed ControlTower or silently quit a populated old enrollment dialog.
