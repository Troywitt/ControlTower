#!/usr/bin/env python3
"""Generate a reviewable statusLine merge patch. Never edits Claude settings.

Run this yourself with your chosen non-secret settings file. Only statusLine is
copied into the private review folder; other settings are neither emitted nor logged.
"""
import argparse
import json
from pathlib import Path
import shlex
import sys
from quota_feed import private_dir, publish, envelope


def prepare(settings, review_dir, output, python=sys.executable):
    review_dir = private_dir(review_dir)
    output = private_dir(output)
    if review_dir == output or review_dir in output.parents or output in review_dir.parents:
        raise ValueError("Keep review and quota folders separate")
    existing = settings.get("statusLine")
    if existing is not None and (not isinstance(existing, dict) or existing.get("type") != "command"
                                  or not isinstance(existing.get("command"), str)):
        raise ValueError("Unsupported existing statusLine; preserve it manually")
    if existing and len(existing["command"].encode()) > 16384:
        raise ValueError("Existing command exceeds wrapper limit; preserve it manually")
    patch = dict(existing or {"type": "command"})
    command = [python, str(Path(__file__).with_name("claude_statusline.py").resolve()), "--output", str(output)]
    if existing:
        # Write once. Never wrap our own previous wrapper or overwrite a review.
        if "claude_statusline.py" in existing["command"]:
            raise ValueError("Bridge already configured; refusing a wrapper cycle")
        previous = review_dir / "previous-statusline.command"
        with previous.open("x") as file:
            file.write(existing["command"])
        previous.chmod(0o600)
        command += ["--previous-file", str(previous)]
    patch["command"] = shlex.join(command)
    for name, value in (("statusline-merge-patch.json", {"statusLine": patch}),
                        ("statusline-rollback.json", {"statusLine": existing})):
        path = review_dir / name
        with path.open("x") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
        path.chmod(0o600)
    publish(output, envelope("claude", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        data = Path(args.settings).read_bytes()
        if len(data) > 1024 * 1024:
            raise ValueError("Settings too large")
        settings = json.loads(data)
        if not isinstance(settings, dict):
            raise ValueError("Invalid settings")
        prepare(settings, args.review_dir, args.output)
        print("Prepared statusline-merge-patch.json and statusline-rollback.json. No Claude settings changed.")
    except (ValueError, TypeError, OSError):
        print("Preparation stopped. Use fresh private folders and a valid command-based statusLine; no settings changed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
