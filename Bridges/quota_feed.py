"""Quota-only schema. Never serialize the input object or provider error text."""
import json
import math
import os
from pathlib import Path
import stat
import tempfile
import time

MAX_INPUT = 131072


def number(value, maximum=100):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def window(label, pct, reset=None):
    if not number(pct):
        raise ValueError("Invalid quota")
    result = {"id": label, "usedPercent": pct}
    if reset is not None:
        if not number(reset, 32503680000):
            raise ValueError("Invalid reset")
        result["resetsAt"] = reset
    return result


def envelope(provider, windows, now=None):
    return {"version": 1, "provider": provider, "observedAt": time.time() if now is None else now, "windows": windows}


def claude_feed(payload, now=None):
    rate = payload.get("rate_limits") or {}
    rows = []
    for key, label in (("five_hour", "Session"), ("seven_day", "Weekly")):
        value = rate.get(key)
        if value is not None:
            rows.append(window(label, value.get("used_percentage"), value.get("resets_at")))
    return envelope("claude", rows, now)


def codex_feed(payload, now=None):
    # Choose Codex explicitly; never mix Spark/review/other limit buckets.
    mapping = payload.get("rateLimitsByLimitId")
    rate = mapping.get("codex") if isinstance(mapping, dict) else payload.get("rateLimits")
    if not isinstance(rate, dict):
        raise ValueError("Codex limits unavailable")
    if rate.get("limitId") not in (None, "codex"):
        raise ValueError("Wrong limit bucket")
    rows = []
    for key, label in (("primary", "Primary"), ("secondary", "Secondary")):
        value = rate.get(key)
        if value is not None:
            rows.append(window(label, value.get("usedPercent"), value.get("resetsAt")))
    return envelope("codex", rows, now)


def private_dir(path):
    path = Path(path).absolute()
    # No existing symlink components, even in parent directories.
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("Symlink directory refused")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Use an owner-only directory")
    return path


def publish(directory, data):
    directory = private_dir(directory)
    raw = json.dumps(data, allow_nan=False, separators=(",", ":")).encode()
    if len(raw) > 8192 or data["provider"] not in ("claude", "codex"):
        raise ValueError("Invalid feed")
    fd, temp = tempfile.mkstemp(prefix=".quota-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, directory / (data["provider"] + ".json"))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
