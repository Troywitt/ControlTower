# Handoff: ControlTower Private review build

## Status
- Status: partial — implementation/synthetic verification and signed review build passed; no live credential enrollment or installed-app acceptance.
- Sender / tool / run id: Codex GPT-6 Astra, task 01a0c676-576a-7512-859b-da903fee88b6.
- Written (UTC): 2026-09-22.
- Repo and exact checkout: `/Users/troywitt/AI/Code/ControlTower`, branch `harden/explicit-quota-access`, implementation HEAD `801ca44dcc190f9213e4a403cde2ea5a9cf4220a`. Later commit changes this verification document only.
- Authoritative plan: docs/HARDENING-PLAN.md; security boundary: SECURITY.md.
- Replies to: originating task 01a0c670-a5f0-7a31-9f26-2b459686ea85, read-only v1.0.1 audit, then authorization for fork/hardening and Claude/Codex/Gemini tracking.

## Read first
1. SECURITY.md — no guarantee against app/OS compromise; same-process broker and manual access-token enrollment, not a provider sign-in implementation.
2. `/Users/troywitt/AI/Meta/claude/bin/agent-lease.sh check` — do not edit while another tool holds a live lease.
3. Compare git status with workspace state below. Only the new manifest's targets are active; do not build/run historical upstream code.

## What changed and why
- Fork: `https://github.com/Troywitt/ControlTower`; base upstream v1.1.0 `9b9afbfd978500cbf10f0e7b50efcd8b56b44304`.
- New dependency-free active targets replace the original provider/UI build. Upstream historical code remains excluded for provenance.
- Explicit per-provider enrollment, own Keychain service, zero startup discovery, fixed usage endpoints, all redirects denied, no raw-error/secret logging, manual refresh and synchronous revoke/cancellation.
- Claude/Codex optional live quota windows; Gemini optional Code Assist model quotas with explicit project. Cursor/Copilot/Antigravity live paths unavailable for documented reasons; all six accept opt-in local aggregate exports.
- Separate identity `com.bodie.controltower.private`; App Sandbox plus only network-client and user-selected read-only entitlements. No updater, unsafe runtime exceptions, original installer or automatic app launch.

## Verification
All commands below ran in `/Users/troywitt/AI/Code/ControlTower` at implementation SHA `801ca44dcc190f9213e4a403cde2ea5a9cf4220a`.

| Check | Result | Command | Evidence |
|---|---|---|---|
| Synthetic tests | PASS | `CLANG_MODULE_CACHE_PATH=/tmp/controltower-clang-cache SWIFTPM_MODULECACHE_OVERRIDE=/tmp/controltower-swift-cache swift test --disable-sandbox` | `/tmp/controltower-801ca44-tests.log`: 22 tests / 4 suites passed; fake vaults and intercepted URLSession only |
| Release build and signed app boundary | PASS | `Scripts/build_private.sh` | `/tmp/controltower-801ca44-build.log`: build complete, signed artifact gate PASS, review artifact prepared; no launch/install |
| Source boundary | PASS | `python3 Scripts/security_gate.py` | Exact endpoint set, active targets, no packages/discovery/CLI/logging and exact entitlement set |
| Signature integrity | PASS | `codesign --verify --strict <artifact>` (called by build script) | Successful exit; subsequent entitlement and bundle gate passed |
| Independent read-only review | PASS, bounded | Reviewer inspected active targets and packaging after fixes | Initial weak token-shape and UI revoke-race findings resolved; no new concrete source blocker in re-review. Not a whole-system audit |
| Live Keychain / provider login / UI | NOT RUN | None | Requires user-controlled next step; no actual credentials used |

Artifact: `.build/artifacts/review.jZomfe/ControlTower Private.app`. Pointer: `.build/artifacts/latest-path.txt`. Version 0.1.0 build 1. Info.plist `CTSourceRevision` matches implementation SHA above. Main executable SHA-256: `a1b4a64d7c927ab5376ff47973c5d979f635e2df5b1125c3caba10093f70532e`. Extracted signed entitlements in `.build/artifacts/review.jZomfe/entitlements.plist`: app-sandbox=true, files.user-selected.read-only=true, network.client=true; no other entitlements. Artifact payload gate accepted only the main executable, Info.plist and code resources; dynamic libraries are system libraries only.

## Assumptions and unknowns
- ASSUMED: user accepts manual refresh and advanced explicit short-lived access-token setup for this review build. If seamless login/renewal is essential, a separate supported-auth design is needed.
- UNKNOWN: real account token compatibility, scopes, correct Gemini Code Assist project, provider support for these internal endpoints. Blocks real-account acceptance: yes; blocks synthetic review build: no.
- UNKNOWN: ad-hoc signed app's real Keychain UX/persistence across rebuilds. Prefer stable user-controlled signing before routine enrollment. No identity/certificate was selected from user Keychain.
- Residual risk: same-process broker, OS trust/proxies and non-zeroizable Swift token strings. TLS is standard macOS trust; no bypass/pinning or system-policy changes. Network host restriction is code-level, not an OS firewall.

## Remaining work
- [ ] User review of draft PR/security boundary and choice to proceed to isolated UI/Keychain/live-provider acceptance.
- [ ] Verify actual provider setup using user-controlled enrollment (no tokens in chat); inspect real usage/error UX, then assess routine signing/install.
- Failed attempts retained: sandbox initially blocked compiler cache/dsymutil; redirected temporary caches and authorized build outside tool sandbox resolved it. CLT lacked XCTest; switched to bundled Swift Testing. SwiftUI State macro unavailable in CLT; used ObservableObject/StateObject. First artifact parser received human-readable codesign output; corrected XML export. No security checks were relaxed.
- Blockers: no implementation blocker; live acceptance intentionally not performed.
- **Next action:** review the prepared artifact/PR before authorizing any real-token use or installation. Do not replace `/Applications/ControlTower.app` automatically.

## Workspace state
- Dirty or untracked files and owner: this verification document is Codex-owned until committed; all implementation committed. Build artifacts ignored.
- Stash ids: None.
- Running jobs: None after final verification.
- Live data touched / snapshots: None. No credentials, auth files, cookies, transcripts, app DBs or existing app permissions accessed or changed. Only public upstream metadata/source and synthetic tests.
- Lease: Codex acquired before edits; release at end of task after PR preparation.
