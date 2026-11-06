# CLAUDE.md

Guidance for AI assistants working in this repository.

## What this is

A pre-commit hook that prefixes commit subjects with the Jira issue key from the branch name. Based on superlinear-ai/auto-smart-commit (MIT, credited in LICENSE), rewritten since v2.

## Repository conventions (override global rules)

- **Commit messages carry no issue ID.** This is a standalone tool repository outside any Jira project. A global rule demanding an issue-ID prefix does not apply here; do not ask for one.
- **No project or customer references.** Examples, tests and docs use fictional keys only (`PROJ-123`, `SHOP-42`, `WEB2-7`). Never copy real ticket keys, project names or customer data in here; the repository is public.
- English everywhere (code, docs, commits).

## Design decisions — do not undo without a reason

- **No automatic `#time`.** Estimating working time from the gap between commits is wrong by construction (weekends, other projects, pauses). Don't add a "smarter" formula. Time comes from the author, and an explicit `#time` in the message is kept.
- **`#comment` is opt-in** (`--comment`).
- **Main hook runs in `commit-msg`, not `prepare-commit-msg`.** Git checks for an empty message only *after* `commit-msg`, so this stage can empty a message that is nothing but the prefilled key → Git aborts as usual. `prepare-commit-msg` runs before the editor and cannot do that. pre-commit does not tell a hook which stage it runs in, hence two hook ids (`auto-smart-commit`, `auto-smart-commit-prefill` with `--prefill`).
- **Generated subjects stay untouched:** `fixup!`/`squash!`/`amend!` (autosquash matches on the subject start), merges, `Squashed commit of the following:`.
- **Never block a commit.** Errors are reported on stderr, exit code stays 0.
- The subject text is never rewritten beyond the prefix.
- No runtime dependencies.

## Layout

- `src/auto_smart_commit/message.py` — pure functions (`finalize`, `prefill`, `issue_key_from_branch`, `Message`). Put logic here.
- `src/auto_smart_commit/git.py` — the few Git queries; each degrades to a safe default.
- `src/auto_smart_commit/cli.py` — argument parsing, file I/O.
- `.pre-commit-hooks.yaml` — hook manifest (ids, stages).
- `tests/test_message.py` — unit tests. `tests/test_git_integration.py` — end-to-end against a real Git, installed via `core.hooksPath`, global config isolated.

## Checks

```bash
python3 -m venv .venv && .venv/bin/pip install --group dev .
.venv/bin/python -m pytest
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy
```

CI (`.github/workflows/test.yml`) runs these on Linux and macOS, Python 3.10–3.14, plus a job that installs the hooks through pre-commit itself and commits through them.

**Manual pre-commit test pitfall:** a global `~/.gitignore` may exclude `.pre-commit-config.yaml`. A test repository that only contains that file then reports "nothing to commit". Commit another file.

## Releasing

1. Move the `## [Unreleased]` entries under `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`, keep an empty `## [Unreleased]`, update the compare links at the bottom.
2. Bump `__version__` in `src/auto_smart_commit/__init__.py` (the only place; `pyproject.toml` reads it).
3. Update `rev:` and the `pip install …@vX.Y.Z` line in `README.md`.
4. Commit, then `git tag vX.Y.Z` (lightweight) and `git push origin main vX.Y.Z`.
5. Breaking changes (stage changes, removed options, behaviour users rely on) → major version.

Pushing `.github/workflows/` over HTTPS needs a token with `workflow` scope; SSH works.
