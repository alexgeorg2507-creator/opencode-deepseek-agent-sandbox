import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd, cwd=None, expect_fail=False):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=not expect_fail
    )


def _make_checker(tmp):
    script_src = Path(__file__).resolve().parent.parent.parent / "scripts" / "agent_boundary_check.py"
    checker = tmp / "agent_boundary_check.py"
    checker.write_text(script_src.read_text(encoding="utf-8"))
    return checker


def _init_repo(tmp):
    _run(["git", "init"], cwd=tmp)
    _run(["git", "config", "user.email", "test@test"], cwd=tmp)
    _run(["git", "config", "user.name", "Test"], cwd=tmp)


def _write_task(tmp, content):
    p = tmp / "task.json"
    p.write_text(json.dumps(content))
    return p


def test_default_mode_ignores_uncommitted():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        (tmp / "Dockerfile").write_text("FROM alpine\n")

        task = _write_task(tmp, {
            "allowed_files": ["README.md", "task.json"],
            "forbidden_files": ["Dockerfile"],
        })

        env = {**os.environ, "BASE_REF": "main"}
        result = subprocess.run(
            [sys.executable, str(checker), str(task)],
            cwd=tmp, capture_output=True, text=True, env=env,
        )

        assert result.returncode == 0, (
            f"Expected 0 (uncommitted ignored), got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "Boundary check: PASS" in result.stdout


def test_include_working_tree_catches_untracked_not_allowed():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        (tmp / "secret.key").write_text("key\n")

        task = _write_task(tmp, {
            "allowed_files": ["README.md", "task.json"],
            "forbidden_files": ["**/*secret*"],
        })

        env = {**os.environ, "BASE_REF": "main"}
        result = subprocess.run(
            [sys.executable, str(checker), "--include-working-tree", str(task)],
            cwd=tmp, capture_output=True, text=True, env=env,
        )

        assert result.returncode != 0, (
            f"Expected non-zero for untracked NOT_ALLOWED, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "NOT_ALLOWED" in result.stdout or "FORBIDDEN_CHANGED" in result.stdout


def test_include_working_tree_catches_unstaged_forbidden():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        (tmp / "Dockerfile").write_text("FROM alpine\n")
        _run(["git", "add", "Dockerfile"], cwd=tmp)
        _run(["git", "commit", "-m", "add Dockerfile"], cwd=tmp)

        (tmp / "Dockerfile").write_text("FROM ubuntu\n")

        task = _write_task(tmp, {
            "allowed_files": ["README.md", "Dockerfile", "task.json"],
            "forbidden_files": ["Dockerfile"],
        })

        env = {**os.environ, "BASE_REF": "HEAD~1"}
        result = subprocess.run(
            [sys.executable, str(checker), "--include-working-tree", str(task)],
            cwd=tmp, capture_output=True, text=True, env=env,
        )

        assert result.returncode != 0, (
            f"Expected non-zero for unstaged forbidden, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "FORBIDDEN_CHANGED" in result.stdout


def test_include_working_tree_passes_with_allowed_untracked():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md", checker.name], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        (tmp / "allowed_new.txt").write_text("new file\n")

        task = _write_task(tmp, {
            "allowed_files": ["README.md", "task.json", "agent_boundary_check.py", "allowed_new.txt"],
            "forbidden_files": ["Dockerfile"],
        })

        env = {**os.environ, "BASE_REF": "main"}
        result = subprocess.run(
            [sys.executable, str(checker), "--include-working-tree", str(task)],
            cwd=tmp, capture_output=True, text=True, env=env,
        )

        assert result.returncode == 0, (
            f"Expected 0 for allowed untracked, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "Boundary check: PASS" in result.stdout


if __name__ == "__main__":
    test_default_mode_ignores_uncommitted()
    print("test_default_mode_ignores_uncommitted: PASS")
    test_include_working_tree_catches_untracked_not_allowed()
    print("test_include_working_tree_catches_untracked_not_allowed: PASS")
    test_include_working_tree_catches_unstaged_forbidden()
    print("test_include_working_tree_catches_unstaged_forbidden: PASS")
    test_include_working_tree_passes_with_allowed_untracked()
    print("test_include_working_tree_passes_with_allowed_untracked: PASS")
