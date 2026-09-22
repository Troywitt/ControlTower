"""Opt-in, short-lived field-shape diagnostics. Never export input values."""
import json
import os
import stat
import tempfile
import time
from quota_feed import number, private_dir


def shape(payload):
    result = {}
    missing = object()
    def visit(value, name, maximum=None):
        kind = {dict: "object", list: "array", str: "string", bool: "boolean",
                int: "number", float: "number", type(None): "null"}.get(type(value), "missing")
        result[name] = {"type": kind}
        if maximum is not None:
            result[name]["valid"] = number(value, maximum)
    visit(payload, "input")
    rate = payload.get("rate_limits", missing) if isinstance(payload, dict) else missing
    visit(rate, "rate_limits")
    for key in ("five_hour", "seven_day"):
        value = rate.get(key, missing) if isinstance(rate, dict) else missing
        visit(value, key)
        for field, maximum in (("used_percentage", 100), ("resets_at", 32503680000)):
            item = value.get(field, missing) if isinstance(value, dict) else missing
            visit(item, key + "." + field, maximum)
    return result


def record(directory, payload):
    # Marker is a local diagnostic opt-in, never a provider input field.
    # Expiry is bounded to fifteen minutes; absent marker means no output.
    try:
        directory = private_dir(directory)
        fd = os.open(directory / "claude-diagnostic.enable", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 32:
                return
            expiry = float(stream.read(33))
        now = time.time()
        if not now < expiry <= now + 900:
            return
        data = {"version": 1, "observedAt": now, "fields": shape(payload)}
        fd, temp = tempfile.mkstemp(prefix=".diagnostic-", dir=directory)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, allow_nan=False)
            os.replace(temp, directory / "claude-diagnostic.json")
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    except (OSError, ValueError, TypeError):
        pass
