"""Command line entry point, called by pre-commit or directly as a Git hook."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from auto_smart_commit import __version__, git
from auto_smart_commit.message import finalize, issue_key_from_branch, prefill

# prepare-commit-msg sources for which Git wrote the message itself.
_SKIPPED_SOURCES = {"merge", "squash", "commit"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-smart-commit",
        description="Prefix the commit message with the Jira issue key from the branch name.",
    )
    parser.add_argument("message_file", type=Path, help="commit message file, passed by Git")
    parser.add_argument("source", nargs="?", default="", help="prepare-commit-msg source, passed by Git")
    parser.add_argument("object", nargs="?", default="", help="prepare-commit-msg commit, passed by Git")
    parser.add_argument(
        "--prefill",
        action="store_true",
        help="prepare-commit-msg mode: only put the key into an empty message before the editor opens",
    )
    parser.add_argument(
        "--comment",
        action="store_true",
        help="turn the commit body into a Jira #comment (off by default)",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="also accept lowercase keys in the branch name, e.g. feature/proj-123-login",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    issue_key = issue_key_from_branch(git.current_branch(), ignore_case=args.ignore_case)
    if not issue_key or git.is_merging():
        return 0

    try:
        text = args.message_file.read_text(encoding="utf-8")
    except OSError as error:
        print(f"auto-smart-commit: cannot read {args.message_file}: {error}", file=sys.stderr)
        return 0  # never block a commit because of this hook

    comment = git.comment_string()
    if args.prefill:
        # Git passes the source as an argument, pre-commit as an environment variable.
        source = args.source or os.environ.get("PRE_COMMIT_COMMIT_MSG_SOURCE", "")
        if source in _SKIPPED_SOURCES:
            return 0
        updated = prefill(text, issue_key, comment=comment)
    else:
        updated = finalize(text, issue_key, add_comment=args.comment, comment=comment)

    if updated != text:
        args.message_file.write_text(updated, encoding="utf-8")
    return 0
