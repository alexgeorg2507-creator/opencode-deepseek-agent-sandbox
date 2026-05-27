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


def test_forbidden_change_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        _run(["git", "checkout", "-b", "feature/bad"], cwd=tmp)

        (tmp / "Dockerfile").write_text("FROM alpine\n")
        _run(["git", "add", "Dockerfile"], cwd=tmp)
        _run(["git", "commit", "-m", "bad change"], cwd=tmp)

        task = _write_task(tmp, {
            "allowed_files": ["README.md", "task.json"],
            "forbidden_files": ["Dockerfile"],
        })

        env = {**os.environ, "BASE_REF": "main"}
        result = subprocess.run(
            [sys.executable, str(checker), str(task)],
            cwd=tmp, capture_output=True, text=True, env=env,
        )

        assert result.returncode != 0, f"Expected non-zero, got {result.returncode}"
        assert "FORBIDDEN_CHANGED" in result.stdout, (
            f"Expected FORBIDDEN_CHANGED in output, got:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def test_allowed_change_passes():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        checker = _make_checker(tmp)
        _init_repo(tmp)

        (tmp / "README.md").write_text("# repo\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "baseline"], cwd=tmp)
        _run(["git", "branch", "-m", "main"], cwd=tmp)

        _run(["git", "checkout", "-b", "feature/good"], cwd=tmp)

        (tmp / "README.md").write_text("# repo\n\nallowed change\n")
        _run(["git", "add", "README.md"], cwd=tmp)
        _run(["git", "commit", "-m", "good change"], cwd=tmp)

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
            f"Expected zero for allowed change, stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "Boundary check: PASS" in result.stdout


if __name__ == "__main__":
    test_forbidden_change_fails()
    print("test_forbidden_change_fails: PASS")
    test_allowed_change_passes()
    print("test_allowed_change_passes: PASS")
