#!/usr/bin/env python3
"""Private-terminal adapter for the unmodified, pinned official Gemini CLI.

User performs sign-in and enters /model. No generated input or model prompts.
Terminal screen exists only in bounded memory; only fixed quota rows are saved.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import tty
from quota_feed import envelope, private_dir, publish, window

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("Pro", "Flash", "Flash Lite")
ROW = re.compile(r"^(Pro|Flash Lite|Flash)\s+[▬ ]*\s(\d{1,3})%\s*(?:Resets:\s*(\d{1,2}):(\d{2})\s*([AP]M)\s*\((?:(\d{1,3})h)?\s*(?:(\d{1,2})m)?\))?$")


def parse_screen(lines, now):
    # Bounded screen only, no scrollback, unknown rows fail closed.
    if len(lines) > 80 or any(len(line) > 180 for line in lines):
        raise ValueError("Screen bounds")
    clean = [line.strip().strip("│ ").strip() for line in lines]
    if "Select Model" not in clean or "(Press Esc to close)" not in clean or "Model usage" not in clean:
        return None
    start = clean.index("Model usage") + 1
    end = clean.index("(Press Esc to close)", start)
    rows = []
    seen = set()
    for line in clean[start:end]:
        if not line:
            continue
        match = ROW.fullmatch(line)
        if not match or match[1] in seen:
            raise ValueError("Unrecognized quota row")
        label, pct = match[1], int(match[2])
        seen.add(label)
        reset = None
        if match[3]:
            hours, minutes = int(match[6] or 0), int(match[7] or 0)
            if not 1 <= int(match[3]) <= 12 or int(match[4]) > 59 or minutes > 59 or not 0 < hours * 60 + minutes <= 10080:
                raise ValueError("Invalid reset duration")
            # CLI rounds remaining duration up to minutes. This is an estimate.
            reset = now + 60 * (hours * 60 + minutes)
        rows.append(window(label, pct, reset))
    if not rows:
        return None
    return envelope("gemini", rows, now)


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            # npm bin symlinks are inert; their target is separately hashed.
            data = os.readlink(path).encode()
        elif path.is_file():
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            data = path.read_bytes()
        else:
            continue
        digest.update(str(path.relative_to(root)).encode() + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def verify_runtime():
    pins = json.loads((ROOT / "Bridges/gemini-runtime-pin.json").read_text())
    for key, relative in (("npmTree", ".build/gemini-runtime/node_modules"), ("pythonTree", ".build/gemini-python")):
        if tree_hash(ROOT / relative) != pins[key]:
            raise ValueError("Runtime changed")
    node = Path(pins["node"])
    if hashlib.sha256(node.read_bytes()).hexdigest() != pins["nodeSha256"]:
        raise ValueError("Node changed")
    return node


def prepare_state(state):
    # Do not silently bypass a real machine policy. Only path metadata is read.
    system = Path("/Library/Application Support/GeminiCli")
    if any((system / name).exists() for name in ("settings.json", "system-defaults.json")):
        raise ValueError("Existing system Gemini policy requires review")
    state = private_dir(state)
    marker = state / "controltower-gemini-v1"
    if not marker.exists():
        if any(state.iterdir()):
            raise ValueError("Use a new empty adapter directory")
        marker.write_text("ControlTower Gemini v1\n")
        marker.chmod(0o600)
        home = private_dir(state / "home")
        config = private_dir(home / ".gemini")
        settings = {"telemetry": {"enabled": False}, "privacy": {"usageStatisticsEnabled": False},
                    "general": {"enableAutoUpdate": False, "enableAutoUpdateNotification": False},
                    "context": {"fileName": [], "discoveryMaxDirs": 0, "memoryBoundaryMarkers": [], "includeDirectoryTree": False},
                    "security": {"folderTrust": {"enabled": True}}}
        with (config / "settings.json").open("x") as stream:
            json.dump(settings, stream)
        (config / "settings.json").chmod(0o600)
    if marker.is_symlink() or marker.read_text() != "ControlTower Gemini v1\n":
        raise ValueError("Unrecognized state")
    home = private_dir(state / "home")
    cwd = private_dir(state / "empty-workspace")
    policy = private_dir(state / "adapter-policy")
    for name in ("settings.json", "system-defaults.json"):
        target = policy / name
        if not target.exists():
            with target.open("x") as stream:
                stream.write("{}\n")
            target.chmod(0o600)
        if target.is_symlink() or target.read_text().strip() != "{}":
            raise ValueError("Unexpected private policy")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home), "GEMINI_CLI_NO_RELAUNCH": "1",
           "GEMINI_TELEMETRY_ENABLED": "false",
           "GEMINI_CLI_SYSTEM_SETTINGS_PATH": str(policy / "settings.json"),
           "GEMINI_CLI_SYSTEM_DEFAULTS_PATH": str(policy / "system-defaults.json"),
           "LANG": "en_US.UTF-8", "TERM": "xterm-256color", "NO_COLOR": "1",
           "TMPDIR": str(private_dir(state / "tmp"))}
    return cwd, env


def stop(child):
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        try:
            child.terminate()
        except (ProcessLookupError, PermissionError):
            pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            child.kill()
        child.wait(timeout=3)


def acquire_feed_lock(output, provider="gemini"):
    if provider not in ("gemini", "grok"):
        raise ValueError("Unsupported terminal provider")
    fd = os.open(output / ("." + provider + "-adapter.lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    lock = os.fdopen(fd, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock
    except BaseException:
        lock.close()
        raise


def main(*, provider="gemini", verify=verify_runtime, prepare=prepare_state,
         parse=parse_screen, dialog_label="Select Model", command=None, notice=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Run in your own private Terminal, never an agent-captured session")
    child = None
    original = None
    master = None
    lock = None
    owns_output = False
    failed = False
    stage = "runtime verification"
    failure_kind = "unavailable"
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        os.umask(0o077)  # adapter and child only; no system-wide permission change
        binary = verify()
        sys.path.insert(0, str(ROOT / ".build/gemini-python"))
        import pyte
        output, state = private_dir(args.output), private_dir(args.state)
        stage = "private state preparation"
        if output == state or output in state.parents or state in output.parents:
            raise ValueError("Separate quota folder required")
        cwd, env = prepare(state)
        lock = acquire_feed_lock(output, provider)
        owns_output = True
        publish(output, envelope(provider, []))
        print(notice or "Official Gemini owns sign-in in a separate private home. Complete Google sign-in and trust prompts yourself. At the normal prompt enter /model; leave that dialog visible. Esc closes it; /model refreshes. Do not send a model message. Only rounded tier quotas and estimated resets leave Terminal.")
        print("Ctrl+] quits this adapter. Keep sign-in output private.", flush=True)
        stage = "private terminal creation"
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 60, 140, 0, 0))
        stage = "official interactive client startup"
        argv = command(binary) if command else [str(binary), str(ROOT / ".build/gemini-runtime/node_modules/@google/gemini-cli/bundle/gemini.js")]
        child = subprocess.Popen(argv,
                                 stdin=slave, stdout=slave, stderr=slave, cwd=cwd, env=env, start_new_session=True)
        os.close(slave)
        screen = pyte.Screen(140, 60)
        stream = pyte.ByteStream(screen)
        stage = "private terminal input setup"
        original = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
        last_output = time.monotonic()
        captured = False
        dirty = False
        bytes_since_pause = 0
        stage = "quota screen observation"
        while child.poll() is None:
            ready, _, _ = select.select([master, sys.stdin], [], [], .2)
            if sys.stdin in ready:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data or b"\x1d" in data:
                    break
                os.write(master, data)
            if master in ready:
                try:
                    data = os.read(master, 16384)
                except OSError:
                    break
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)  # user-owned terminal only, never logged
                bytes_since_pause += len(data)
                if bytes_since_pause > 2_000_000:
                    raise ValueError("Terminal flood")
                stream.feed(data)
                # OSC window title/icon can contain arbitrary provider data; discard.
                screen.title = screen.icon_name = ""
                last_output = time.monotonic()
                dirty = True
            if dirty and time.monotonic() - last_output >= .8:
                dirty = False
                bytes_since_pause = 0
                lines = screen.display
                dialog = any(dialog_label in line for line in lines)
                if not dialog:
                    captured = False
                elif not captured:
                    try:
                        result = parse(lines, time.time())
                    except ValueError:
                        result = None
                    publish(output, result or envelope(provider, []))
                    # A loading dialog may arrive before its quota response.
                    # Capture once after valid rows, not once after its shell.
                    captured = result is not None
    except (Exception, KeyboardInterrupt) as error:
        # Never print provider errors, screen contents, login URLs or input.
        failed = True
        failure_kind = type(error).__name__
        if isinstance(error, OSError) and isinstance(error.errno, int):
            failure_kind += " errno " + str(error.errno)
    finally:
        cleanup_failed = False
        try:
            if original is not None:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original)
        except (OSError, termios.error):
            cleanup_failed = failed = True
        try:
            if child is not None:
                stop(child)
        except (OSError, subprocess.TimeoutExpired):
            cleanup_failed = failed = True
        finally:
            if master is not None:
                os.close(master)
            if owns_output:
                try:
                    publish(args.output, envelope(provider, []))
                except (OSError, ValueError):
                    cleanup_failed = failed = True
            if lock:
                lock.close()
        if failed:
            print("\nAdapter unavailable or cancelled at " + stage + " (" + failure_kind + "). Provider details suppressed.")
        print("\nCleanup incomplete; check the private Terminal." if cleanup_failed else "\nTerminal adapter stopped. No raw terminal data was saved.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
