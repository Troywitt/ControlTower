# Provider-owned setup (review build 0.4)

**Status: actual Claude quota-to-dashboard acceptance passed; Codex/Gemini/Grok enrollment remains pending.** Never enter a session token in ControlTower or chat. The new dashboard has no token form or network entitlement. Claude and Codex feed real provider quota observations through a dedicated local folder; this is separate from optional token-count imports. Gemini uses strict parsing of the official interactive quota screen.

## Claude: first user step

1. In your own Terminal, run the command below. It reads only your chosen settings file to prepare a patch, preserves the existing command and statusLine options, and writes **nothing** to `.claude/`. Review files contain only statusLine settings, not the rest of your settings. Use fresh review directories; repeated preparation refuses overwrites.

```bash
python3 /Users/troywitt/AI/Code/ControlTower/Bridges/prepare_claude.py \
  --settings "$HOME/.claude/settings.json" \
  --review-dir "$HOME/Library/Application Support/ControlTowerPrivate/claude-review-v1" \
  --output "$HOME/Library/Application Support/ControlTowerPrivate/quota-feed"
```

2. Open `statusline-merge-patch.json` in that review folder. Merge **only its `statusLine` value** into your existing settings using your editor. Keep all other settings. If you have no settings file, first create an empty `{}` file yourself. The generator intentionally does not install the patch. `statusline-rollback.json` records the old value; to undo, restore it, or remove `statusLine` if the old value was null.
3. Continue your normal signed-in Claude Code session. Its documented statusLine quota fields require a supported version (current docs: v2.1.251+) and Pro/Max account, after the first API response. Do not send a model request just for this acceptance without choosing to do so yourself. The bridge forwards stdin in memory to your original statusLine command and preserves its terminal display. It never logs raw stdin. The original command remains trusted user code and retains its existing access.
4. Open the **new 0.4 review artifact**, click Claude → **Choose quota-feed folder…**, and choose only `~/Library/Application Support/ControlTowerPrivate/quota-feed`. Expect Session/Weekly percentages plus observation time once Claude supplies them. Missing windows stay unavailable; after five minutes without an observation, the dashboard says stale. Watching checks the local files every five seconds; it does not poll Anthropic.

Only quota percentages/reset times/provider/version/observation time leave the statusLine bridge. It drops transcript paths, working directory, session IDs, costs, and all other input. It records the time it *observed* Claude's statusLine data, not a verified provider-fetch time; repeated cached provider data may remain unchanged. Claude being idle/closed means no guaranteed fresh allowance. This covers documented 5-hour/7-day fields, not all model-specific allowances.

## Codex: official device login in a private terminal

ControlTower's helper runs the **unmodified signed official Codex executable**, over private stdio. It has its own HOME/CODEX_HOME; no existing login discovery. The helper requests Keychain-only storage (no `auto` plaintext fallback). The official process owns auth/refresh; our code does not open tokens or credential files. Keychain persistence and actual quota access remain unverified until you run the live acceptance yourself.

The installed binary was signature-verified without executing sign-in:
- Resolved release: `0.153.4-aarch64-apple-darwin`
- Apple signing requirement: identifier `codex`, team `2DC432GLL2`, Apple generic anchor.
- SHA-256: `b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3`
- Its offline schema generator confirms device login + `account/rateLimits/read` fields. That is protocol evidence, not account acceptance.

1. In your own private Terminal (not an agent-captured terminal), run:

```bash
open "/Users/troywitt/AI/Code/ControlTower/Bridges/Start Codex Quotas.command"
```

2. Official Codex now runs `login --device-auth` directly. It owns the complete device flow and prints its instructions only into your private Terminal. The wrapper does not capture, parse or save this output. Complete sign-in yourself and keep this same window open. Do not share codes, callbacks or terminal screenshots. This official login has account authority beyond quota reads.
3. Only after official login exits successfully does the launcher print **“Official CLI login exited successfully. Checking quota access next.”** It then starts the quota-only app-server in exactly the same private HOME/CODEX_HOME, with the same verified binary and keyring-only configuration. This success line proves only that the login command exited0. Acceptance still requires **“Quota snapshot published.”**, nonempty actual quota windows and a matching dashboard reading.
4. Select the dedicated quota-feed folder in the dashboard's Codex card. Return in Terminal refreshes; `q` or Ctrl+C stops the provider and clears the feed. Keep this Terminal open while tracking. For a later saved-login run, open `Bridges/Resume Codex Quotas.command`; it starts no login flow.

The feed lock spans enrollment and quota startup. Nonzero official exit, cancellation or the660-second overall login bound stops without starting the quota reader or repeating sign-in. Both clients use a minimal allowlisted environment, not inherited provider keys/proxies/config. Official output stays user-owned and may include provider error details; report only the wrapper's fixed final status. Provider-managed files/logs remain private and must not be inspected by the dashboard or wrapper. Runtime login/Keychain persistence is still unverified. The earlier app-server-managed `--login` flow remains for diagnostics but is no longer used by the Start launcher.

No loopback listener or system-wide permission change is needed by this wrapper; IPC uses pipes and device login. The helper is intentionally user-started **outside** the dashboard sandbox. The original app's endpoint restriction does not constrain official Codex's network destinations. System/MDM policy can still affect Codex; the private environment does not bypass managed policy. No model/turn/tool, credit/reset, or account-change method is exposed. Unknown server requests, errors, oversize lines and timeouts stop the adapter. This wrapper does not automatically retry or accept trust prompts. Keychain might prompt during your explicit login; cancel unexpected requests. Raw provider errors/stdout/stderr are never logged. Failed device completion exposes only a fixed classified category; process exit, malformed protocol, notification flood and timeout are distinguished. The helper cannot reconstruct a failure reason from a run made before this reporting fix.

Disconnect in the dashboard stops only its file reads. Quit the Terminal helper separately to stop the provider process. The saved provider login remains under official Codex's management; the dashboard does not delete it. This initial review adapter uses manual terminal refresh and separate setup, not a polished one-click integration.

## Gemini: official interactive quota display

The official pinned CLI 0.60.0 is installed only under `.build/gemini-runtime`; no global installation. The helper verifies the npm tree, Python parser tree, and Node executable against `Bridges/gemini-runtime-pin.json`. The npm lockfile is retained in `Bridges/gemini-package-lock.json`. Parser dependencies are pyte 0.8.2 and wcwidth 0.2.13 in `.build/gemini-python`. On this reviewed machine, `bash Scripts/prepare_gemini_runtime.sh` restores dependencies and verifies the pins. Pins include the current machine's Node binary and platform-specific optional packages; other machines require a reviewed repin. Do not silently regenerate pins after an update.

1. Open `Bridges/Start Gemini Quotas.command` in your own Terminal. Keep its output private. The adapter starts the unmodified official CLI in a new home with telemetry/usage reporting/auto-update disabled. Existing Google sessions and settings are untouched. Google manages the new credentials; the adapter does not read them or claim Keychain-only storage.
2. Answer any trust prompt yourself for the empty adapter workspace, and complete official Google sign-in yourself. The adapter does not accept prompts or enter credentials for you. If project onboarding, a paid plan change, or an unexpected permission is required, stop and resolve that explicit decision first.
3. At the normal Gemini prompt, enter `/model`. This official command requests quota refresh and opens the model dialog without a model-generation call. Leave the dialog visible. The helper publishes only known tier labels and numeric quotas.
4. Connect Gemini to the dedicated quota-feed folder in the 0.4 dashboard. Verify the displayed tiers match the Terminal. Press Esc, then enter `/model` again for another observation. **Ctrl+]** stops the helper and marks its feed unavailable. Dashboard Disconnect stops only the dashboard reader.

The CLI groups model buckets by tier and displays the highest usage in each group, rounded to an integer percentage. The dashboard labels these Pro, Flash, and Flash Lite, not individual models. Reset times are estimated from remaining duration rounded up to a minute; the UI labels them estimated. A dialog publishes once; redraws do not renew its observation timestamp. Missing/malformed/unknown rows stay unavailable. Observations age into stale after five minutes. A successful refresh cannot be proven from rendered values alone: the official client may retain cached quota after a provider error. The UI is a best-effort observation, not a stable API contract.

The wrapper forwards user input but generates none. Do not enter a model message just to obtain quota. It never uses headless `/stats`, copies OAuth identities or auth files, logs terminal contents, or auto-accepts trust. Strict fixed-name parsing excludes identity/account text even if it appears elsewhere on screen.

## Grok: official SuperGrok usage display; live acceptance pending

This adapter targets the $30 consumer SuperGrok weekly allowance. It does not substitute API-team billing. The official [Grok Build CLI](https://docs.x.ai/build/overview) owns browser sign-in; its interactive `/usage` command opens subscription usage without a model prompt.

Official binary 1.0.40 is installed only at `.build/grok-runtime/grok-1.0.40-macos-aarch64`. SHA-256: `3f2aef9618191a2c60d18a5044fa462c9c77bdc4187b02ed716b0394e8d4fef2`. Each launch checks its hash and strict Apple signature (X.AI Corporation team `5Y6N3AJ54S`, identifier `xai-grok-pager`). The public archive is `https://x.ai/cli/grok-1.0.40-macos-aarch64.gz`. No global install or shell change is needed. The installer was not executed. Terminal parsing uses the same pinned app-local Python dependencies as Gemini.

1. Open `Bridges/Start Grok Quotas.command` in your own private Terminal after the earlier provider setup is finished.
2. Complete official subscription sign-in and trust prompts yourself. Do not select API billing or a paid plan change to make this adapter work.
3. At the normal prompt enter `/usage` and leave **Usage limit** visible. Only **Weekly limit (SuperGrok)** followed by the fixed quota bar is accepted. The adapter sends no input itself.
4. Connect the Grok card to the dedicated quota-feed folder. Compare its weekly percentage to Terminal. Esc then `/usage` refreshes the observation; Ctrl+] stops the helper and clears the feed. Dashboard Disconnect stops only its reader.

A separate private provider home and empty Git workspace limit inherited configuration. Updates, leader reuse, telemetry, feedback, indexing and cross-tool compatibility discovery are disabled for this child. Existing machine policy stops setup for review. Before interactive startup, official `inspect --json` runs in memory and rejects external hooks/plugins/MCP/LSP/instructions or non-builtin agents/skills. No report is saved. Official credential storage remains opaque and provider-managed.

The CLI floors its percentage to an integer and prints a reset date without year or timezone. The adapter infers only an upcoming weekly reset in the same system timezone; ambiguous daylight-saving times omit the reset. The dashboard labels resets estimated and screen values possibly cached. Idle redraws do not renew observation time. This is version-specific UI extraction, not a stable quota API.

Verification so far: strict signature, private configuration preflight, parser fixtures and shared terminal lifecycle tests. **Real sign-in and the released binary's authenticated screen remain unverified.** The public source snapshot `9bb727ccdff0a793ee73bcde4e2e09cbef6b5387` is a periodic sync, not the binary's reported commit `eb1a2256660d`; fixtures alone cannot establish a screen match. The card explicitly shows live acceptance pending. If actual screen differs, the feed stays unavailable; no raw screen should be shared with an agent.

## Sources and freshness

Checked 2026-09-22; public main branches and provider interfaces can change.
- [Claude statusLine quota contract](https://code.claude.com/docs/en/statusline)
- [Claude authentication](https://code.claude.com/docs/en/authentication) (`setup-token` is model-only)
- [Claude credential-use rules](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use). This is provider support/terms context, not a legal conclusion about every private own-user tool. Provider-owned auth avoids collecting session credentials.
- [Codex app-server login and rate limits](https://developers.openai.com/codex/app-server)
- [Gemini stats implementation](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/commands/statsCommand.ts)
- [Gemini ACP command registry](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/acp/acpCommandHandler.ts)
- [Gemini headless dispatch](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/nonInteractiveCli.ts) and [command result handling](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/nonInteractiveCliCommands.ts)
- [Google desktop OAuth registration](https://developers.google.com/identity/protocols/oauth2/native-app)

Pinned source: [model command](https://github.com/google-gemini/gemini-cli/blob/v0.60.0/packages/cli/src/ui/commands/modelCommand.ts), [quota renderer](https://github.com/google-gemini/gemini-cli/blob/v0.60.0/packages/cli/src/ui/components/ModelQuotaDisplay.tsx), and [reset formatter](https://github.com/google-gemini/gemini-cli/blob/v0.60.0/packages/cli/src/ui/utils/formatters.ts).
