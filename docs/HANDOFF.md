# Handoff: ControlTower Private 0.4

## Status
- Status: partial. Actual Claude and Codex quota feed/UI comparison passed in version0.4. Gemini/Grok sign-in and live readings, plus Codex saved-login reuse, remain pending. Latest acceptance below supersedes earlier pending-Codex entries.
- Sender: Codex GPT-6 Astra, task01a0c676-576a-7512-859b-da903fee88b6; origin01a0c670-a5f0-7a31-9f26-2b459686ea85; lease run20260922T062355Z-codex-9ff5d407.
- Written UTC: 2026-09-22.
- Repo: /Users/troywitt/AI/Code/ControlTower; branch harden/explicit-quota-access; implementation SHA cd82b933a68a832586f630918da5770e6dd8e407. Later checkpoint commit is documentation-only.
- Authoritative setup: PROVIDER-SETUP.md, SECURITY.md, UI-ACCEPTANCE-04.md. Draft PR https://github.com/Troywitt/ControlTower/pull/1.
- Replies to: 0.3 handoff, retained in git history.

## Read first
1. Never inspect auth files, Keychain tokens, provider terminal contents, raw statusLine input, transcripts, codes or callback URLs. User owns sign-in/trust/MFA. Only dedicated quota JSON can be read.
2. Acquire/check repo lease before editing. Never edit .claude, global CLAUDE.md, Meta or others' files.
3. Recheck checkout/status and preserve working live0.4 Claude/Codex dashboard and active Codex helper.

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

## Device-sign-in failure diagnosis, 2026-09-22

User's next Start attempt reached the private device-code display, then stopped at official device sign-in (unavailable), without provider-reported login completion. There is no timing evidence or proof the browser step finished. No timeout, Keychain failure or user cancellation may be inferred from that generic line.

The pinned AccountLoginCompletedNotification schema matches the helper's success/loginId handling. However, on success:false the helper discarded the official error string and raised a generic error. That reporting bug is fixed: only a fixed classified reason is retained, with no raw error text printed/saved. EOF, malformed messages/completions, unwanted server requests, notification flood, local pipe failure and the existing absolute timeout now remain distinct. The introduction now says Keychain storage is requested, rather than promising an unverified successful save. No storage fallback or policy change.

Real-pipe synthetic regressions pass for coalesced and fragmented frames, delayed completion, completion before the start response, secret-bearing failure notification categorization/cancellation, EOF, malformed messages and timeout. Existing receive buffering already consumes buffered lines before selecting; no buffering bug or premature timeout was reproduced. Existing single-writer, method allowlist, keyring config and flood bounds remain. There are33 passing bridge tests in /tmp/controltower-login-lifecycle-tests.log. User's actual failure cause remains unknown because earlier code discarded it; no actual private sign-in was captured or triggered by tools.

Next user step: run the updated Start Codex Quotas.command in their private Terminal, complete official device sign-in, leave that window open and report only its final fixed status line. Expected success is provider-reported login complete followed by quota snapshot published. This is a changed diagnostic retry, not a claim sign-in itself is repaired. Root relays the step.

## Direct official enrollment path, 2026-09-22

Fable's suggestion was verified locally before implementation. Pinned signature/hash-verified Codex0.153.4 `login --help`, run only in an empty temporary profile, supports `--device-auth` and -c overrides. Public upstream cli/src/login.rs passes configured storage mode into device enrollment and reports exit0 on success; that mutable source is supporting evidence, not a claim about an exact pinned commit. No actual authentication was started by tools.

Start Codex Quotas.command now selects --enroll-official. Shared provider_context constructs the exact same binary/config/cwd/env for direct official CLI login and subsequent quota-only app-server. Official login inherits only the user's Terminal (no pipes/capture), requests keyring-only storage, and owns codes/browser flow. It holds the single-writer feed lock across the transition. Login exit0 is required to start quota reading; nonzero/cancel/660-second deadline stops with a fixed status and bounded owned-process cleanup. Resume remains quota-only. Legacy --login diagnostics remain but are not selected by Start.

Verification in /Users/troywitt/AI/Code/ControlTower: python3 -m unittest discover -s Tests/BridgeTests -v PASS36 tests (/tmp/controltower-direct-login-tests.log); zsh -n Start launcher PASS; git diff --check PASS. New tests cover shared private identity/config/env, inherited terminal streams, failure/cancel/deadline cleanup, and strict login-success-before-quota sequencing. Dashboard unchanged; no rebuild needed. Real login exit, persisted Keychain reuse and actual quotas remain PENDING.

Next user step: open the Start launcher in a private Terminal, follow OFFICIAL Codex sign-in instructions, keep the window open. Expect “Official CLI login exited successfully. Checking quota access next.” then “Quota snapshot published.” Only the latter plus actual nonempty feed/UI establishes quota acceptance. Report only final fixed status, no code or raw provider error. Root relays the single step.

## Confirmed default-Keychain lookup correction, 2026-09-22

Actual official CLI failure was “A default keychain could not be found” during Keychain-only token storage. Read-only `/usr/bin/security default-keychain -d user` in minimal environments reproduced it: real OS HOME exit0 with existing login Keychain path; isolated provider HOME exit1. CFFIXED_USER_HOME with isolated HOME did not repair lookup and was not adopted. No Keychain items/default/search lists/passwords/permissions were read or changed.

provider_context now derives HOME from pwd.getpwuid(os.getuid()), retains the EXACT existing private CODEX_HOME, and supplies the same identity to official login and quota processes. Corrected provider env passed the same metadata lookup (exit0). Empty working directory is initialized as its own Git root with no global Git config/template; hooks/plugins/remoteplugins/apps/workspace dependencies/shellsnapshot/tools/memories/imports are disabled in the child. Host-skill skipping is requested. Known system/managed policy metadata stops before feature overrides; ordinary managed enforcement remains.

Isolation evidence: pinned official CLI featureslist confirms requested flags; a synthetic invalid normal~/.codex/config.toml does not affect startup with privateCODEX_HOME. Public configuration code loads user config from CODEX_HOME; public hook engine returns before discovery when hooks disabled and plugin hook sources empty. Important limitation: synthetic explicit skills/list still discovers a host skill with skip_host_skill_discovery=true. That flag is NOT a universal filesystem firewall. Production rejects skills/list/hooks/list/plugins/list/configread and all thread/turn methods. No actual host skills were requested. A synthetic file-atime experiment lacked a working positive control and provides NO read-isolation evidence; do not cite it as proof.

Public audit revision94174e44cbc54cece45f6052328ca0c2cd7a8a2a under ignored .build/codex-public-audit provides supporting source, not exact pinned-binary provenance. No credential-bearing profile/source/log was uploaded.

Validation: `python3 -m unittest discover -s Tests/BridgeTests -v` in /Users/troywitt/AI/Code/ControlTower PASS38 tests, log/tmp/controltower-home-fix-tests.log. New regressions cover OS-derived HOME against inherited poisoning, exact privateCODEX_HOME parity, Git root creation, known-policy stop, feature flags and expanded RPC denials. Corrected-env security metadata checkPASS without provider authentication. Dashboard and Claude unchanged. Actual login storage and nonemptyquota/UI acceptance still pending. Next action is the same Start launcher with the VERIFIED changed environment, private user device sign-in, keep Terminal open; root relays only that step.

## Actual Codex acceptance and live dashboard switch, 2026-09-22

Status remains partial overall. Adapter state e3ab9ae produced a valid nonempty actual Codex quota feed after user-reported official sign-in/publication. A bounded Python strict-schema read of only dedicated Claude/Codex quota JSON in /Users/troywitt/AI/Code/ControlTower confirmed allowed percentages, resets and observation ages; a nonblocking lock check confirmed the Codex helper active. Native CUA accessibility comparison PASS: verified release0.4 artifact/hash from UI-ACCEPTANCE-04.md displayed matching actual Claude Session/Weekly and Codex Primary values/resets. Both correctly displayed stale once their observations exceeded five minutes. Personal amounts omitted from public evidence. Only Primary was supplied; duration and Secondary were not inferred.

Version0.2 was quit and version0.4 launched, then both actual quota-folder connections were restored. The original installed app, provider credentials, Claude statusLine and active Codex helper were untouched. No provider refresh/restart or sign-in retry occurred. No claim of saved-login persistence or currently fresh allowance is made. Earlier unavailable/login failures above remain historical evidence, superseded only for actual feed/UI acceptance.

Workspace: documentation-only acceptance update; no unrelated dirty files, no stashes, no live feed writes. Active jobs: reviewed private dashboard0.4 and user-owned Codex helper. User stops that helper with q; preserve it during remaining setup. Lease released after checkpoint commit.

Next single user step: open Bridges/Start Gemini Quotas.command in a private Terminal, complete official Google sign-in/trust personally, then enter /model and leave its quota dialog open. Origin task relays this; do not capture the Terminal or generate a model prompt. Verify only the sanitized Gemini feed and matching dashboard next. Grok remains later; Codex saved-login reuse remains separately unverified.
