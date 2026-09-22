#!/usr/bin/env python3
"""User-started stdio adapter. Official Codex owns auth; dashboard sees quotas.

No shell, token-file access, generic RPC entry point, model turns, or socket server.
Run in a private terminal; do not record the device code during sign-in.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
from quota_feed import MAX_INPUT, codex_feed, envelope, private_dir, publish

ALLOWED = {"initialize", "account/login/start", "account/login/cancel", "account/rateLimits/read"}
REQUIREMENT = 'anchor apple generic and identifier "codex" and certificate leaf[subject.OU] = "2DC432GLL2"'


def verify_binary(path, expected_sha):
    binary = Path(path).resolve(strict=True)
    if not binary.is_file() or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise ValueError("Invalid binary pin")
    digest = hashlib.sha256()
    with binary.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        raise ValueError("Binary changed; review update before reconnecting")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", "-R", "=" + REQUIREMENT, str(binary)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    return binary


def launch(binary, state):
    state = private_dir(state)
    marker = state / "controltower-adapter-v1"
    if not marker.exists():
        if any(state.iterdir()):
            raise ValueError("Use a new empty provider-state directory")
        with marker.open("x") as file:
            file.write("ControlTower private Codex state v1\n")
        marker.chmod(0o600)
    if marker.is_symlink() or marker.read_text() != "ControlTower private Codex state v1\n":
        raise ValueError("Unrecognized adapter state")
    home = private_dir(state / "provider-home")
    cwd = private_dir(state / "empty-workspace")
    # Fixed private HOME/CODEX_HOME for this child only. No inherited token,
    # proxy, provider URL, node injection, or project-config environment values.
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "CODEX_HOME": str(home / "codex"),
           "TMPDIR": str(private_dir(state / "tmp")), "LANG": "en_US.UTF-8"}
    return subprocess.Popen([str(binary), "-c", 'cli_auth_credentials_store="keyring"',
                             "-c", "check_for_update_on_startup=false", "-c", "analytics.enabled=false",
                             "app-server", "--listen", "stdio://"],
                            cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)


class RPC:
    def __init__(self, process):
        self.process = process
        self.serial = 0
        self.buffer = bytearray()
        self.login_result = None
        self.selector = selectors.DefaultSelector()
        self.selector.register(process.stdout, selectors.EVENT_READ)

    def send(self, message):
        raw = json.dumps(message, separators=(",", ":")).encode() + b"\n"
        self.process.stdin.write(raw)
        self.process.stdin.flush()

    def receive(self, deadline):
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError("Provider timeout")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                raise ValueError("Provider stopped")
            self.buffer.extend(chunk)
            if len(self.buffer) > MAX_INPUT:
                raise ValueError("Provider response too large")
        line, _, rest = self.buffer.partition(b"\n")
        self.buffer = bytearray(rest)
        result = json.loads(line)
        if not isinstance(result, dict):
            raise ValueError("Invalid protocol")
        return result

    def notification(self, message):
        # The adapter never executes server-initiated requests, tools or prompts.
        if "method" in message and "id" in message:
            raise ValueError("Unexpected server request")
        if message.get("method") == "account/login/completed":
            params = message.get("params", {})
            self.login_result = (params.get("loginId"), params.get("success") is True)

    def call(self, method, params=None, timeout=30):
        if method not in ALLOWED:
            raise ValueError("RPC method refused")
        # No externally managed tokens or API keys are accepted by this adapter.
        if method == "account/login/start" and params != {"type": "chatgptDeviceCode"}:
            raise ValueError("Login type refused")
        self.serial += 1
        expected = self.serial
        self.send({"id": expected, "method": method, "params": params or {}})
        deadline = time.monotonic() + timeout
        count = 0
        while True:
            count += 1
            if count > 256:
                raise ValueError("Excess provider messages")
            message = self.receive(deadline)
            self.notification(message)
            if message.get("id") == expected:
                if "error" in message or "result" not in message:
                    raise ValueError("Provider operation failed")
                return message["result"]

    def initialize(self):
        self.call("initialize", {"clientInfo": {"name": "controltower_quota", "version": "0.2.0"},
                                 "capabilities": {"experimentalApi": False}})
        self.send({"method": "initialized", "params": {}})

    def login(self, display):
        self.login_result = None
        result = self.call("account/login/start", {"type": "chatgptDeviceCode"})
        code = result.get("userCode", "")
        login_id = result.get("loginId")
        if (result.get("type") != "chatgptDeviceCode" or not isinstance(login_id, str)
                or not re.fullmatch(r"[A-Z0-9-]{4,32}", code)
                or result.get("verificationUrl") != "https://auth.openai.com/codex/device"):
            raise ValueError("Unsupported device login response")
        display("Open https://auth.openai.com/codex/device in your browser. Enter this private code: " + code)
        # Do not log result/authUrl, account details, raw errors, or callbacks.
        deadline = time.monotonic() + 600
        try:
            count = 0
            while self.login_result is None or self.login_result[0] != login_id:
                count += 1
                if count > 256:
                    raise ValueError("Excess login notifications")
                self.notification(self.receive(deadline))
            if not self.login_result[1]:
                raise ValueError("Login did not complete")
        except BaseException:
            try:
                self.call("account/login/cancel", {"loginId": login_id}, timeout=2)
            except Exception:
                pass
            raise

    def close(self):
        self.selector.close()
        self.process.stdin.close()
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=3)
        self.process.stdout.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--state", required=True, help="Dedicated private adapter state, NOT your existing Codex home")
    parser.add_argument("--output", required=True, help="Dedicated quota-only folder")
    parser.add_argument("--login", action="store_true", help="Start official user-owned device sign-in")
    args = parser.parse_args()
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Use a private interactive terminal, not a captured tool session")
    rpc = None
    try:
        output = private_dir(args.output)
        state = private_dir(args.state)
        if output == state or output in state.parents or state in output.parents:
            raise ValueError("Quota folder and provider state must be separate")
        binary = verify_binary(args.binary, args.sha256)
        rpc = RPC(launch(binary, state))
        rpc.initialize()
        if args.login:
            print("Official Codex will store this separate login in macOS Keychain. No plaintext fallback is requested.")
            print("Provider traffic and auth refresh belong to Codex, outside the dashboard sandbox. Ctrl+C cancels.")
            rpc.login(print)
            print("Provider reported login complete.")
        while True:
            publish(output, codex_feed(rpc.call("account/rateLimits/read")))
            print("Quota snapshot published. Return refreshes; q quits and stops this provider process.")
            if input().strip().lower() == "q":
                break
    except (Exception, KeyboardInterrupt):
        # Do not expose raw provider errors, auth URLs, file contents or tracebacks.
        print("Adapter stopped or provider operation unavailable. No token fallback was attempted.", file=sys.stderr)
        return 1
    finally:
        if rpc:
            rpc.close()
        try:
            publish(args.output, envelope("codex", []))
        except (ValueError, OSError):
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
