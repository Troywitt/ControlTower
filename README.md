# ControlTower Private

A security-focused personal fork of [ControlTower](https://github.com/krishcdbry/ControlTower), based on upstream v1.1.0. Explicit connections for Claude, Codex and Gemini usage. No silent credential discovery, browser-cookie import, provider CLI execution, telemetry, or automatic updates.

**Review build, not yet approved for real-token enrollment.** Synthetic tests and artifact checks do not prove live authentication, safe operation on a compromised Mac, or provider support for third-party quota clients. Nothing here is a promise of absolute safety.

## What works in this build

| Provider | Available feature | Setup and limits |
|---|---|---|
| Claude | Provider-reported session/weekly/model quota windows | Explicit access-token connection; short-lived Claude OAuth token shape; compatibility untested with your account |
| Codex | Provider-reported primary/secondary account quota windows | Explicit ChatGPT session access token; optional account ID; not an OpenAI API billing dashboard |
| Gemini | Code Assist per-model quota buckets | Explicit Google access token and Code Assist project ID; not AI Studio API usage/billing or a universal Gemini balance |
| Cursor | Local aggregate imports only | Live browser-session-cookie integration excluded |
| Copilot | Local aggregate imports only | Upstream inferred unlimited usage from GitHub login; this build refuses that unsupported claim |
| Antigravity | Local aggregate imports only | Process inspection, service-token extraction and relaxed localhost TLS excluded |

All connections start off **every launch**. No credential availability probe happens on startup. Click **Connect with access token…** only after reviewing [SECURITY.md](SECURITY.md); this is an advanced manual connection, not an implemented OAuth sign-in flow. Token-format checks reject common mistakes but cannot prove a token's authority or scope. The token is stored only in this app's own macOS Keychain entry. No passwords, refresh-token renewal, plaintext token files or fallback credential sources.

Refresh is manual. Disconnect synchronously closes the consent gate, cancels pending work, discards late responses and blocks future reads/requests. A request already sent cannot be recalled. Saved tokens remain in Keychain until **More → Remove saved token**. **Use saved token** is an explicit new opt-in, not automatic restoration.

For historical counts, enable **Allow local import** and select a strict aggregate JSON export. No transcripts or directories are scanned. Imports replace that provider's prior rows and stay in memory only. See [aggregate format](docs/AGGREGATE-FORMAT.md). Estimates use rates you enter and are neither subscription quota nor an actual bill.

## Build and verify

Requires macOS 14+, Swift 6 and a matching macOS SDK (full Xcode recommended; recent Command Line Tools may support Swift Testing). The active package has **zero third-party dependencies**. Only `LocalUsageCore` and `ControlTowerLocal` are built. Historical upstream source and tests are preserved for provenance but excluded from all current targets; never ship binaries built from the old manifest.

```bash
swift test --disable-sandbox
python3 Scripts/security_gate.py
Scripts/build_private.sh
```

`--disable-sandbox` concerns the Swift build tool's subprocess sandbox, not the shipped app: the packaging script explicitly signs the app with App Sandbox enabled. It produces a fresh `.build/artifacts/review.*/ControlTower Private.app`, verifies its signature, checks its entitlements and linked libraries, and records the path in `.build/artifacts/latest-path.txt`. It **does not launch, install, kill an existing app, or touch credentials**. The old `compile_and_run.sh` now delegates to this build-only script.

Do not run the bare SwiftPM executable as the secure app: SwiftPM alone does not apply App Sandbox. Use only the verified `.app` artifact. Local artifacts are ad-hoc signed for review, not notarized or signed with a durable Developer ID. Rebuilding can alter Keychain trust; real Keychain storage/retrieval and UI acceptance remain explicit user tests before routine use. No Homebrew install/upgrade formula is supplied.

## Security boundary

The packaged app is sandboxed with only outbound networking and user-selected **read-only** file access. There are no JIT, unsigned-memory or disabled-library-validation exceptions. The credential broker is a small internal component and sends tokens only to three fixed HTTPS usage endpoints, rejecting all redirects. It is **in the same process as the UI**, not an OS-isolated vault. A compromised application process or OS can still expose credentials. The app trusts macOS TLS roots and network configuration; it does not bypass corporate proxies or use certificate pinning.

Read [security design and residual risks](SECURITY.md), [implementation plan](docs/HARDENING-PLAN.md), and [verification/handoff](docs/HANDOFF.md) before enrollment. MIT license and original attribution retained.
