"""The few Git facts the hook needs. Every function degrades to a safe default."""

import subprocess


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def current_branch() -> str:
    """The checked-out branch; empty in detached HEAD state (e.g. during a rebase)."""
    return _git("symbolic-ref", "--short", "-q", "HEAD") or ""


def comment_string() -> str:
    """Git's comment prefix: core.commentString (Git 2.45+), else core.commentChar, else ``#``."""
    for key in ("core.commentString", "core.commentChar"):
        value = _git("config", "--get", key)
        # "auto" lets Git choose after the hooks ran; the template still uses "#".
        if value and value != "auto":
            return value
    return "#"


def is_merging() -> bool:
    """True while a merge commit is being created."""
    return _git("rev-parse", "-q", "--verify", "MERGE_HEAD") is not None
