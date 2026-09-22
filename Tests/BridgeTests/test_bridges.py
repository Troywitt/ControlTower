import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Bridges"))
from quota_feed import claude_feed, codex_feed, publish
from prepare_claude import prepare
from codex_quota import RPC, launch


class BridgeTests(unittest.TestCase):
    def test_export_is_allowlist_not_input_dump(self):
        result = claude_feed({"transcript_path": "PRIVATE", "token": "PRIVATE", "rate_limits": {
            "five_hour": {"used_percentage": 23, "resets_at": 1234}, "seven_day": None}}, now=100)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(result["windows"], [{"id": "Session", "usedPercent": 23, "resetsAt": 1234}])
        self.assertEqual(claude_feed({})["windows"], [])
        for bad in (True, -1, 101, float("nan")):
            with self.assertRaises(ValueError):
                claude_feed({"rate_limits": {"five_hour": {"used_percentage": bad}}})

    def test_codex_buckets_and_secret_fields(self):
        result = codex_feed({"account": "PRIVATE", "rateLimitsByLimitId": {
            "spark": {"primary": {"usedPercent": 99}},
            "codex": {"limitId": "codex", "primary": {"usedPercent": 22}, "secondary": None}}})
        self.assertEqual(result["windows"], [{"id": "Primary", "usedPercent": 22}])
        self.assertNotIn("PRIVATE", json.dumps(result))
        with self.assertRaises(ValueError):
            codex_feed({"rateLimitsByLimitId": {"spark": {}}})

    def test_atomic_output_and_private_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            # /var can be a symlink on macOS: canonicalize the test root.
            directory = Path(temp).resolve()
            publish(directory, claude_feed({}))
            target = directory / "claude.json"
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            before = target.stat().st_ino
            publish(directory, claude_feed({}))
            self.assertNotEqual(before, target.stat().st_ino)
            link = directory / "link"
            link.symlink_to(directory, target_is_directory=True)
            with self.assertRaises(ValueError):
                publish(link, claude_feed({}))

    def test_preserves_existing_statusline_without_other_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            original = {"type": "command", "command": "printf original", "padding": 2, "refreshInterval": 10}
            settings = {"statusLine": original, "env": {"TOKEN": "PRIVATE"}}
            prepare(settings, root / "review", root / "feed")
            patch_data = json.loads((root / "review/statusline-merge-patch.json").read_text())
            self.assertEqual(patch_data["statusLine"]["padding"], 2)
            self.assertEqual(patch_data["statusLine"]["refreshInterval"], 10)
            self.assertEqual((root / "review/previous-statusline.command").read_text(), "printf original")
            self.assertNotIn("PRIVATE", json.dumps(patch_data))
            self.assertEqual(settings["statusLine"], original)
            command = patch_data["statusLine"]["command"]
            run = subprocess.run(command, shell=True, input=b'{"rate_limits":{"five_hour":{"used_percentage":40}}}', capture_output=True)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(run.stdout, b"original")
            self.assertEqual(json.loads((root / "feed/claude.json").read_text())["windows"][0]["usedPercent"], 40)

    def fake(self, behavior):
        # Tests alone may inject a fake process. Production verifies a signed binary.
        source = '''import sys,json
for line in sys.stdin:
 m=json.loads(line)
 if "id" not in m: continue
 result={}
 if m["method"]=="account/rateLimits/read": result={"rateLimits":{"primary":{"usedPercent":17}}}
 print(json.dumps({"id":m["id"],"result":result}),flush=True)
'''
        process = subprocess.Popen([sys.executable, "-c", behavior or source], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
        return RPC(process)

    def test_rpc_real_pipes_and_method_denial(self):
        rpc = self.fake(None)
        try:
            rpc.initialize()
            self.assertEqual(codex_feed(rpc.call("account/rateLimits/read"))["windows"][0]["usedPercent"], 17)
            for method in ("turn/start", "command/exec", "account/rateLimits/consumeReset", "account/logout"):
                with self.assertRaises(ValueError): rpc.call(method)
            with self.assertRaises(ValueError): rpc.call("account/login/start", {"type": "chatgptAuthTokens", "accessToken": "PRIVATE"})
        finally: rpc.close()
        self.assertIsNotNone(rpc.process.poll())

    def test_timeout_and_server_request_fail_closed(self):
        for script in ('import time; time.sleep(20)', 'import sys; sys.stdout.write(\'{"id":9,"method":"exec"}\\n\'); sys.stdout.flush(); import time; time.sleep(20)'):
            rpc = self.fake(script)
            try:
                with self.assertRaises((TimeoutError, ValueError)):
                    rpc.call("account/rateLimits/read", timeout=.1)
            finally: rpc.close()

    def test_device_login_success_and_no_secret_export(self):
        script = '''import sys,json
for line in sys.stdin:
 m=json.loads(line)
 if m.get("method")=="account/login/start":
  print(json.dumps({"id":m["id"],"result":{"type":"chatgptDeviceCode","loginId":"fake-login","userCode":"TEST-1234","verificationUrl":"https://auth.openai.com/codex/device"}}),flush=True)
  print(json.dumps({"method":"account/login/completed","params":{"loginId":"fake-login","success":True}}),flush=True)
'''
        rpc = self.fake(script)
        display = []
        try:
            rpc.login(display.append)
            self.assertEqual(len(display), 1)
            self.assertIn("TEST-1234", display[0])
        finally: rpc.close()
        # Device codes exist only in the terminal UX; output publication is quota-only.
        self.assertNotIn("TEST-1234", json.dumps(codex_feed({"rateLimits": {}})))

    def test_untrusted_device_destination_and_oversize_fail(self):
        script = '''import sys,json
m=json.loads(sys.stdin.readline())
print(json.dumps({"id":m["id"],"result":{"type":"chatgptDeviceCode","loginId":"fake","userCode":"TEST-1234","verificationUrl":"https://evil.example"}}),flush=True)
import time; time.sleep(20)
'''
        rpc = self.fake(script)
        try:
            with self.assertRaises(ValueError): rpc.login(lambda _: self.fail("Unexpected display"))
        finally: rpc.close()
        rpc = self.fake('import sys,time; sys.stdout.write("x"*140000); sys.stdout.flush(); time.sleep(20)')
        try:
            with self.assertRaises(ValueError): rpc.call("account/rateLimits/read")
        finally: rpc.close()

    def test_launch_uses_private_environment_and_keyring(self):
        with tempfile.TemporaryDirectory() as temp, patch("codex_quota.subprocess.Popen") as popen:
            with patch.dict(os.environ, {"OPENAI_API_KEY": "PRIVATE", "CODEX_HOME": "/existing/private", "HTTPS_PROXY": "PRIVATE"}):
                launch(Path("/verified/codex"), Path(temp).resolve())
            args, kwargs = popen.call_args
            self.assertIn('cli_auth_credentials_store="keyring"', args[0])
            self.assertEqual(args[0][-2:], ["--listen", "stdio://"])
            self.assertNotIn("PRIVATE", json.dumps(kwargs["env"]))
            self.assertNotIn("/existing/private", json.dumps(kwargs["env"]))
            self.assertTrue(kwargs["start_new_session"])

    def test_login_notification_flood_cancels(self):
        script = '''import sys,json
for line in sys.stdin:
 m=json.loads(line)
 if m["method"]=="account/login/start":
  print(json.dumps({"id":m["id"],"result":{"type":"chatgptDeviceCode","loginId":"fake-login","userCode":"TEST-1234","verificationUrl":"https://auth.openai.com/codex/device"}}),flush=True)
  for _ in range(257): print('{"method":"irrelevant","params":{}}',flush=True)
 elif m["method"]=="account/login/cancel":
  print(json.dumps({"id":m["id"],"result":{}}),flush=True)
'''
        rpc = self.fake(script)
        try:
            with self.assertRaises(ValueError): rpc.login(lambda _: None)
        finally: rpc.close()

    def test_existing_unrelated_provider_state_is_refused(self):
        with tempfile.TemporaryDirectory() as temp, patch("codex_quota.subprocess.Popen") as popen:
            root = Path(temp).resolve()
            (root / "unrelated.txt").write_text("not adapter data")
            with self.assertRaises(ValueError): launch(Path("/verified/codex"), root)
            popen.assert_not_called()

    def test_statusline_command_size_boundary_before_patch(self):
        for size in (16384, 16385):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                settings = {"statusLine": {"type": "command", "command": " " * size}}
                if size == 16384:
                    prepare(settings, root / "review", root / "feed")
                    self.assertTrue((root / "review/statusline-merge-patch.json").exists())
                else:
                    with self.assertRaises(ValueError): prepare(settings, root / "review", root / "feed")
                    self.assertFalse((root / "review/statusline-merge-patch.json").exists())


if __name__ == "__main__": unittest.main()
