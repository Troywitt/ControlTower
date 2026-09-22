# ControlTower Private

A review fork of ControlTower with provider-owned sign-in and a sandboxed quota dashboard. **Partial: actual Claude and Codex quota display is verified in version 0.4. Gemini and Grok account enrollment and dashboard acceptance remain pending. Codex saved-login reuse remains unverified.**

- **Claude:** official statusLine quota fields → bounded quota-only local feed. Preserves existing statusLine; user reviews/applies setup. No token copying.
- **Codex:** user-started local helper → official signed Codex device login and `account/rateLimits/read` → quota-only feed. Separate provider home, Keychain-only requested, manual refresh, no model calls.
- **Grok:** user-owned official CLI sign-in and `/usage` SuperGrok weekly display → strict quota-only feed. Live screen compatibility remains pending.
- **Gemini:** user-owned official CLI sign-in and interactive `/model` screen → strict quota-only feed. Rounded tier percentages and estimated resets; no generated model prompts.
- Other providers retain explanatory unavailable states and optional explicit aggregate token-count imports. Imports are not subscription quotas.

Start with [PROVIDER-SETUP.md](docs/PROVIDER-SETUP.md). Read [SECURITY.md](SECURITY.md) before sign-in. No installer replaces the original app, changes Claude settings, signs in or accesses provider credentials automatically.

```bash
Scripts/test_private.sh
Scripts/build_private.sh
```

The build writes a fresh `ControlTower Private.app` under `.build/artifacts/`; it does not launch or install it. The dashboard has only App Sandbox and user-selected read-only file entitlements. Adapters in `Bridges/` run separately under user control; they are not protected by the dashboard's sandbox. Setup requires Python 3 and the reviewed official Codex binary. Gemini also uses an app-local pinned npm runtime and Python terminal parser; see setup instructions. This remains a review workflow, not one-click onboarding.

Historical upstream sources are excluded. The previous manual-token core is in a separate test-only target and is not shipped in the dashboard. `KeychainVault.swift` is excluded from the executable. The UI has no secret entry or direct provider request path. Previous credential-free UI evidence in `docs/UI-ACCEPTANCE.md` applies to version 0.1 only.

Fork base: upstream v1.1.0 (`9b9afbfd978500cbf10f0e7b50efcd8b56b44304`). Original license/attribution retained.
