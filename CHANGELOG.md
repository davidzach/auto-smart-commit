# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Development tools raised to pytest 9.2, pytest-cov 7.1, ruff 0.17.3 and mypy 2.4.1 (no effect on the hook).

## [2.0.0] - 2026-11-06

### Changed

- **Breaking:** the hook `auto-smart-commit` now runs in the `commit-msg` stage instead of
  `prepare-commit-msg`, so it sees the message after editing. Install the new hook type:
  `pre-commit install --hook-type commit-msg` (or set `default_install_hook_types`). Without it, the
  hook does not run at all.
- Python 3.10 or newer is required (3.9 is end of life).

### Added

- Optional hook `auto-smart-commit-prefill` (`prepare-commit-msg`): shows the issue key in the editor.
- `--ignore-case`: accepts lowercase keys in branch names such as `feature/proj-123-login`.
- Honours `core.commentString` (Git 2.45+) besides `core.commentChar`.
- `--version`, `python -m auto_smart_commit`.

### Fixed

- Closing the editor without writing anything committed a message consisting only of the issue key.
  Git now aborts as for any empty message.
- `fixup!`, `squash!` and `amend!` commits got the key in front and were no longer found by
  `git rebase --autosquash`. They stay unchanged now.
- Merge commits are recognised in the `commit-msg` stage as well (via `MERGE_HEAD` and the subject).
- A hook error (e.g. unreadable message file) no longer blocks the commit.

## 1.0.0 - 2026-11-06 (withdrawn)

- First release, based on superlinear-ai/auto-smart-commit: prefixed the subject with the Jira issue
  key from the branch name (`prepare-commit-msg`), never added `#time`, `#comment` only with
  `--comment`. Withdrawn the same day and replaced by 2.0.0; the tag no longer exists.

[Unreleased]: https://github.com/davidzach/auto-smart-commit/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/davidzach/auto-smart-commit/releases/tag/v2.0.0
