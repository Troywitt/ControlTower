# Claude and Codex: daily use

Both providers have passed actual quota-to-dashboard checks. Codex also passed a later saved-login quota read without another sign-in. This tracker uses manual observations; it does not continuously fetch account quotas.

1. Open `Bridges/Open ControlTower Private.command`. It verifies and opens the exact reviewed dashboard. It does not install, start providers or change login items.
2. After each dashboard launch, use **Choose quota-feed folder…** in the Claude and Codex cards. Select `/Users/troywitt/Library/Application Support/ControlTowerPrivate/quota-feed` for both. Connections last until disconnect or quit.
3. Claude's existing statusLine connection is already set up. Continue normal Claude Code use; a supported statusLine update publishes new percentages. No extra model request is needed just for this tracker.
4. For Codex, open `Bridges/Resume Codex Quotas.command` once and leave that Terminal open. It reuses the separate saved login. **Return** requests a new quota observation; **q** or Ctrl+C stops the helper and clears its feed. Use **Start Codex Quotas.command** only for enrollment if the saved login is unavailable.

**Read snapshot** reloads the local file; it does not contact a provider. The dashboard checks the selected folder every five seconds. An observation older than five minutes is marked **Stale** and is not a claim about current allowance. If a helper terminates abruptly, an old file may remain and age into stale.

Codex's **Primary** label is preserved because the exported data does not include its window duration. A missing Secondary window is not zero usage. Reset times describe the recorded observation; a past reset on stale data does not establish a current quota.

Dashboard **Disconnect** stops file reads only. Quitting the dashboard does not quit the Codex helper. If another helper already owns the Codex lock, return to its Terminal instead of launching a second copy.

No provider credentials are entered in the dashboard. It has only App Sandbox and user-selected read-only file access, with no network or provider-process capability. Official provider software owns sign-in. The original installed ControlTower app is untouched.

Gemini, Antigravity and Grok are deferred. Their code and sessions have been left in place.
