# Provider-owned setup (review build 0.2)

**Status: implementation and synthetic tests, not real-account acceptance.** Never enter a session token in ControlTower or chat. The new dashboard has no token form or network entitlement. Claude and Codex feed real provider quota observations through a dedicated local folder; this is separate from optional token-count imports. Gemini is still blocked on a defensible integration surface.

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
4. Open the **new 0.2 review artifact**, click Claude → **Choose quota-feed folder…**, and choose only `~/Library/Application Support/ControlTowerPrivate/quota-feed`. Expect Session/Weekly percentages plus observation time once Claude supplies them. Missing windows stay unavailable; after five minutes without an observation, the dashboard says stale. Watching checks the local files every five seconds; it does not poll Anthropic.

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
python3 /Users/troywitt/AI/Code/ControlTower/Bridges/codex_quota.py \
  --binary /Users/troywitt/.codex/packages/standalone/releases/0.153.4-aarch64-apple-darwin/bin/codex \
  --sha256 b973d440acac501fd2594a43e7ca9ce41e0a65b9dfb28d0d7a7837c99e1261e3 \
  --state "$HOME/Library/Application Support/ControlTowerPrivate/codex-adapter" \
  --output "$HOME/Library/Application Support/ControlTowerPrivate/quota-feed" \
  --login
```

2. The helper prints the exact official verification destination and one-time device code. Complete sign-in yourself. Do not share the code, terminal screenshots, callbacks or credentials with the agent. Stop if an unexpected destination or permission appears. This sign-in lets **official Codex** use your account, including authority beyond quota reads; the wrapper only requests quota RPCs.
3. After “Quota snapshot published”, choose the quota-feed folder in the dashboard's Codex card. Return in Terminal refreshes; `q` or Ctrl+C stops the official process and publishes unavailable. To use the separate saved login on a later run, omit `--login`; do not use your normal Codex home. Binary updates require a fresh reviewed hash, never automatic acceptance.

No loopback listener or system-wide permission change is needed by this wrapper; IPC uses pipes and device login. The helper is intentionally user-started **outside** the dashboard sandbox. The original app's endpoint restriction does not constrain official Codex's network destinations. System/MDM policy can still affect Codex; the private environment does not bypass managed policy. No model/turn/tool, credit/reset, or account-change method is exposed. Unknown server requests, errors, oversize lines and timeouts stop the adapter. This wrapper does not automatically retry or accept trust prompts. Keychain might prompt during your explicit login; cancel unexpected requests. Raw provider errors/stdout/stderr are never logged.

Disconnect in the dashboard stops only its file reads. Quit the Terminal helper separately to stop the provider process. The saved provider login remains under official Codex's management; the dashboard does not delete it. This initial review adapter uses manual terminal refresh and separate setup, not a polished one-click integration.

## Gemini: exact blocker, not technical impossibility

The official CLI uses the internal `cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota` endpoint after Google sign-in/project onboarding. This confirms technical capability inside that client. It does **not** establish a supported external quota API or permission to borrow its OAuth client credentials.

The bounded public-source spike found:
- Interactive `/stats` refreshes per-model buckets into UI history.
- `/stats model` uses cached pooled values, not a structured per-model export.
- ACP's command registry excludes `stats` and has no quota method.
- Headless slash handling can fall through to `sendMessageStream`; JSON stats describe run tokens/latency, not subscription allowance. Therefore launching headless `/stats` is unsafe for a quota-only adapter.

No Gemini process/account was run. No token extraction, client-key copying, auto-trust, or model prompt was added. Gemini remains a required **unmet** acceptance criterion. Next defensible route: a reviewed official upstream quota-only export/RPC, or a separately authorized own-client Google OAuth integration after verifying service eligibility. A third-party desktop OAuth registration alone does not prove the internal quota API will accept it. Interactive terminal scraping could be a separately accepted brittle fallback, but is not shipped or labeled authoritative here.

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
