# Security design and remaining limits

## Protected behavior in the active build

- Starts with no live or local-import consent and no source I/O. It does not inspect environment variables, home directories, sign-in files, browser cookies, another app's Keychain items, or running processes.
- Enrollment is an explicit per-provider action. Token syntax is checked per provider before persistence or transport; this is NOT cryptographic validation or proof of limited scope. Only an access token and optional account/project identifier enter the app-owned Keychain adapter. No refresh token is parsed, stored or renewed.
- Fixed Keychain service `com.bodie.controltower.private.access-tokens.v1`; fixed accounts from the Provider enum; non-synchronizable generic-password entries. macOS login Keychain default signed-app access control. No caller-controlled service/key/query, access-group sharing, plaintext fallback or credential logger. Background reads use `LAContext.interactionNotAllowed`; failure disconnects rather than repeatedly asking.
- The broker and UI share MainActor. Disconnect revokes consent synchronously, cancels the transport task and advances a generation number. Late responses are discarded even if a transport ignores cancellation. No new credential reads or requests while disconnected. The already transmitted portion of a request cannot be recalled.
- Refresh is manual and coalesced. Every error stops the connection until explicit opt-in. No retry/fallback/token-refresh loops. A separate local-import opt-in gates the file panel and reader; disabling clears local rows. Default reads are zero.
- No third-party package dependencies. The historical upstream sources are excluded by a small explicit package manifest. Static gate checks target names, forbidden discovery/process/logging APIs, endpoint set, and minimal entitlements. App bundle gate checks exact payload, identity and system-only dynamic libraries. These are regression checks, not proofs against a malicious future code change.

## All outbound requests

| Provider | Exact HTTPS destination | Method | Credential and non-secret payload |
|---|---|---|---|
| Claude | `https://api.anthropic.com/api/oauth/usage` | GET | Authorization bearer; fixed OAuth beta header |
| Codex | `https://chatgpt.com/backend-api/wham/usage` | GET | Authorization bearer; optional explicit ChatGPT account ID header |
| Gemini | `https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota` | POST | Authorization bearer; JSON containing only explicit project ID |

No user-controlled URL, port, path, query, proxy, User-Agent or header name. All redirects, same-origin and cross-origin, are denied. Only normal system TLS trust is accepted; HTTP password/client-certificate challenges are refused. Ephemeral URLSession has no URL cache, cookie jar, credential storage or cookie handling. Responses are limited to 128 KiB while streaming and 30 seconds overall. Status errors discard response bodies; parser errors return fixed messages. No explicit logging, raw response retention, analytics, crash-upload SDK or updater in active code.

Gemini route/request shape corresponds to Google's [Code Assist server source](https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/code_assist/server.ts) (`retrieveUserQuota`, POST). Only this route is implemented: no project discovery, provisioning, model generation or billing operations. Claude/Codex routes derive from reviewed upstream source; they are not established as supported third-party public APIs. Missing windows/buckets remain unavailable, never zero usage. Real-token compatibility has NOT been exercised.

## What we cannot guarantee

This is risk reduction, not attack-proofing. App Sandbox limits filesystem access but its network entitlement is not an OS host allowlist: exact destination enforcement lives in reviewed code. A compromised in-process library or modified app can bypass code checks. The enrollment UI necessarily sees what the user pastes, and Swift strings cannot be reliably zeroized; token bytes temporarily exist in UI/broker/URLSession memory. Keychain protects at-rest storage, not a compromised app or Mac. Default OS trust and proxy settings apply; a locally trusted TLS interception certificate is inside the OS trust boundary. We did not inspect or change the user's trust/proxy settings.

We assessed a separate XPC broker. It could remove network and Keychain authority from the dashboard process and reduce a UI-compromise blast radius. It would still have to authenticate callers and protect a broker holding a powerful bearer token. A trustworthy stable caller-signature policy, helper packaging and durable signing/provisioning add materially more setup than this ad-hoc personal review build. This version deliberately makes no OS-isolation claim. A separately signed broker is a reasonable next step before broader distribution or if in-process separation is insufficient for the user.

No documented provider-issued read-only personal quota token or registered third-party OAuth client was established. A usage request does not reduce the token's original authority. This advanced connection cannot offer seamless provider login or reliable automatic renewal. If a provider changes its token format, scopes or internal endpoint, this build fails closed and requires code review; do not weaken checks or introduce scraping just to reconnect. No actual account or provider-contract verification was performed.

The app is ad-hoc signed, not notarized. Codesign verification confirms the artifact's integrity/entitlements at inspection time, not benevolence or future-update safety. For routine use, review the code and complete user-driven real-Keychain/sign-in acceptance; a stable developer signing identity is preferable. No automatic updater or old Homebrew route remains active.

## Private local data

Only a user-selected regular `.json` aggregate file is read (no directory traversal, automatic scan or bookmarks). Reads use O_NOFOLLOW, reject special files and are bounded to 4 MiB. Strict schema rejects unexpected fields, invalid counts/dates, duplicates and unbounded labels. No prompts, conversation content, credential objects or user identifiers are expected in the schema. An incorrectly selected file is read to validate it, so users should choose a prepared aggregate export, not auth files. Import content, paths, token values and response bodies are never logged. Only validated rows stay in app memory, cleared on disconnect/import opt-out/quit. No export or upload feature exists.

## Validation

Synthetic broker spies assert no credential/network calls on startup, unavailable providers or after disabling. Tests cover revocation and late-response rejection, per-provider opt-in, missing data, API-key/header-injection mistakes, conservative Gemini buckets, secret-redacted descriptions/errors, exact endpoints/methods, ephemeral configuration, same/cross-host redirect rejection, and intercepted URLSession responses. No test reads actual Keychain values or calls a provider. Final command/revision evidence is in docs/HANDOFF.md.
