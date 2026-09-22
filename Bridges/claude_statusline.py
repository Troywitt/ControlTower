#!/usr/bin/env python3
"""Receives Claude's official statusLine stdin; writes only allowlisted quotas.

Does not read Claude config, transcripts or credentials. With --previous-file,
passes stdin IN MEMORY to the user's unchanged previous statusLine command.
That command already received this input; it is user-supplied trusted code.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from quota_feed import MAX_INPUT, claude_feed, publish
from claude_diagnostic import record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-file")
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        return 1
    try:
        payload = json.loads(raw)
        record(args.output, payload)
        publish(args.output, claude_feed(payload))
    except (ValueError, TypeError, AttributeError, OSError):
        # Replace prior quota with unavailable; do not leave a fresh-looking success.
        try:
            publish(args.output, claude_feed({}))
        except (ValueError, OSError):
            pass
    if args.previous_file:
        try:
            command = Path(args.previous_file).read_text()
            if len(command.encode()) > 16384:
                return 1
            # Never captures or logs previous output; preserves the original display.
            child = subprocess.Popen(command, shell=True, executable="/bin/sh", stdin=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                child.communicate(raw, timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
                return 1
        except (OSError, subprocess.TimeoutExpired):
            return 1
    else:
        sys.stdout.write("ControlTower quota bridge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
