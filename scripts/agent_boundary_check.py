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


def get_working_tree_changed_files() -> list[str]:
    files: set[str] = set()

    staged = run(["git", "diff", "--cached", "--name-only"])
    for line in staged.splitlines():
        if line.strip():
            files.add(line.strip())

    unstaged = run(["git", "diff", "--name-only"])
    for line in unstaged.splitlines():
        if line.strip():
            files.add(line.strip())

    untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    for line in untracked.splitlines():
        if line.strip():
            files.add(line.strip())

    return sorted(files)


def main() -> int:
    include_working_tree = False
    task_arg = None

    for arg in sys.argv[1:]:
        if arg == "--include-working-tree":
            include_working_tree = True
        elif task_arg is None:
            task_arg = arg
        else:
            print("Usage: agent_boundary_check.py [--include-working-tree] <task.json>", file=sys.stderr)
            return 2

    if task_arg is None:
        print("Usage: agent_boundary_check.py [--include-working-tree] <task.json>", file=sys.stderr)
        return 2

    task_path = Path(task_arg)
    task = json.loads(task_path.read_text(encoding="utf-8"))

    base_ref = os.getenv("BASE_REF", "origin/main")
    diff_range = f"{base_ref}...HEAD"

    try:
        changed_raw = run(["git", "diff", "--name-only", diff_range])
    except subprocess.CalledProcessError as exc:
        print(f"Failed to read git diff for range {diff_range}", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 2

    changed_files: list[str] = [line for line in changed_raw.splitlines() if line.strip()]

    if include_working_tree:
        try:
            working_tree_files = get_working_tree_changed_files()
        except subprocess.CalledProcessError as exc:
            print("Failed to read working tree changes", file=sys.stderr)
            print(exc, file=sys.stderr)
            return 2

        combined: set[str] = set(changed_files)
        combined.update(working_tree_files)
        changed_files = sorted(combined)

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
