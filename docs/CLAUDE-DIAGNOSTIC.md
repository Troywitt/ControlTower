# Claude quota field diagnostic

The optional wrapper diagnostic records only fixed field names, JSON type labels,
and numeric-validity booleans. It never records field values, other input keys,
prompts, paths, credentials, or raw stdin. It does not invoke Claude or a provider.
The existing terminal display and quota behavior remain unchanged.

Opt-in: an owner-only regular `claude-diagnostic.enable` file in the selected feed
directory contains an epoch expiry no more than 900 seconds ahead. Missing,
expired, symlinked, or non-private markers disable recording. Output replaces
`claude-diagnostic.json` atomically with mode 0600; there is no accumulating log.
Delete the marker to stop early, or let it expire. No Claude settings edit is
required. A normal status-line update loads the modified Python wrapper.

Validation: `python3 -m unittest discover -s Tests/BridgeTests -v` passed 13 tests
in `/Users/troywitt/AI/Code/ControlTower` on the diagnostic working tree based on
`682fb39897cb97d19355e0b9b8908fe96425060a`. The negative sentinel test verifies
that secret strings in both expected and unexpected fields cannot be exported;
absent and expired markers produce no new report. `python3 Scripts/security_gate.py`
and `git diff --check` also passed.

Scratch reproduction of the documented numeric Claude rate-limit schema passed.
A following payload without `rate_limits` clears prior quota windows. This is
the current unavailable-state behavior, not evidence that a real session sent
such an update. Empty live windows alone cannot distinguish missing fields from
invalid values. Live account quota acceptance remains partial.
