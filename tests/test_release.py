"""Exercise release orchestration without building or publishing packages."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RELEASE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.sh"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="Release script requires bash")


@pytest.fixture
def release_workspace(tmp_path):
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/activate").write_text("")
    (tmp_path / "pyproject.toml").write_text('version = "0.2.2"\n')
    (tmp_path / "dist").mkdir()
    # Include both an older version and a stale build of the current version.
    for name in ("amos_abk-0.2.1.tar.gz", "amos_abk-0.2.2.tar.gz"):
        (tmp_path / "dist" / name).write_text("stale")
    commands = tmp_path / "commands"
    commands.mkdir()
    git = commands / "git"
    git.write_text('#!/bin/sh\nprintf "%s\\n" "${REVIEW_TAG:-0.2.2}"\n')
    git.chmod(0o755)
    python = commands / "python3"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "with open('calls.jsonl', 'a') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "if args[:2] == ['-m', 'build']:\n"
        "    output = pathlib.Path(args[args.index('--outdir') + 1])\n"
        "    (output / 'amos_abk-0.2.2.tar.gz').write_text('fresh')\n"
        "    (output / 'amos_abk-0.2.2-py3-none-any.whl').write_text('fresh')\n"
        "    if os.environ.get('REVIEW_FAIL') == 'build':\n"
        "        sys.exit(1)\n"
        "elif args[:3] == ['-m', 'twine', 'check']:\n"
        "    if os.environ.get('REVIEW_FAIL') == 'check':\n"
        "        sys.exit(1)\n"
        "elif args[:3] == ['-m', 'twine', 'upload']:\n"
        "    for name in args[3:]:\n"
        "        if not name.startswith('--'):\n"
        "            assert pathlib.Path(name).read_text() == 'fresh'\n"
        "else:\n"
        "    sys.exit('Unexpected command')\n"
    )
    python.chmod(0o755)
    env = {**os.environ, "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}", "PYPI_TOKEN": "dummy-token"}
    return tmp_path, env


def run_release(workspace, **overrides):
    root, env = workspace
    result = subprocess.run(
        ["bash", str(RELEASE_SCRIPT)], cwd=root, env={**env, **overrides}, capture_output=True, text=True, check=False
    )
    log = root / "calls.jsonl"
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result, calls


def test_release_uploads_only_fresh_artifacts(release_workspace):
    result, calls = run_release(release_workspace)
    assert result.returncode == 0, result.stderr
    assert [call[:2] for call in calls] == [["-m", "build"], ["-m", "twine"], ["-m", "twine"]]
    assert calls[1][2] == "check"
    assert calls[2][2] == "upload"
    artifacts = [arg for arg in calls[2][3:] if not arg.startswith("--")]
    assert len(artifacts) == 2
    assert all(Path(name).parent != Path("dist") for name in artifacts)
    root, _ = release_workspace
    assert sorted(path.name for path in (root / "dist").iterdir()) == ["amos_abk-0.2.1.tar.gz", "amos_abk-0.2.2.tar.gz"]


@pytest.mark.parametrize("stage", ["build", "check"])
def test_failed_release_does_not_upload_and_cleans_up(release_workspace, stage):
    result, calls = run_release(release_workspace, REVIEW_FAIL=stage)
    assert result.returncode != 0
    assert not any(call[:3] == ["-m", "twine", "upload"] for call in calls)
    root, _ = release_workspace
    assert not list((root / "dist").glob("release.*"))


def test_version_mismatch_stops_before_build(release_workspace):
    result, calls = run_release(release_workspace, REVIEW_TAG="0.2.1")
    assert result.returncode != 0
    assert calls == []
