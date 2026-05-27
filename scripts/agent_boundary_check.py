#!/usr/bin/env python3

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: agent_boundary_check.py <task.json>", file=sys.stderr)
        return 2

    task_path = Path(sys.argv[1])
    task = json.loads(task_path.read_text(encoding="utf-8"))

    base_ref = os.getenv("BASE_REF", "origin/main")
    diff_range = f"{base_ref}...HEAD"

    try:
        changed_raw = run(["git", "diff", "--name-only", diff_range])
    except subprocess.CalledProcessError as exc:
        print(f"Failed to read git diff for range {diff_range}", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 2

    changed_files = [line for line in changed_raw.splitlines() if line.strip()]

    allowed = task.get("allowed_files", [])
    forbidden = task.get("forbidden_files", [])

    errors = []

    for file in changed_files:
        if matches(file, forbidden):
            errors.append(f"FORBIDDEN_CHANGED: {file}")

        if not matches(file, allowed):
            errors.append(f"NOT_ALLOWED: {file}")

    print("Changed files:")
    if changed_files:
        for file in changed_files:
            print(f"- {file}")
    else:
        print("- none")

    if errors:
        print("\nBoundary violations:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nBoundary check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
