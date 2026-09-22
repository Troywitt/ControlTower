# Handoff: Claude review of ControlTower Private

## Status
- Status: **partial app delivery; ready for Claude review**. Implementation, tests and prior live acceptance exist. The app is not currently operating as a continuously updating tracker. Do not equate passed tests with current live operation.
- Sender: Codex (GPT-6 Astra), task `01a0c676-576a-7512-859b-da903fee88b6`; lease run `20260922T201747Z-codex-6a657a02`.
- Written UTC: 2026-09-22T20:19:42+00:00
- Repo: `/Users/troywitt/AI/Code/ControlTower`; branch `harden/explicit-quota-access`; reviewed source HEAD before this documentation commit: `873f74a019e222dba0f7deb2bd139940da771bf5`. This handoff is committed after that SHA; use `git log -1` for its commit.
- Remote: `https://github.com/Troywitt/ControlTower.git`; draft PR [#1](https://github.com/Troywitt/ControlTower/pull/1). Keep draft; no merge authorized.
- Authoritative current scope: **Claude and Codex only**. Troy deferred Gemini, Antigravity and Grok, then asked for this handoff so Claude can examine the app. Do not resume deferred onboarding or model research.
- Replies to: prior `docs/HANDOFF.md` (history remains in Git). This document replaces its accumulated and sometimes superseded instructions.

## Read first
1. Read `docs/CLAUDE-CODEX.md`, `SECURITY.md`, `docs/UI-ACCEPTANCE-041.md` and the current source before changing behavior.
2. Run `/Users/troywitt/AI/Meta/claude/bin/agent-lease.sh check`; acquire your own lease before editing. Do not break another live lease.
3. Compare `git status` with Workspace state below. Do not stash/reset/clean others' work.
4. Never inspect auth files, Keychain items, provider logs, raw statusLine stdin, transcripts, populated sign-in screens, device codes or callback URLs. User owns sign-in/trust/MFA. Only strict dedicated quota JSON and nonsecret process/lock metadata are appropriate for live checks.
5. Do not edit global instructions, `.claude/`, `CLAUDE.md` or `/Users/troywitt/AI/Meta`. Do not send prompts to provider models to refresh quota.

## What changed and why
- The shipped target is `ControlTowerLocal`, backed by `Sources/LocalUsageCore`. Historical upstream code in `Sources/ControlTower` and `Sources/ControlTowerCore` is not the current app. The previous token core is test-only; `KeychainVault.swift` is excluded.
- Dashboard: strict quota-only files, App Sandbox plus user-selected read-only folder access; no network, credential lookup, provider launcher, updater or persisted connection bookmarks. Reads selected files every five seconds; observations older than five minutes are stale.
- Claude: `Bridges/claude_statusline.py` and `prepare_claude.py` retain the existing statusLine. Troy applied the setup. Actual published quota and native UI comparison passed. No ongoing process is required from this adapter; updates depend on normal Claude Code statusLine activity.
- Codex: `Bridges/codex_quota.py` launches the verified official binary in a private CODEX_HOME with keyring-only storage requested. Real OS HOME is preserved for macOS default-Keychain lookup; normal Codex config is excluded. Official client owns all authentication. Only allowlisted quota RPCs are exposed.
- `Start Codex Quotas.command` performs official device enrollment in the user's own Terminal, then reads quota. `Resume Codex Quotas.command` reuses saved login, never initiates login. Return refreshes; q/Ctrl+C stops and clears the feed. Keep the helper open while tracking.
- Saved-login reuse was verified through an official quota-only process while the singleton lock was idle. No credential contents were inspected, no new sign-in occurred, and the bounded check wrote no live feed.
- Version0.4.1 (`c87dacc`) adds honest per-card refresh guidance and replaces stale --login instructions with Resume/Start guidance. `873f74a` adds daily-use docs and the reviewed dashboard launcher.
- Deferred Gemini/Grok code remains checked in. Gemini startup query TypeError was fixed in `4964a7d`; no authenticated acceptance completed. Antigravity investigation stopped without source changes. Leave any user-owned deferred sessions alone.

## Current product state and review focus
The latest direct status check, before this handoff, found the reviewed dashboard showing **Claude Disconnected** and **Codex Disconnected**, and the Codex singleton lock idle. Both strict quota files existed but were stale. Claude's file had advanced since the earlier overnight acceptance, establishing later normal activity, but it was still old at the status check. Personal quota amounts are omitted here. Treat current process state as time-sensitive and recheck it safely.

The app is a working **manual-refresh review build**, not a finished, self-maintaining desktop experience. Its main practical gaps are:
- Quitting/reopening loses both folder connections by design; users must choose the dedicated folder again for each provider.
- Codex needs a separate running Terminal and explicit Return refresh. A stopped/crashed helper can leave an old snapshot, correctly labeled stale.
- Claude can be stale while idle; Read snapshot reloads the file and does not fetch provider data.
- The dashboard still displays deferred provider cards. This can distract from the two-provider scope.
- The launcher points to an exact local ignored artifact. A new clone must build, review and deliberately update the artifact pin; it cannot use that machine-local artifact automatically.

Claude's first job is to review these usability and lifecycle gaps against Troy's expectation that the app simply works, while retaining the security boundary. Do not silently add auto-start services, background account polling, persistent access, credential discovery or network capability. Present any such architectural decision before expanding permissions. Fix ordinary authorized implementation defects with focused tests.

## Verification
All commands below ran in `/Users/troywitt/AI/Code/ControlTower`.

| Check | Result | Command/observation | At SHA | Evidence |
|---|---|---|---|---|
| Current test suite and source boundary | PASS | `bash Scripts/test_private.sh` | `873f74a` | 29 Swift tests in 5 suites; 39 Python tests; `/tmp/controltower-claude-handoff-tests.log` |
| Reviewed launcher | PASS | `zsh 'Bridges/Open ControlTower Private.command' --check` | `873f74a` | Exact hash, strict signature, source/payload/entitlement gate; did not open app |
| Codex launcher syntax | PASS | `zsh -n 'Bridges/Start Codex Quotas.command' 'Bridges/Resume Codex Quotas.command'` | `873f74a` | Exit0 |
| Diff formatting | PASS | `git diff --check` | `873f74a` plus handoff docs | No errors |
| Release build | PASS, prior observation | `bash Scripts/build_private.sh` | `c87dacc` | `/tmp/controltower-041-build.log`; exact artifact below |
| Actual Claude/Codex feed-to-UI comparison | PASS, prior observation | Strict sanitized feed read + native0.4 accessibility comparison | adapter `e3ab9ae`; documented `9f86feb` | `docs/UI-ACCEPTANCE-04.md` |
| Official Codex saved-login reuse | PASS, prior observation | Idle-lock-protected initialize + account/rateLimits/read, validated quota, owned-process cleanup | `873f74a` source state | `docs/UI-ACCEPTANCE-041.md`; no live feed write |
| Current connected/fresh operation | NOT PASSED | Latest native UI + strict feed/lock read | `873f74a` | Both disconnected; Codex helper stopped; files stale. Requires reconnection and normal provider updates |

Reviewed artifact: `.build/artifacts/review.RlknAq/ControlTower Private.app`, version0.4.1/build5. Embedded source revision `c87dacc9e8baa42bdec92ca362f51fb2a7e1befd`. Executable SHA-256 `ae19c16b49bca53498937c17c711a5763771bfeb27787ce03de0975db0d58c94`.

## Assumptions and unknowns
- Codex exports Primary/Secondary without window duration. Do not relabel Primary as five-hour or weekly; missing Secondary is not zero usage.
- Saved login worked in the observed run; indefinite future validity is not guaranteed. Official client may request sign-in later.
- Same-user local tampering is outside the JSON boundary; quota files are not cryptographically authenticated.
- Official provider processes have normal user privileges outside the dashboard sandbox. Feature flags are not a universal filesystem firewall.
- Ignored build/runtime artifacts and provider state are intentionally not in Git. No secrets, live feeds, provider homes, binaries or raw logs should be committed.
- No current assumption that any old Terminal PID is still the same process. Revalidate lock/process metadata before any recovery action.

## Remaining work
- [ ] Review the app and report concrete correctness/usability issues, prioritizing the manual reconnect/helper lifecycle.
- [ ] Restore Claude and Codex folder selections, with user coordination if they are manipulating the chooser.
- [ ] User opens Resume Codex Quotas.command once, leaves it open and refreshes with Return. Verify only sanitized feed and actual matching UI; do not inspect the private Terminal.
- [ ] Observe Claude after ordinary user activity; do not make a model call solely to freshen it.
- [ ] Resolve review findings within approved scope, then verify an ordinary close/reopen workflow and clearly state its remaining manual steps.
- Failed attempts retained: isolated Codex HOME broke default-Keychain lookup (fixed by real HOME/private CODEX_HOME); generic errors obscured sign-in failures (fixed categories); Gemini pyte private-query TypeError fixed but provider deferred; normal Gemini trust-restart exit199 was expected; duplicate Gemini launch hit a live lock and was left alone; build dsymutil sandbox denial resolved by targeted Apple build-tool escalation; Codex folder-chooser automation paused when user changes were detected. Never bypass a live singleton lock.
- Blockers: current user-owned provider/session state and incomplete everyday-use experience. No source/test failure is currently known.
- **Next action:** read this handoff and inspect the active target, then perform a focused Claude/Codex review. No Google/Grok work and no new sign-in without a demonstrated need.

## Workspace state
- At start: clean working tree at873f74a; no unrelated dirty/untracked files. This handoff and its root pointer are the only new work in this turn.
- All source, tests, launchers and documentation from this task are committed. Final handoff commit is pushed to origin/harden/explicit-quota-access; confirm equality with `git ls-remote origin refs/heads/harden/explicit-quota-access` and `git rev-parse HEAD`.
- Stashes: none created. No source deletions, resets, cleans, installations or login items.
- Running jobs: no agent-owned background jobs left. Reviewed dashboard was opened for status inspection; it may remain open. Codex helper was stopped at latest check. Deferred user sessions were not inspected or stopped.
- Live data: only bounded sanitized quota JSON and lock metadata read. Files under `/Users/troywitt/Library/Application Support/ControlTowerPrivate/quota-feed`; do not select provider-state directories in the dashboard. No live state modified or copied for this handoff.
- Lease: Codex releases after final commit/push verification. Claude must acquire a new lease before editing.
