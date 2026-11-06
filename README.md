# auto-smart-commit

[![test](https://github.com/davidzach/auto-smart-commit/actions/workflows/test.yml/badge.svg)](https://github.com/davidzach/auto-smart-commit/actions/workflows/test.yml)

A [pre-commit](https://pre-commit.com) hook that puts the Jira issue key from the branch name in front of every commit message.

```
branch:  PROJ-123_login-form
commit:  git commit -m "Add login form"
result:  PROJ-123 Add login form
```

Based on [superlinear-ai/auto-smart-commit](https://github.com/superlinear-ai/auto-smart-commit) (MIT), with one deliberate difference: **it never logs time.**

## Why no automatic `#time`

The original hook appends `ISSUE-KEY #time …` to every commit, computed as the time since your last commit on *any* branch, minus nights and lunch breaks. Weekends, holidays, meetings and work on other projects all count as working time. After four weeks without a commit in a repository, a single commit booked `5w 0d 2h 41m` to a Jira ticket.

The gap between two commits says nothing about the time spent on the second one, so no formula fixes this. Time is logged by whoever knows it: in Jira, or by writing the command into the commit message yourself. The hook keeps it as written:

```
PROJ-123 Add login form

PROJ-123 #time 1h 25m Add login form
```

## Installation

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, commit-msg, prepare-commit-msg]

repos:
  - repo: https://github.com/davidzach/auto-smart-commit
    rev: v2.0.0
    hooks:
      - id: auto-smart-commit           # required: adds the key (commit-msg)
      - id: auto-smart-commit-prefill   # optional: shows the key in the editor (prepare-commit-msg)
```

```bash
pre-commit install
```

**Without `default_install_hook_types`**, install the hook types explicitly. Plain `pre-commit install` only installs the `pre-commit` hook type, and then this hook silently never runs:

```bash
pre-commit install --hook-type commit-msg --hook-type prepare-commit-msg
```

Keep the `rev` current with `pre-commit autoupdate`.

## Behaviour

Branch `PROJ-123_login-form`:

| You commit | Result |
|---|---|
| `git commit -m "Add login form"` | `PROJ-123 Add login form` |
| `git commit -m "SHOP-9 Fix typo"` (subject starts with a key) | unchanged |
| `git commit -m "Revert SHOP-9 change"` (key only mentioned) | `PROJ-123 Revert SHOP-9 change` |
| `git commit` → editor, type `Add login form` | `PROJ-123 Add login form` (with prefill: key already in the editor) |
| `git commit` → editor, close without typing | aborted, like any empty commit message |
| `git commit --fixup HEAD` | `fixup! …` unchanged, `rebase --autosquash` keeps working |
| merge commit, `git merge --squash` | unchanged |
| `git commit --amend --no-edit` | unchanged |
| message already contains `#time` or `#comment` | kept as written |

No key in the branch name (`main`, `develop`, detached HEAD during a rebase): every message stays unchanged.

The rest of the subject is never rewritten: no capitalisation, no trailing-dot removal. Git's comment block (editor help text, the diff of `commit -v`) stays where Git expects it; `core.commentChar` and `core.commentString` are honoured.

If the hook fails for any reason, it reports the error and lets the commit through.

## Options

Add them as `args` in `.pre-commit-config.yaml`:

```yaml
      - id: auto-smart-commit
        args: [--comment, --ignore-case]
```

| Option | Effect |
|---|---|
| `--comment` | Turns the commit body into a Jira `#comment` (first body line prefixed with `PROJ-123 #comment`). Off by default: a technical commit body rarely belongs in a ticket a customer may read. |
| `--ignore-case` | Also accepts lowercase keys in the branch name: `feature/proj-123-login` → `PROJ-123`. Off by default, because a branch like `fix-123` would then count as issue `FIX-123`. |

Branch names may carry the key anywhere (`PROJ-123_login`, `feature/PROJ-123-login`); the first key wins.

## When does Jira pick up `#time` and `#comment`?

Smart commit commands are processed by Jira, not by this hook, and only if:

- the repository is connected to Jira (e.g. GitHub for Jira, GitLab for Jira Cloud, Bitbucket),
- the commit author's email address belongs to a Jira user with permission on the issue,
- the commit is pushed to the connected host.

If a command is ignored, check these three first.

## Migrating

**From superlinear-ai / radix-ai auto-smart-commit:** replace `repo` and `rev`, keep `id: auto-smart-commit`, add `default_install_hook_types` (see above), run `pre-commit install`. Optionally remove the old `prepare-commit-msg` hook script: `pre-commit uninstall --hook-type prepare-commit-msg`, then `pre-commit install` again.

**From v1:** v1 ran in `prepare-commit-msg`, v2 runs in `commit-msg`. Add `default_install_hook_types` and run `pre-commit install`. See [CHANGELOG.md](CHANGELOG.md).

## Using it without pre-commit

```bash
pip install git+https://github.com/davidzach/auto-smart-commit@v2.0.0
printf '#!/bin/sh\nexec auto-smart-commit "$@"\n' > .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg
```

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install --group dev .
.venv/bin/python -m pytest       # unit tests + end-to-end tests against a real Git
.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/mypy
```

See [CLAUDE.md](CLAUDE.md) for conventions and the release procedure.

## License

MIT, see [LICENSE](LICENSE).
