#!/usr/bin/env python3
"""Official Grok /usage screen adapter; no token access or generated input."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import subprocess
import time
from gemini_quota import ROOT, main as terminal_main, stop, tree_hash
from quota_feed import envelope, private_dir, window

BINARY = ROOT / ".build/grok-runtime/grok-1.0.40-macos-aarch64"
SHA256 = "3f2aef9618191a2c60d18a5044fa462c9c77bdc4187b02ed716b0394e8d4fef2"
REQUIREMENT = 'anchor apple generic and identifier "xai-grok-pager" and certificate leaf[subject.OU] = "5Y6N3AJ54S"'


def verify_runtime():
    if hashlib.sha256(BINARY.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Grok binary changed")
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", "-R", "=" + REQUIREMENT, str(BINARY)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    pins = json.loads((ROOT / "Bridges/gemini-runtime-pin.json").read_text())
    if tree_hash(ROOT / ".build/gemini-python") != pins["pythonTree"]:
        raise ValueError("Terminal parser changed")
    return BINARY


def reset_epoch(text, now):
    # Official display omits year/zone. Resolve only an unambiguous upcoming
    # weekly reset in the same system-local timezone used by the official CLI.
    match = re.fullmatch(r"([A-Z][a-z]{2,8}) (\d{1,2}), (\d{2}):(\d{2})", text)
    if not match:
        raise ValueError("Unrecognized reset display")
    current = datetime.datetime.fromtimestamp(now)
    choices = []
    for year in (current.year - 1, current.year, current.year + 1):
        for fmt in ("%Y %b %d, %H:%M", "%Y %B %d, %H:%M"):
            try:
                wall = datetime.datetime.strptime(str(year) + " " + text, fmt)
                for fold in (0, 1):
                    value = wall.replace(fold=fold).timestamp()
                    if now - 60 <= value <= now + 8 * 86400:
                        choices.append(value)
            except ValueError:
                pass
    choices = set(choices)
    if not choices:
        raise ValueError("Ambiguous reset date")
    if len(choices) > 1:
        return None  # DST fold/gap has no defensible exact instant
    return choices.pop()


def parse_screen(lines, now):
    if len(lines) > 80 or any(len(line) > 180 for line in lines):
        raise ValueError("Screen bounds")
    headers = []
    for i, line in enumerate(lines):
        for match in re.finditer(r"│([^│]*)│", line):
            if match[1].strip() == "Weekly limit (SuperGrok)":
                headers.append((i, match.start() + 1, match.end() - 1))
    if len(headers) != 1:
        return None
    index, left, right = headers[0]
    modal = [line[left:right].strip() for line in lines]
    if not any(all(label in line for label in ("Context usage", "Usage limit", "Session info")) for line in modal[:index]):
        return None
    if not any("Esc close" in line for line in modal[index:]):
        return None
    if any("Couldn't load usage" in line or "Loading usage" in line for line in modal):
        return None
    after = [line for line in modal[index + 1:] if line]
    if not after:
        return None
    percent = re.fullmatch(r"[█░]{30}\s+(\d{1,3})%", after[0])
    if not percent:
        raise ValueError("Unrecognized allowance bar")
    reset = None
    resets = [line for line in after[1:] if line.startswith("Resets:")]
    if len(resets) > 1:
        raise ValueError("Conflicting resets")
    if resets:
        reset = reset_epoch(resets[0].removeprefix("Resets:").strip(), now)
    return envelope("grok", [window("Weekly", int(percent[1]), reset)], now)


def inspect_configuration(binary, cwd, env, state):
    child = subprocess.Popen([str(binary), "inspect", "--json"], cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    raw = bytearray()
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline:
            if select.select([child.stdout], [], [], .2)[0]:
                chunk = os.read(child.stdout.fileno(), 16384)
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > 262144:
                    raise ValueError("Inspection exceeds bound")
        child.wait(timeout=max(.1, deadline - time.monotonic()))
        if child.returncode:
            raise ValueError("Inspection failed")
        data = json.loads(raw)
        validate_inspection(data, state)
    finally:
        stop(child)
        child.stdout.close()


def validate_inspection(data, state):
    for key in ("hooks", "plugins", "mcpServers", "lspServers", "projectInstructions"):
        if data.get(key) != []:
            raise ValueError("Unexpected external configuration")
    for key in ("skills", "agents"):
        items = data.get(key)
        if not isinstance(items, list) or any(item.get("source") != {"type": "builtin"} for item in items):
            raise ValueError("Unexpected external extension")
    layers = data.get("configSources", {}).get("layers")
    if not isinstance(layers, list):
        raise ValueError("Inspection contract changed")
    for layer in layers:
        if layer.get("note") == "empty":
            continue
        path = Path(layer.get("path", "")).absolute()
        if layer.get("note") or state not in path.parents:
            raise ValueError("Existing configuration requires review")


def prepare_state(state):
    # Preserve machine policy, and stop instead of loading or bypassing it.
    if Path("/etc/grok").exists() or Path("/Library/Application Support/ClaudeCode/managed-settings.json").exists():
        raise ValueError("Machine policy requires review")
    state = private_dir(state)
    marker = state / "controltower-grok-v1"
    if not marker.exists():
        if any(state.iterdir()):
            raise ValueError("Use a new empty adapter directory")
        marker.write_text("ControlTower Grok v1\n");marker.chmod(0o600)
        home = private_dir(state / "home")
        grok_home = private_dir(home / ".grok")
        config = grok_home / "config.toml"
        config.write_text('[cli]\nauto_update = false\nuse_leader = false\n[features]\ntelemetry = false\nfeedback = false\ncodebase_indexing = false\nsupport_permission = true\n[telemetry]\nmixpanel_enabled = false\ntrace_upload = false\n[diagnostics]\nerror_reporting = false\n[session]\nload_envrc = false\n')
        config.chmod(0o600)
    if marker.is_symlink() or marker.read_text() != "ControlTower Grok v1\n":
        raise ValueError("Unrecognized state")
    home = private_dir(state / "home")
    grok_home = private_dir(home / ".grok")
    cwd = private_dir(state / "empty-workspace")
    # A real empty repository bounds discovery even when the provider resolves
    # repository roots through git rather than looking for a marker directory.
    if not (cwd / ".git/HEAD").exists():
        subprocess.run(["/usr/bin/git", "init", "--quiet", "--template=", str(cwd)],
                       env={"HOME": str(home), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"},
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    env = {"HOME": str(home), "GROK_HOME": str(grok_home), "PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8",
           "TERM": "xterm-256color", "TMPDIR": str(private_dir(state / "tmp")),
           "GROK_DISABLE_AUTOUPDATER": "1", "GROK_TELEMETRY_ENABLED": "false", "DISABLE_TELEMETRY": "1",
           "GROK_TELEMETRY_TRACE_UPLOAD": "0", "GROK_TELEMETRY_MIXPANEL_ENABLED": "false",
           "DISABLE_ERROR_REPORTING": "1", "GROK_ERROR_REPORTING": "false", "GROK_CRASH_HANDLER": "0",
           "GROK_MEMORY": "0", "GROK_SUBAGENTS": "0", "GROK_PROMPT_SUGGESTIONS": "0", "GROK_FEEDBACK_ENABLED": "0"}
    for vendor in ("CLAUDE", "CURSOR", "CODEX"):
        for part in ("SKILLS", "RULES", "AGENTS", "MCPS", "HOOKS", "SESSIONS"):
            env["GROK_" + vendor + "_" + part + "_ENABLED"] = "false"
    inspect_configuration(BINARY, cwd, env, state)
    return cwd, env


if __name__ == "__main__":
    raise SystemExit(terminal_main(provider="grok", verify=verify_runtime, prepare=prepare_state,
        parse=parse_screen, dialog_label="Usage limit", command=lambda binary: [str(binary), "--no-leader", "--fullscreen", "--no-subagents", "--disable-web-search"],
        notice="Official Grok owns sign-in in a separate private home. Complete subscription sign-in and trust prompts yourself. At the normal prompt enter /usage and leave Usage limit visible. Esc closes it; /usage refreshes. Do not send a model message or choose billing changes. Only weekly percentage and an estimated local reset leave this Terminal."))
