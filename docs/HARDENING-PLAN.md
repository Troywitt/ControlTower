# Explicit quota access and local usage plan

Scope: authorized fork, local implementation, synthetic verification, signed review artifact and PR. No live credentials, auth files, cookies, user transcripts, Keychain permissions, /Applications replacement, installation or provider sign-in.

Base: upstream v1.1.0, 9b9afbfd978500cbf10f0e7b50efcd8b56b44304. The initial v1.0.1 audit is the starting evidence; current Gemini/Codex/Copilot paths were reread. Existing source is retained but no longer built by the active package.

Final requirements incorporate Troy's clarifications: credential protection takes priority; live Claude/Codex quotas retained through explicit opt-in; Gemini included; other integrations kept only where they can meet the same boundary. A plaintext file was a suggestion, not required. Use own Keychain entries and access tokens, no reuse of refresh tokens, no background discovery, no provider CLI or cookie/probe fallback. Start disconnected; make disabled/no-I/O real. Manual refresh only; missing data unavailable.

Implementation chunks:
1. Minimal dependency-free core: provider endpoint policy, numeric response parsing, consent/revocation broker, Keychain-only adapter and error redaction.
2. Standalone SwiftUI dashboard and explicit enrollment with format checks and honest scope limits. Gemini requires an explicit project. Cursor/Copilot/Antigravity live modes unavailable with concrete reasons. Optional strictly selected aggregate imports and user-entered cost rates.
3. Signed sandbox app packaging with distinct identity, no updater/legacy installation route, only network-client and selected-file read-only entitlements. Never run/install the build automatically.
4. Synthetic tests, security gate and independent review; resolve findings, record exact revision and evidence; PR to the user's fork, no upstream changes.

Acceptance evidence and status live in HANDOFF.md. Same-process broker is deliberately not described as an isolated helper; token authority, system trust, short expiry, ad-hoc signing and untested live setup are material limits documented in SECURITY.md.
