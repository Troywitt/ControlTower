#!/usr/bin/env python3
"""User-started stdio adapter. Official Codex owns auth; dashboard sees quotas.

No shell, token-file access, generic RPC entry point, model turns, or socket server.
Run in a private terminal; do not record the device code during sign-in.
"""
import argparse
import fcntl
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


class AdapterError(ValueError):
    """Reason strings are constants supplied only by this module."""
    def __init__(self, category):
        self.category = category
        super().__init__(category)


class ProviderOperationError(AdapterError):
    """Only a fixed category survives; never retain the provider error body."""
    def __init__(self, error):
        message = error.get("message", "") if isinstance(error, dict) else ""
        message = message.lower() if isinstance(message, str) else ""
        code = error.get("code") if isinstance(error, dict) else None
        if any(term in message for term in ("keyring", "keychain", "credential store")):
            category = "credential storage unavailable"
        elif any(term in message for term in ("expired", "expiration")):
            category = "provider sign-in expired"
        elif any(term in message for term in ("denied", "declined", "cancelled", "canceled")):
            category = "provider sign-in denied or cancelled"
        elif any(term in message for term in ("persist", "save credentials", "save auth", "saving auth", "store credentials")):
            category = "credential storage unavailable"
        elif any(term in message for term in ("not authenticated", "not logged in", "requires authentication", "authentication required", "requires chatgpt", "missing access token", "unauthorized", "401")):
            category = "saved login unavailable or rejected"
        elif any(term in message for term in ("forbidden", "403")):
            category = "provider access denied"
        elif any(term in message for term in ("429", "too many requests")):
            category = "provider rate limited"
        elif any(term in message for term in ("timed out", "timeout", "connect", "dns")):
            category = "provider connection unavailable"
        elif type(code) is int and code in (-32601, -32602):
            category = "provider protocol incompatible"
        else:
            category = "provider request rejected"
        self.category = category
        super().__init__(category)


def acquire_feed_lock(output):
    fd = os.open(output / ".codex-adapter.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    lock = os.fdopen(fd, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock
    except BaseException:
        lock.close()
        raise


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


def provider_context(binary, state):
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
    codex_home = private_dir(home / "codex")
    cwd = private_dir(state / "empty-workspace")
    # Fixed private HOME/CODEX_HOME for this child only. No inherited token,
    # proxy, provider URL, node injection, or project-config environment values.
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "CODEX_HOME": str(codex_home),
           "TMPDIR": str(private_dir(state / "tmp")), "LANG": "en_US.UTF-8"}
    command = [str(binary), "-c", 'cli_auth_credentials_store="keyring"',
               "-c", "check_for_update_on_startup=false", "-c", "analytics.enabled=false"]
    return command, cwd, env


def launch(binary, state):
    command, cwd, env = provider_context(binary, state)
    return subprocess.Popen(command + ["app-server", "--listen", "stdio://"],
                            cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)


def stop_provider(child):
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            child.terminate()
        except ProcessLookupError:
            pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                child.kill()
            except ProcessLookupError:
                pass
        child.wait(timeout=3)


def official_login(binary, state):
    # Called only after main's private-terminal check and binary verification.
    # Inherit the user's terminal directly: no pipes, capture, parsing or log.
    command, cwd, env = provider_context(binary, state)
    child = subprocess.Popen(command + ["login", "--device-auth"], cwd=cwd, env=env,
                             start_new_session=True)
    try:
        try:
            result = child.wait(timeout=660)
        except subprocess.TimeoutExpired:
            raise AdapterError("official login exceeded overall deadline") from None
        if result != 0:
            raise AdapterError("official CLI login failed; quota reader not started")
    finally:
        stop_provider(child)


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
                raise AdapterError("official provider process exited")
            self.buffer.extend(chunk)
            if len(self.buffer) > MAX_INPUT:
                raise AdapterError("provider response exceeded size limit")
        line, _, rest = self.buffer.partition(b"\n")
        self.buffer = bytearray(rest)
        try:
            result = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise AdapterError("malformed provider message") from None
        if not isinstance(result, dict):
            raise AdapterError("malformed provider message")
        return result

    def notification(self, message):
        # The adapter never executes server-initiated requests, tools or prompts.
        if "method" in message and "id" in message:
            raise AdapterError("unexpected provider request refused")
        if message.get("method") == "account/login/completed":
            params = message.get("params", {})
            if not isinstance(params, dict) or type(params.get("success")) is not bool:
                raise AdapterError("malformed login completion")
            # Keep only correlation and a fixed failure category in memory.
            # Provider error strings can contain auth data and never leave here.
            failure = None if params["success"] else ProviderOperationError({"message": params.get("error")}).category
            self.login_result = (params.get("loginId"), params["success"], failure)

    def call(self, method, params=None, timeout=30):
        if method not in ALLOWED:
            raise ValueError("RPC method refused")
        # No externally managed tokens or API keys are accepted by this adapter.
        if method == "account/login/start" and params != {"type": "chatgptDeviceCode"}:
            raise ValueError("Login type refused")
        self.serial += 1
        expected = self.serial
        # Unit-parameter methods (including account/rateLimits/read) require
        # JSON null in the pinned schema; do not rely on permissive decoding.
        self.send({"id": expected, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        count = 0
        while True:
            count += 1
            if count > 256:
                raise ValueError("Excess provider messages")
            message = self.receive(deadline)
            self.notification(message)
            if message.get("id") == expected:
                if "error" in message:
                    raise ProviderOperationError(message["error"])
                if "result" not in message:
                    raise ValueError("Missing provider result")
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
                    raise AdapterError("login notification limit exceeded")
                self.notification(self.receive(deadline))
            if not self.login_result[1]:
                raise AdapterError("provider reported sign-in failure: " + self.login_result[2])
        except BaseException:
            try:
                self.call("account/login/cancel", {"loginId": login_id}, timeout=2)
            except Exception:
                pass
            raise

    def close(self):
        self.selector.close()
        try:
            self.process.stdin.close()
        except OSError:
            pass
        # Reap an already exited child before signalling. Its old process group
        # can cease to exist or be inaccessible; never mask the original error.
        if self.process.poll() is not None:
            self.process.stdout.close()
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                self.process.terminate()
            except (ProcessLookupError, PermissionError):
                pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=3)
            except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                pass
        self.process.stdout.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--state", required=True, help="Dedicated private adapter state, NOT your existing Codex home")
    parser.add_argument("--output", required=True, help="Dedicated quota-only folder")
    enrollment = parser.add_mutually_exclusive_group()
    enrollment.add_argument("--login", action="store_true", help="Legacy app-server device sign-in")
    enrollment.add_argument("--enroll-official", action="store_true", help="Official CLI owns device sign-in, then quota-only app-server starts")
    args = parser.parse_args()
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Use a private interactive terminal, not a captured tool session")
    rpc = None
    lock = None
    stage = "local preparation"
    try:
        output = private_dir(args.output)
        state = private_dir(args.state)
        if output == state or output in state.parents or state in output.parents:
            raise ValueError("Quota folder and provider state must be separate")
        lock = acquire_feed_lock(output)
        binary = verify_binary(args.binary, args.sha256)
        if args.enroll_official:
            stage = "official CLI device sign-in"
            publish(output, envelope("codex", []))
            print("Official Codex will handle device sign-in in this private Terminal. Keychain-only storage is requested. Keep this window open; Ctrl+C cancels.", flush=True)
            official_login(binary, state)
            print("Official CLI login exited successfully. Checking quota access next.", flush=True)
        stage = "official provider startup"
        rpc = RPC(launch(binary, state))
        rpc.initialize()
        if args.login:
            stage = "official device sign-in"
            print("Official Codex is configured to request macOS Keychain storage for this separate login. No plaintext fallback is requested.")
            print("Provider traffic and auth refresh belong to Codex, outside the dashboard sandbox. Ctrl+C cancels.")
            rpc.login(print)
            print("Provider reported login complete.")
        while True:
            stage = "quota read"
            payload = rpc.call("account/rateLimits/read")
            stage = "quota decoding"
            snapshot = codex_feed(payload)
            del payload
            publish(output, snapshot)
            print("Quota snapshot published. Return refreshes; q quits and stops this provider process." if snapshot["windows"] else
                  "Provider returned no quota windows. Return retries; q quits. No usage is available yet.")
            if input().strip().lower() == "q":
                break
    except (Exception, KeyboardInterrupt) as error:
        # Do not expose raw provider errors, auth URLs, file contents or tracebacks.
        category = error.category if isinstance(error, AdapterError) else "cancelled" if isinstance(error, KeyboardInterrupt) else "timeout" if isinstance(error, TimeoutError) else "local pipe or terminal unavailable" if isinstance(error, OSError) else "unavailable"
        print("Adapter stopped at " + stage + " (" + category + "). No token fallback was attempted.", file=sys.stderr)
        return 1
    finally:
        try:
            if rpc:
                rpc.close()
        finally:
            if lock:
                try:
                    publish(args.output, envelope("codex", []))
                except (ValueError, OSError):
                    pass
                lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
