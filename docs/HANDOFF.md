# Handoff: ControlTower Private 0.4

## Status
- Status: partial. Claude real-account acceptance passed previously; Codex/Gemini/Grok sign-in and live readings remain pending.
- Sender: Codex GPT-6 Astra, task01a0c676-576a-7512-859b-da903fee88b6; origin01a0c670-a5f0-7a31-9f26-2b459686ea85; lease run20260922T062355Z-codex-9ff5d407.
- Written UTC: 2026-09-22.
- Repo: /Users/troywitt/AI/Code/ControlTower; branch harden/explicit-quota-access; implementation SHA cd82b933a68a832586f630918da5770e6dd8e407. Later checkpoint commit is documentation-only.
- Authoritative setup: PROVIDER-SETUP.md, SECURITY.md, UI-ACCEPTANCE-04.md. Draft PR https://github.com/Troywitt/ControlTower/pull/1.
- Replies to: 0.3 handoff, retained in git history.

## Read first
1. Never inspect auth files, Keychain tokens, provider terminal contents, raw statusLine input, transcripts, codes or callback URLs. User owns sign-in/trust/MFA. Only dedicated quota JSON can be read.
2. Acquire/check repo lease before editing. Never edit .claude, global CLAUDE.md, Meta or others' files.
3. Recheck checkout/status and preserve working live0.2 Claude dashboard.

## What changed and why
- Added Grok1.0.40 official CLI adapter for SuperGrok weekly subscription usage. Signature/hash pin, private provider home, empty Git workspace, telemetry/updates/cross-tool discovery off, bounded official configuration preflight. No API-spend substitution or model prompts.
- Fixed shared Gemini/Grok terminal loop's select() arguments and initial-loading capture. Full synthetic terminal lifecycle now verifies publication, no idle re-aging and exit clearing.
- Grok parser requires exact SuperGrok header; reset time inferred only within upcoming weekly window, omitted for ambiguous DST.
- Dashboard0.4 supports four fixed quota feeds while retaining no network, credential or process capability. New artifact does not replace live0.2 yet.
- Earlier Codex startup fix creates isolated CODEX_HOME and avoids masking primary failures during cleanup. Official initialize/cleanup passed without authentication.

## Verification
All commands below ran in /Users/troywitt/AI/Code/ControlTower.

| Check | Result | Command/observation | At SHA | Evidence |
|---|---|---|---|---|
| Tests/source gate | PASS | bash Scripts/test_private.sh | cd82b933 | 29 Swift/5 suites,28 Python; /tmp/controltower-cd82b93-tests.log |
| Release signature/sandbox | PASS | bash Scripts/build_private.sh | cd82b933 | /tmp/controltower-04-build.log; exact artifact/hash in UI-ACCEPTANCE-04.md |
| Grok synthetic native UI | PASS | separate QA app, actual file picker and atomic fixtures | cd82b933 | Percentage/reset,stale,empty,disconnect; QA quit,live app retained |
| Real Claude quota | PASS, prior observation | strict feed + native0.2 dashboard | prior0.2 | Session/Weekly actual data matched; diagnostic marker removed |
| Real Codex/Gemini/Grok | PENDING | user private sign-in | not accepted | Latest bounded Codex check found no feed; 'done' did not establish login |
| Official Grok configuration | PASS, no auth | isolated official inspect --json, memory only | implementation fixture | Only private config/builtin agents; signature verified; no provider report saved |

## Assumptions and unknowns
- Gemini/Grok screen extraction is version-specific. Official values may be cached; observation time is not proven network freshness. Percentages rounded/floored; resets estimated.
- Grok public source9bb727cc differs from released binary commit eb1a2256660d; actual authenticated grammar remains unverified. Unknown/malformed screen stays unavailable.
- Codex requests Keychain-only storage; real persistence/reuse unverified. Gemini/Grok official storage remains opaque, not claimed Keychain-only.
- Dependencies are machine-pinned under ignored .build; no global installation or PATH change. Other machines need reviewed pins.

## Remaining work
- [ ] User retries fixed Codex private launcher and sees “Quota snapshot published”; verify only sanitized feed and actual dashboard match.
- [ ] User runs Gemini launcher, owns Google sign-in/trust, enters /model; verify real feed/UI.
- [ ] User runs Grok launcher, owns subscription sign-in/trust, enters /usage; verify released screen grammar through bounded parser output and actual quota/UI comparison.
- [ ] After sign-in, open0.4 and reconnect dedicated feed folder. Keep live0.2 until ready.
- Failed attempts: Codex missing private directory and secondary cleanup PermissionError fixed. Gemini select() wrong argument fixed by full lifecycle regression. Earlier direct startup did not exercise wrapper. PTY regression initially blocked while test failed to drain output; corrected test passes. Bare swift test lacked repo cache/macro setup; repo test_private.sh passes. Synthetic fixture initially had nonprivate permissions; corrected only fixture to0700.
- Blocker: user-owned authentication; do not poll absent feeds indefinitely or infer consent/success from silence.
- **Next action:** clarify whether the user's “done” means Codex sign-in; otherwise run fixed Codex launcher in their private Terminal. Origin relays questions; no duplicated prompts.

## Workspace state
- Codex-owned changes checkpointed; no unrelated dirty files observed. No stash/reset/clean.
- Stashes: none created.
- Running jobs: live ControlTower Private0.2 watches Claude. QA0.4 closed. No provider auth terminals inspected; user owns their lifecycle.
- Live data: only allowlisted dedicated quota feed; latest Codex feed absent. No synthetic data written into live folder. No auth/transcript data copied to repository or PR.
- Lease: release after final checkpoint/push; acquire afresh before any later edit.

## Latest Codex live attempt, 2026-09-22

User completed device sign-in and reported publication, but the bounded feed check found empty windows and no helper lock owner. A subsequent user-owned saved-login run failed at quota read (unavailable). Account acceptance is still pending; do not claim login persistence passed. Added fixed-category provider failure reporting, distinct quota-read/decoding stages, honest empty-window messaging, and Resume Codex Quotas.command without --login. Raw provider errors remain private and are never printed/saved. Next action: user runs Resume and reports only the fixed status line. Python bridge suite PASS (29 tests), including error-category secret sentinel and real-pipe failure tests; log /tmp/controltower-codex-diagnostic-tests.log. Dashboard executable unchanged.

## Codex error classification correction, 2026-09-22

The updated Resume launcher reported “provider protocol incompatible”. Investigation found this label was overconfident: official Codex also uses JSON-RPC -32600 for its fixed ChatGPT-authentication-required message. Classifier now recognizes that message and leaves unknown -32600 errors generic. Do not interpret this as a protocol-caused login failure.

The pinned0.153.4 offline ClientRequest schema specifies null quota params. Helper now sends null instead of converting None to {}; a strict schema regression protects it. Actual unauthenticated official app-server testing found BOTH {} and null reach the same authentication-required outcome, so empty-object serialization was not proved to be the live blocker. Experimental API remains off.

One authorized saved-login quota-only check via the verified official executable, the existing separate provider home, and a held feed lock returned “saved login unavailable or rejected”. It initialized and terminated cleanly; no provider credentials/raw payloads or sign-in UI were inspected and no model request was made. This confirms the current provider process cannot use that saved authentication, but does not determine whether it was absent, expired or inaccessible. No plaintext/token fallback was added. The working Claude app is unchanged.

Evidence: generated public schema .build/codex-protocol-01534/ClientRequest.json; fixed-category official runtime checks observed in this task; Python log /tmp/controltower-codex-auth-category-tests.log. Upstream primary evidence for the authentication error: https://github.com/openai/codex/blob/main/codex-rs/app-server/tests/suite/v2/rate_limits.rs (main is mutable; pinned runtime independently reproduced the category). Next action requires user-owned Start Codex Quotas.command sign-in, keeping the SAME window open until both “Provider reported login complete.” and “Quota snapshot published.” appear. Resume alone cannot restore unavailable authentication. Root relays this single step. Account acceptance remains pending.
