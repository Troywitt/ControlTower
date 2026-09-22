# Optional local aggregate imports

Enable local imports separately, then select one JSON file. Import replaces existing rows for that provider; values are held in memory only. The file must contain an array with exactly these fields per row:

```json
[
  {
    "id": "synthetic-day-1",
    "provider": "gemini",
    "date": "2026-09-21",
    "model": "gemini-example",
    "inputTokens": 1000,
    "cachedInputTokens": 200,
    "outputTokens": 300
  }
]
```

Provider: `claude`, `codex`, `gemini`, `cursor`, `copilot`, or `antigravity`, matching the card. IDs must be unique per file. ID/model labels accept only letters, digits, dot, underscore and hyphen (80 characters maximum). Dates are real YYYY-MM-DD dates from 2000–2200. Counts are nonnegative integers, each at most 1 trillion. Maximum 10,000 rows / 4 MiB.

**inputTokens excludes cachedInputTokens** so the sum does not count cached input twice. outputTokens includes reasoning tokens where those are a subset. Exporters must normalize source semantics and avoid counting repeated/mirrored events before creating the file. This app does not generate or scan transcripts to produce exports. Do not include emails, account IDs, prompts, secrets, paths or conversation text.

Rates entered in the UI are USD per million tokens. One rate set applies to all rows; for meaningful mixed-model cost comparisons use one model per export or rates appropriate to your aggregate. Costs are API-equivalent estimates, not actual subscription charges or remaining allowance. Zero/unknown rates do not establish zero spend.
