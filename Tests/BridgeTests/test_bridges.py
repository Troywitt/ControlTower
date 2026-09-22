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
from codex_quota import RPC, launch, acquire_feed_lock, ProviderOperationError, AdapterError, official_login, main
from claude_diagnostic import record, shape
import time


class BridgeTests(unittest.TestCase):
    def test_direct_enrollment_and_quota_share_private_identity(self):
        with tempfile.TemporaryDirectory() as temp, patch("codex_quota.subprocess.Popen") as popen:
            state = Path(temp).resolve()
            popen.return_value.wait.return_value = 0
            popen.return_value.poll.return_value = 0
            with patch.dict(os.environ, {"OPENAI_API_KEY": "SECRET", "CODEX_HOME": "/outside", "HTTPS_PROXY": "SECRET"}):
                official_login(Path("/verified/codex"), state)
                login_args, login_kwargs = popen.call_args
                launch(Path("/verified/codex"), state)
                quota_args, quota_kwargs = popen.call_args
            self.assertEqual(login_args[0][-2:], ["login", "--device-auth"])
            self.assertEqual(login_args[0][:-2], quota_args[0][:-3])
            self.assertEqual(login_kwargs["env"], quota_kwargs["env"])
            self.assertEqual(login_kwargs["cwd"], quota_kwargs["cwd"])
            self.assertNotIn("SECRET", json.dumps(login_kwargs["env"]))
            self.assertNotIn("/outside", json.dumps(login_kwargs["env"]))
            for stream in ("stdin", "stdout", "stderr"):
                self.assertNotIn(stream, login_kwargs)  # private terminal, no capture
            self.assertTrue(login_kwargs["start_new_session"])

    def test_direct_enrollment_failure_cancel_and_deadline_cleanup(self):
        cases = [(1, AdapterError), (KeyboardInterrupt(), KeyboardInterrupt),
                 (subprocess.TimeoutExpired("synthetic", 660), AdapterError)]
        for outcome, expected in cases:
            with tempfile.TemporaryDirectory() as temp, patch("codex_quota.subprocess.Popen") as popen, patch("codex_quota.os.killpg") as kill:
                child = popen.return_value
                child.wait.side_effect = [outcome, 0]
                child.poll.return_value = 1 if outcome == 1 else None
                with self.assertRaises(expected): official_login(Path("/verified/codex"), Path(temp).resolve())
                if outcome != 1: kill.assert_called_once()

    def test_quota_starts_only_after_successful_official_enrollment(self):
        for failure in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                args = ["test", "--binary", "/verified/codex", "--sha256", "unused", "--state", str(root / "state"),
                        "--output", str(root / "feed"), "--enroll-official"]
                with patch.object(sys, "argv", args), patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True), patch("codex_quota.verify_binary", return_value=Path("/verified/codex")), patch("codex_quota.official_login") as enroll, patch("codex_quota.launch") as start, patch("codex_quota.RPC") as rpc_type, patch("builtins.input", return_value="q"), patch("builtins.print"):
                    if failure: enroll.side_effect = AdapterError("official CLI login failed; quota reader not started")
                    else: start.side_effect = lambda *_: self.assertTrue(enroll.called)
                    rpc_type.return_value.call.return_value = {"rateLimits": {"primary": {"usedPercent": 12}}}
                    self.assertEqual(main(), 1 if failure else 0)
                    if failure:
                        start.assert_not_called();rpc_type.assert_not_called()
                    else:
                        rpc_type.return_value.initialize.assert_called_once()
                        rpc_type.return_value.call.assert_called_once_with("account/rateLimits/read")
                        rpc_type.return_value.login.assert_not_called()
                    self.assertEqual(json.loads((root / "feed/codex.json").read_text())["windows"], [])

    def test_provider_errors_export_only_fixed_categories(self):
        sentinel = "SECRET_SENTINEL_ACCOUNT_AUTH_URL"
        cases = [("Not authenticated", "saved login unavailable or rejected"),
                 ("Keychain failed", "credential storage unavailable"),
                 ("HTTP 403", "provider access denied"),
                 ("HTTP 429", "provider rate limited"),
                 ("DNS failed", "provider connection unavailable"),
                 ("unexpected", "provider request rejected")]
        for message, category in cases:
            error = ProviderOperationError({"message": message + sentinel, "data": sentinel})
            self.assertEqual(str(error), category)
            self.assertNotIn(sentinel, repr(vars(error)) + repr(error))
        self.assertEqual(str(ProviderOperationError({"code": -32602})), "provider protocol incompatible")
        self.assertEqual(str(ProviderOperationError({"code": -32600})), "provider request rejected")
        self.assertEqual(str(ProviderOperationError({"code": -32600, "message": "chatgpt authentication required to read rate limits"})), "saved login unavailable or rejected")
        script = 'import sys,json;m=json.loads(sys.stdin.readline());print(json.dumps({"id":m["id"],"error":{"code":-32000,"message":"Not authenticated ' + sentinel + '"}}),flush=True)'
        rpc = self.fake(script)
        try:
            with self.assertRaisesRegex(ProviderOperationError, "saved login unavailable or rejected"):
                rpc.call("account/rateLimits/read")
        finally:
            rpc.close()

    def test_codex_single_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            first = acquire_feed_lock(root)
            try:
                with self.assertRaises(BlockingIOError): acquire_feed_lock(root)
            finally: first.close()
            acquire_feed_lock(root).close()

    def test_diagnostic_exports_only_fixed_shapes(self):
        secret = "SECRET_SENTINEL_PROMPT_PATH_TOKEN"
        payload = {secret: secret, "rate_limits": {"five_hour": {
            "used_percentage": secret, "resets_at": secret}, "seven_day": secret}}
        report = shape(payload)
        self.assertNotIn(secret, json.dumps(report))
        self.assertEqual(report["five_hour.used_percentage"], {"type": "string", "valid": False})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            record(root, payload)
            target = root / "claude-diagnostic.json"
            self.assertFalse(target.exists())
            marker = root / "claude-diagnostic.enable"
            marker.write_text(str(time.time() + 120))
            marker.chmod(0o600)
            record(root, payload)
            self.assertNotIn(secret, target.read_text())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            before = target.read_bytes()
            marker.write_text(str(time.time() - 1))
            record(root, {})
            self.assertEqual(target.read_bytes(), before)

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

    def test_quota_request_uses_null_params_with_stable_capabilities(self):
        # Exact contract from pinned 0.153.4 ClientRequest.json: quota params
        # are null, not {}. Do not relax this fake to accept the old request.
        script = '''import sys,json
initialized=False
for line in sys.stdin:
 m=json.loads(line)
 if "id" not in m: continue
 if m["method"]=="initialize":
  initialized=m["params"]["capabilities"]=={"experimentalApi":False}
  print(json.dumps({"id":m["id"],"result":{}}),flush=True)
 elif m["method"]=="account/rateLimits/read":
  if not initialized or m.get("params","MISSING") is not None:
   print(json.dumps({"id":m["id"],"error":{"code":-32600,"message":"Invalid request"}}),flush=True)
  else:
   print(json.dumps({"id":m["id"],"result":{"rateLimits":{"primary":{"usedPercent":17}}}}),flush=True)
'''
        rpc = self.fake(script)
        try:
            rpc.initialize()
            with self.assertRaises(ProviderOperationError):
                rpc.call("account/rateLimits/read", {})
            result = codex_feed(rpc.call("account/rateLimits/read"))
            self.assertEqual(result["windows"][0]["usedPercent"], 17)
        finally:
            rpc.close()

    def test_cleanup_reaps_exited_child_without_signalling(self):
        rpc = self.fake('raise SystemExit(1)')
        rpc.process.wait(timeout=3)
        with patch("codex_quota.os.killpg") as kill:
            rpc.close()
            kill.assert_not_called()

    def test_cleanup_group_denial_falls_back_to_owned_child(self):
        rpc = self.fake('import time; time.sleep(20)')
        with patch("codex_quota.os.killpg", side_effect=PermissionError):
            rpc.close()
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

    def test_device_login_handles_coalesced_fragmented_and_delayed_notifications(self):
        for mode in ("coalesced", "completion_first", "fragmented", "delayed"):
            script = '''import sys,json,time
m=json.loads(sys.stdin.readline())
reply=json.dumps({"id":m["id"],"result":{"type":"chatgptDeviceCode","loginId":"test-login","userCode":"TEST-1234","verificationUrl":"https://auth.openai.com/codex/device"}})+"\\n"
other=json.dumps({"method":"account/updated","params":{"PRIVATE":"SECRET_SENTINEL"}})+"\\n"
done=json.dumps({"method":"account/login/completed","params":{"loginId":"test-login","success":True}})+"\\n"
mode=MODE
if mode=="coalesced":
 sys.stdout.write(reply+other+done);sys.stdout.flush()
elif mode=="completion_first":
 sys.stdout.write(done+reply);sys.stdout.flush()
elif mode=="fragmented":
 for part in (reply[:9],reply[9:]+other+done[:23],done[23:]):
  sys.stdout.write(part);sys.stdout.flush();time.sleep(.03)
else:
 sys.stdout.write(reply);sys.stdout.flush();time.sleep(.2)
 sys.stdout.write(other+done);sys.stdout.flush()
time.sleep(10)
'''.replace("MODE", repr(mode))
            rpc = self.fake(script)
            try:
                rpc.login(lambda _: None)
                self.assertTrue(rpc.login_result[1])
            finally:
                rpc.close()

    def test_failed_login_preserves_only_safe_reason_and_cancels(self):
        sentinel = "SECRET_SENTINEL_CALLBACK_TOKEN"
        for provider_error, expected in (("Keychain failed " + sentinel, "credential storage unavailable"),
                                         ("device code expired " + sentinel, "provider sign-in expired"),
                                         (sentinel, "provider request rejected")):
            script = '''import sys,json
for line in sys.stdin:
 m=json.loads(line)
 if m["method"]=="account/login/start":
  reply={"id":m["id"],"result":{"type":"chatgptDeviceCode","loginId":"test-login","userCode":"TEST-1234","verificationUrl":"https://auth.openai.com/codex/device"}}
  done={"method":"account/login/completed","params":{"loginId":"test-login","success":False,"error":ERROR}}
  sys.stdout.write(json.dumps(reply)+"\\n"+json.dumps(done)+"\\n");sys.stdout.flush()
 elif m["method"]=="account/login/cancel":
  print(json.dumps({"id":m["id"],"result":{}}),flush=True)
'''.replace("ERROR", repr(provider_error))
            rpc = self.fake(script)
            try:
                with self.assertRaises(AdapterError) as caught:
                    rpc.login(lambda _: None)
                self.assertEqual(str(caught.exception), "provider reported sign-in failure: " + expected)
                self.assertNotIn(sentinel, str(caught.exception) + repr(rpc.login_result))
                self.assertEqual(rpc.serial, 2)  # cancellation was sent
            finally:
                rpc.close()

    def test_login_eof_malformed_and_idle_timeout_are_distinct(self):
        for source, expected in (("raise SystemExit(0)", "official provider process exited"),
                                 ("print('not-json',flush=True)", "malformed provider message")):
            rpc = self.fake(source)
            try:
                with self.assertRaisesRegex(AdapterError, expected):
                    rpc.receive(time.monotonic() + 1)
            finally:
                rpc.close()
        rpc = self.fake('import time;time.sleep(10)')
        try:
            with self.assertRaises(TimeoutError): rpc.receive(time.monotonic() + .1)
        finally:
            rpc.close()
        with self.assertRaisesRegex(AdapterError, "malformed login completion"):
            RPC.notification(object(), {"method": "account/login/completed", "params": {"success": "true"}})

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
            self.assertTrue(Path(kwargs["env"]["CODEX_HOME"]).is_dir())

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
