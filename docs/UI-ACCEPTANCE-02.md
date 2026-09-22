# 0.2 synthetic native UI acceptance — 2026-09-22

**PASS, bounded synthetic workflow; real-account acceptance NOT RUN.**

Source `e7227b46ae0812ad3bfaa95faabcce33972d3701`; production review bundle `.build/artifacts/review.iKiDno/ControlTower Private.app` passed signed payload/entitlement gate. For UI testing, copied its compiled app to `.build/quota-ui-qa/ControlTower Quota QA.app`, changed only QA bundle identity/name and re-signed with the same sandbox/read-only entitlements. QA bundle ID `com.bodie.controltower.quota-qa` ensures the potentially user-populated 0.1 app is not inspected or closed. This identity difference limits the test: production identity launch/account behavior is not accepted here.

Native CUA results were observed in task `01a0c676-576a-7512-859b-da903fee88b6`. No screenshots or accessibility of user credential fields were taken; the new UI has no credential fields. Folder picker listings were suppressed; only navigation controls were returned. The selected path was generated synthetic fixtures `.build/quota-ui-qa/feed`, not user files.

| Action | Observed result |
|---|---|
| Launch QA app | All providers disconnected, local imports off; no manual-token controls |
| Select Claude synthetic quota folder | `Watching quota feed`, Session25.0%, Weekly40.0%, observation timestamp |
| Atomically replace Claude file without clicking refresh | After >5sec,45.0% shown and removed weekly window disappeared |
| Publish timestamp600sec old | `Stale — last observation is over five minutes old. Current allowance is unknown; refresh through the provider adapter.` |
| Publish empty windows | Previous percentage removed; provider quota unavailable message displayed |
| Disconnect Claude | Disconnected; quota removed |
| Select Codex synthetic folder | Primary15.0% from fixed codex.json; observed stale label because fixture had aged |
| Disconnect Codex | Disconnected; quota removed |
| Open Claude Setup instructions | Numbered provider-owned setup instructions, no secret-entry field, explicit no-account-acceptance statement |
| Close sheet and quit QA app | Disconnected state before quit; QA bundle absent in app inventory after Cmd+Q |

No official provider process was started for these UI checks. No credentials, account requests, real Keychain enrollment or saved-token reuse. Exact user steps and Gemini blocker remain in PROVIDER-SETUP.md. Menu-bar status popup and real-account flows are outside this test. The old0.1 app was not touched and its current state is unknown.
