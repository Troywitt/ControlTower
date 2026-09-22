import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import pty
import select
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Bridges"))
sys.path.insert(0, str(ROOT / ".build/gemini-python"))
from gemini_quota import parse_screen, prepare_state, acquire_feed_lock, stop
import pyte


def screen(rows):
    return ["│ Select Model │", "│ Model usage │", *["│ " + r + " │" for r in rows], "│ (Press Esc to close) │"]


class GeminiTests(unittest.TestCase):
    def test_terminal_loading_then_snapshot_no_reaging_and_quit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            output, state = root / "feed", root / "state"
            loading = "\x1b[2J\x1b[HSelect Model\r\nLoading quotas\r\n(Press Esc to close)"
            ready = "\x1b[2J\x1b[H" + "\r\n".join(screen(["Pro ▬▬▬▬ 12%"]))
            fake = "import sys,time;sys.stdout.write(" + repr(loading) + ");sys.stdout.flush();time.sleep(1.2);sys.stdout.write(" + repr(ready) + ");sys.stdout.flush();time.sleep(1.2);sys.stdout.write(" + repr(ready) + ");sys.stdout.flush();time.sleep(30)"
            code = ("import sys;from pathlib import Path;sys.path.insert(0," + repr(str(ROOT / "Bridges")) + ");"
                    "from gemini_quota import main;sys.argv=['test','--state'," + repr(str(state)) + ",'--output'," + repr(str(output)) + "];"
                    "main(verify=lambda:Path(sys.executable),prepare=lambda state:(state,{'HOME':str(state),'PATH':'/usr/bin:/bin'}),"
                    "command=lambda binary:[str(binary),'-c'," + repr(fake) + "])")
            master, slave = pty.openpty()
            process = subprocess.Popen([sys.executable, "-c", code], stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
            os.close(slave)
            target = output / "gemini.json"
            first = None
            synthetic_output = bytearray()
            deadline = time.monotonic() + 6
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]: synthetic_output.extend(os.read(master, 16384))
                    if target.exists():
                        data = json.loads(target.read_text())
                        if data["windows"]:
                            first = data
                            break
                self.assertIsNotNone(first, synthetic_output.decode(errors="replace"))
                self.assertEqual(first["windows"][0]["usedPercent"], 12)
                time.sleep(1.4)
                self.assertEqual(json.loads(target.read_text())["observedAt"], first["observedAt"])
                os.write(master, b"\x1d")
                deadline = time.monotonic() + 8
                while process.poll() is None and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try:
                            synthetic_output.extend(os.read(master, 16384))
                        except OSError:
                            break
                self.assertIsNotNone(process.poll(), synthetic_output.decode(errors="replace"))
                self.assertEqual(json.loads(target.read_text())["windows"], [])
            finally:
                if process.poll() is None:
                    process.terminate();process.wait(timeout=5)
                os.close(master)

    def test_single_writer_and_cancellation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            first = acquire_feed_lock(root)
            try:
                with self.assertRaises(BlockingIOError): acquire_feed_lock(root)
            finally: first.close()
            acquire_feed_lock(root).close()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
        with patch("gemini_quota.os.killpg", side_effect=PermissionError):
            stop(child)
        self.assertIsNotNone(child.poll())
        with patch("gemini_quota.os.killpg") as kill:
            stop(child)
            kill.assert_not_called()

    def test_rounded_tier_percentages_and_estimated_resets(self):
        result = parse_screen(screen(["Pro ▬▬▬▬ 33% Resets: 1:30 AM (23h 59m)",
                                      "Flash ▬▬▬▬ 0%", "Flash Lite ▬▬▬▬ 100% Resets: 7:00 AM (168h)"]), 1000)
        self.assertEqual([r["usedPercent"] for r in result["windows"]], [33, 0, 100])
        self.assertEqual(result["windows"][0]["resetsAt"], 1000 + 1439 * 60)
        self.assertNotIn("resetsAt", result["windows"][1])

    def test_secret_text_never_exported(self):
        secret = "SECRET_SENTINEL_TOKEN_AUTH_PROMPT"
        result = parse_screen([secret] + screen(["Pro ▬▬▬▬ 12%"]), 1000)
        self.assertNotIn(secret, json.dumps(result))
        for row in [secret, "Pro ▬▬▬▬ 12% " + secret, "Other ▬▬▬▬ 12%", "Pro ▬▬▬▬ 101%",
                    "Pro ▬▬▬▬ 12% Resets: 1:00 PM (2h 99m)"]:
            with self.assertRaises(ValueError): parse_screen(screen([row]), 1000)
        self.assertIsNone(parse_screen([secret, "Login with Google"], 1000))

    def test_duplicates_partial_and_wrapped_fail_closed(self):
        with self.assertRaises(ValueError): parse_screen(screen(["Pro ▬▬▬▬ 12%"] * 2), 1000)
        self.assertIsNone(parse_screen(screen(["Pro ▬▬▬▬ 12%"])[:-1], 1000))
        with self.assertRaises(ValueError): parse_screen(screen(["Pro ▬▬▬▬", "12%"]), 1000)
        with self.assertRaises(ValueError): parse_screen(["x" * 181], 1000)

    def test_ansi_screen_and_redraw_removes_old_data(self):
        target = pyte.Screen(140, 60)
        stream = pyte.ByteStream(target)
        payload = "\x1b[2J\x1b[H" + "\r\n".join(screen(["Pro ▬▬▬▬ \x1b[32m12%\x1b[0m"]))
        stream.feed(payload.encode())
        self.assertEqual(parse_screen(target.display, 1000)["windows"][0]["usedPercent"], 12)
        stream.feed(b"\x1b[2J\x1b[HLogin with Google")
        self.assertIsNone(parse_screen(target.display, 1001))

    def test_isolation_and_no_telemetry(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp).resolve()
            cwd, env = prepare_state(state)
            self.assertNotIn("GEMINI_CLI_HOME", env)
            self.assertNotIn("GEMINI_API_KEY", env)
            self.assertEqual(env["GEMINI_TELEMETRY_ENABLED"], "false")
            self.assertEqual(env["GEMINI_CLI_NO_RELAUNCH"], "1")
            self.assertEqual(env["HOME"], str(state / "home"))
            settings = json.loads((state / "home/.gemini/settings.json").read_text())
            self.assertFalse(settings["privacy"]["usageStatisticsEnabled"])
            self.assertFalse(settings["general"]["enableAutoUpdate"])
            self.assertEqual(settings["context"]["fileName"], [])
            self.assertEqual(settings["context"]["discoveryMaxDirs"], 0)
            self.assertEqual(settings["context"]["memoryBoundaryMarkers"], [])
            for key in ("GEMINI_CLI_SYSTEM_SETTINGS_PATH", "GEMINI_CLI_SYSTEM_DEFAULTS_PATH"):
                self.assertEqual(Path(env[key]).read_text().strip(), "{}")
                self.assertEqual(Path(env[key]).stat().st_mode & 0o777, 0o600)
            self.assertEqual((state / "home/.gemini/settings.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__": unittest.main()
