# Credential-free UI acceptance — 2026-09-22

Result: tested flows passed; menu-bar status-popup activation remains unverified because that surface was not exposed by the native UI tool. No code defect was confirmed and no code/entitlement/auth change was made.

## Artifact and authorization

Troy explicitly approved checking the interface without credentials. Launched separately from `/Users/troywitt/AI/Code/ControlTower/.build/artifacts/review.jZomfe/ControlTower Private.app`; did not install or replace the upstream app. Before launch, Info.plist identity/version/source revision and executable checksum matched the prior verified artifact:

- `com.bodie.controltower.private`, 0.1.0 build 1.
- `CTSourceRevision`: `801ca44dcc190f9213e4a403cde2ea5a9cf4220a`.
- Executable SHA-256: `a1b4a64d7c927ab5376ff47973c5d979f635e2df5b1125c3caba10093f70532e`.
- Checkout at test start: clean, `d6d1b5e7c9821ac57c9cf5b1f9a14ea4121cf387`; source unchanged from the tested implementation. Documentation-only update after QA.

## Observed native UI checks

| Check | Result | Observed evidence |
|---|---|---|
| Disconnected startup | PASS | All six providers show Disconnected; no quota numbers; all Allow local import checkboxes off and import buttons disabled |
| Claude dialog | PASS | Correct fixed Anthropic usage URL; blank secure text field; unchecked consent; Save in Keychain & fetch usage disabled; Cancel returned disconnected |
| Codex dialog | PASS | Correct ChatGPT usage URL; blank secure token field and optional account-ID field; submit disabled; Cancel returned disconnected |
| Gemini dialog | PASS | Correct Google Code Assist quota URL; blank secure token field; Required Code Assist project ID; clear separation from AI Studio billing; submit disabled; Cancel returned disconnected |
| Quota honesty | PASS | Missing data says unavailable; no invented 0%, unlimited allowance, cost or subscription balance |
| Other provider cards | PASS | Cursor, Copilot, Antigravity visibly explain live unavailability; local import controls present, no live-connect buttons |
| Scrolling and layout | PASS | Top dashboard, cards, all three dialog layouts and bottom security limitations readable at the observed window size |
| Import cancel | PASS | Enabled only Antigravity's local-import checkbox, opened picker; Open disabled with no selection; clicked Cancel; no data/count/error appeared; turned opt-in back off |
| Provider More menu | PASS, menu only | Remove saved token entry visible; cancelled the menu without selecting it |
| Standard window/menu behavior | PASS, bounded | Window menu accessible; closed dashboard, app remained running; New Window shortcut restored dashboard with disconnected/default-off state; dismissed menu via native Cancel action |
| Menu-bar status popup / its Open dashboard action | UNVERIFIED | Tool exposed window/app menus but not the status-item popup; no claim that its reopen path was tested |
| Keychain/security prompts | No prompt observed | No token entered, saved token used, credential removal invoked or permission granted during checked flows |
| Live auth / actual quota rendering | NOT RUN | Explicitly outside this approval; no live token/provider calls performed by the tester |

Native screenshots were captured in Codex task `01a0c676-576a-7512-859b-da903fee88b6`: initial dashboard, blank Claude dialog, blank Codex dialog, blank Gemini dialog, bottom three provider cards/security footer. They show only the review app and no credentials. The file picker was deliberately not screenshotted and file-list details were excluded from tool output. No file was selected or opened.

## Runtime evidence limits

The review app ran as PID 46039. Two `lsof -nP -a -p 46039 -i` snapshots returned no rows (exit 1) while disconnected, including after the cancel-only interactions. This means no open network sockets were reported at those two instants; it is NOT continuous traffic capture and cannot prove that no earlier/transient request occurred. Source restrictions and the prior 22 synthetic tests provide separate evidence of no credential/provider I/O before opt-in; the UI alone cannot establish that claim. No Keychain tracing, real credential inspection, TLS interception, packet capture or private-file tracing was performed.

The initial native getApp call took approximately 1931 seconds before returning the running app state. The tool exposed no pending permission explanation or auto-review rejection; the reason for that delay is unknown. After closing the window, window-state reads timed out until New Window restored it; the app remained running. These tool limitations remain visible rather than being marked as application security failures.

At the end the UI tool reported user interaction. The latest state was refreshed: all providers disconnected and all local imports off. The review window was left open for Troy; no further actions were taken against it. Existing `/Applications/ControlTower.app` and its permissions were not changed.

## Next boundary

Credential-free checked flows are accepted within the limits above. Real Keychain enrollment, provider compatibility, live quota display, routine signing/install, and the menu-bar status-popup path remain unverified. No test suite rerun or new binary was needed because this turn changes only QA documentation.
