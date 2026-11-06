"""End-to-end tests against a real Git: the hook is installed as an actual Git hook,
so Git's own behaviour (empty-message abort, merges, comment stripping) is part of the test."""

import os
import runpy
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from auto_smart_commit.cli import main

ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str, editor: str = "true", check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **ENV, "GIT_EDITOR": editor}
    return subprocess.run(["git", *args], cwd=repo, env=env, check=check, capture_output=True, text=True)


def last_message(repo: Path) -> str:
    return git(repo, "log", "-1", "--format=%B").stdout.strip()


def write_hook(hooks: Path, name: str, *extra: str) -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    script = hooks / name
    command = f'exec "{sys.executable}" -m auto_smart_commit {" ".join(extra)} "$@"'
    script.write_text(f'#!/bin/sh\nPYTHONPATH="{src}" {command}\n', encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    git(path, "init", "-q", "-b", "PROJ-123_login-form")
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    write_hook(hooks, "commit-msg")
    write_hook(hooks, "prepare-commit-msg", "--prefill")
    git(path, "config", "core.hooksPath", str(hooks))
    monkeypatch.chdir(path)
    return path


def commit_file(repo: Path, name: str, *args: str, editor: str = "true") -> subprocess.CompletedProcess[str]:
    (repo / name).write_text(name, encoding="utf-8")
    git(repo, "add", name)
    return git(repo, "commit", *args, editor=editor, check=False)


def test_message_option(repo: Path) -> None:
    commit_file(repo, "a", "-m", "Add login form", "-m", "Some body.")
    assert last_message(repo) == "PROJ-123 Add login form\n\nSome body."


def test_editor_message(repo: Path) -> None:
    editor = "sed -i.bak '1s/$/Written in the editor/'"
    assert commit_file(repo, "a", editor=editor).returncode == 0
    assert last_message(repo) == "PROJ-123 Written in the editor"


def test_untouched_editor_aborts(repo: Path) -> None:
    result = commit_file(repo, "a", editor="true")
    assert result.returncode != 0
    assert "empty commit message" in result.stderr.lower()


def test_verbose_commit(repo: Path) -> None:
    editor = "sed -i.bak '1s/$/Verbose commit/'"
    assert commit_file(repo, "a", "-v", editor=editor).returncode == 0
    assert last_message(repo) == "PROJ-123 Verbose commit"


def test_fixup_keeps_autosquash_working(repo: Path) -> None:
    commit_file(repo, "a", "-m", "Add login form")
    commit_file(repo, "b", "--fixup", "HEAD")
    assert last_message(repo) == "fixup! PROJ-123 Add login form"


def test_amend_keeps_message(repo: Path) -> None:
    commit_file(repo, "a", "-m", "Add login form")
    (repo / "a").write_text("changed", encoding="utf-8")
    git(repo, "commit", "-a", "--amend", "--no-edit")
    assert last_message(repo) == "PROJ-123 Add login form"


def test_merge_commit_untouched(repo: Path) -> None:
    commit_file(repo, "a", "-m", "Base")
    git(repo, "checkout", "-q", "-b", "other")
    commit_file(repo, "b", "-m", "Other side")
    git(repo, "checkout", "-q", "PROJ-123_login-form")
    commit_file(repo, "c", "-m", "This side")
    git(repo, "merge", "-q", "--no-ff", "other", "--no-edit")
    assert last_message(repo) == "Merge branch 'other' into PROJ-123_login-form"


def test_branch_without_key(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "develop")
    commit_file(repo, "a", "-m", "No key here")
    assert last_message(repo) == "No key here"


def test_detached_head(repo: Path) -> None:
    commit_file(repo, "a", "-m", "Base")
    git(repo, "checkout", "-q", "--detach")
    commit_file(repo, "b", "-m", "Detached")
    assert last_message(repo) == "Detached"


def test_custom_comment_char(repo: Path) -> None:
    git(repo, "config", "core.commentChar", ";")
    editor = "sed -i.bak '1s/$/With semicolon comments/'"
    assert commit_file(repo, "a", editor=editor).returncode == 0
    assert last_message(repo) == "PROJ-123 With semicolon comments"


def test_cli_unreadable_file_does_not_block(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(repo / "missing")]) == 0
    assert "cannot read" in capsys.readouterr().err


def test_cli_prefill_skips_amend_source(repo: Path) -> None:
    message = repo / "MSG"
    message.write_text("", encoding="utf-8")
    assert main([str(message), "commit", "HEAD", "--prefill"]) == 0
    assert message.read_text(encoding="utf-8") == ""


def test_cli_prefill_source_from_pre_commit_env(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRE_COMMIT_COMMIT_MSG_SOURCE", "merge")
    message = repo / "MSG"
    message.write_text("", encoding="utf-8")
    assert main([str(message), "--prefill"]) == 0
    assert message.read_text(encoding="utf-8") == ""


def test_cli_ignore_case(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feature/shop-42-cart")
    message = repo / "MSG"
    message.write_text("Fix cart\n", encoding="utf-8")
    assert main([str(message), "--ignore-case"]) == 0
    assert message.read_text(encoding="utf-8") == "SHOP-42 Fix cart\n"


def test_module_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "auto_smart_commit", "--version"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.startswith("auto-smart-commit ")


def test_module_entry_point(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    message = repo / "MSG"
    message.write_text("Via module\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["auto_smart_commit", str(message)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("auto_smart_commit", run_name="__main__")
    assert exit_info.value.code == 0
    assert message.read_text(encoding="utf-8") == "PROJ-123 Via module\n"
