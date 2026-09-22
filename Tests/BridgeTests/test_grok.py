import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
import os
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Bridges"))
from grok_quota import parse_screen, validate_inspection


def fixture(header="Weekly limit (SuperGrok)", percent=50, reset="May 29, 00:00"):
    content = ["Context usage   Usage limit   Session info", "", header, "",
               "█" * 15 + "░" * 15 + "  " + str(percent) + "%", "Resets: " + reset,
               "", "Tab switch   Esc close"]
    return ["     │" + line.ljust(70) + "│" for line in content]


class GrokTests(unittest.TestCase):
    now = datetime.datetime(2026, 5, 22, 1).timestamp()

    def test_source_fixture_weekly_subscription_only(self):
        result = parse_screen(fixture(), self.now)
        self.assertEqual(result["windows"], [{"id": "Weekly", "usedPercent": 50,
            "resetsAt": datetime.datetime(2026, 5, 29).timestamp()}])
        for header in ("Weekly limit", "Monthly limit", "Usage", "Monthly limit (API)", "Weekly limit (Other)"):
            self.assertIsNone(parse_screen(fixture(header=header), self.now))

    def test_dst_ambiguity_omits_reset(self):
        try:
            with patch.dict(os.environ, {"TZ": "America/Los_Angeles"}):
                time.tzset()
                now = datetime.datetime(2026, 10, 30, 12).timestamp()
                result = parse_screen(fixture(reset="Nov 01, 01:30"), now)
                self.assertEqual(result["windows"][0]["usedPercent"], 50)
                self.assertNotIn("resetsAt", result["windows"][0])
        finally:
            time.tzset()

    def test_no_identity_or_other_fields_exported(self):
        secret = "SECRET_SENTINEL_ACCOUNT_TOKEN"
        lines = [secret] + fixture() + [secret]
        self.assertNotIn(secret, json.dumps(parse_screen(lines, self.now)))
        with self.assertRaises(ValueError): parse_screen(fixture(reset=secret), self.now)
        self.assertIsNone(parse_screen(["Sign in " + secret], self.now))

    def test_incomplete_conflicting_invalid_and_date_boundary(self):
        self.assertIsNone(parse_screen(fixture()[:-1], self.now))
        self.assertIsNone(parse_screen(fixture() + fixture(), self.now))
        with self.assertRaises(ValueError): parse_screen(fixture(percent=101), self.now)
        with self.assertRaises(ValueError): parse_screen(fixture(reset="May 30, 23:59"), self.now)
        now = datetime.datetime(2026, 12, 30, 12).timestamp()
        result = parse_screen(fixture(reset="Jan 02, 00:00"), now)
        self.assertEqual(result["windows"][0]["resetsAt"], datetime.datetime(2027, 1, 2).timestamp())

    def test_configuration_preflight_rejects_external_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp).resolve()
            data = {key: [] for key in ("hooks", "plugins", "mcpServers", "lspServers", "projectInstructions", "skills")}
            data["agents"] = [{"source": {"type": "builtin"}}]
            data["configSources"] = {"layers": [{"role": "user", "path": str(state / "home/.grok/config.toml")}]}
            validate_inspection(data, state)
            for key in ("hooks", "mcpServers", "projectInstructions", "skills", "agents"):
                changed = dict(data);changed[key] = [{"source": {"type": "user", "path": "/outside"}}]
                with self.assertRaises(ValueError): validate_inspection(changed, state)
            data["configSources"]["layers"].append({"role": "system-managed", "path": "/etc/grok/policy.toml"})
            with self.assertRaises(ValueError): validate_inspection(data, state)


if __name__ == "__main__": unittest.main()
