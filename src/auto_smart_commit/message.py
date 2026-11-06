"""Pure functions on commit messages. No Git calls, no file access."""

import re
from dataclasses import dataclass

# Jira project keys start with a letter, followed by letters, digits or underscores.
# The lookarounds keep "XABC-1" or "ABC-12x" from matching only a part.
_KEY = r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9_]+-[0-9]+(?![0-9A-Za-z])"
ISSUE_KEY_RE = re.compile(_KEY)
ISSUE_KEY_ANY_CASE_RE = re.compile(_KEY, re.IGNORECASE)
LEADING_ISSUE_KEY_RE = re.compile(rf"^{_KEY}")

SCISSORS = "------------------------ >8 ------------------------"

# Subjects Git generates or relies on. "fixup!"/"squash!"/"amend!" must stay at the very
# start, otherwise `git rebase --autosquash` no longer finds the commit they belong to.
_GENERATED_SUBJECT_RE = re.compile(
    r"^(fixup! |squash! |amend! |Merge (branch|branches|remote-tracking branch|tag|commit|pull request) "
    r"|Merge [0-9a-f]{7,40}|Squashed commit of the following:)"
)


def issue_key_from_branch(branch: str, ignore_case: bool = False) -> str | None:
    """Return the first Jira issue key in a branch name.

    ``PROJ-123_fix-login`` and ``feature/PROJ-123_fix-login`` give ``PROJ-123``. With
    ``ignore_case`` a lowercase ``feature/proj-123-fix`` gives ``PROJ-123`` as well.
    """
    pattern = ISSUE_KEY_ANY_CASE_RE if ignore_case else ISSUE_KEY_RE
    match = pattern.search(branch)
    return match.group(0).upper() if match else None


@dataclass
class Message:
    """A commit message split into the author's text and Git's trailing comment block
    (editor help text and, with ``commit -v``, everything from the scissors line on)."""

    content: list[str]
    comments: list[str]

    @classmethod
    def parse(cls, text: str, comment: str = "#") -> "Message":
        lines = text.splitlines()
        end = len(lines)
        for index, line in enumerate(lines):
            if line.startswith(comment) and SCISSORS in line:
                end = index
                break
        start = end
        while start > 0 and (lines[start - 1].startswith(comment) or not lines[start - 1].strip()):
            start -= 1
        content = lines[:start]
        while content and not content[0].strip():
            content.pop(0)
        return cls(content=content, comments=lines[start:])

    @property
    def subject(self) -> str:
        return self.content[0] if self.content else ""

    @property
    def body(self) -> list[str]:
        body = self.content[1:]
        while body and not body[0].strip():
            body = body[1:]
        return body

    def render(self) -> str:
        lines = list(self.content)
        comments = list(self.comments)
        while comments and not comments[0].strip():
            comments.pop(0)
        if comments:
            if lines:
                lines.append("")
            lines += comments
        return "\n".join(lines) + "\n" if lines else ""


def is_generated(subject: str) -> bool:
    """True for subjects Git writes itself or needs unchanged (merges, fixups)."""
    return bool(_GENERATED_SUBJECT_RE.match(subject))


def finalize(text: str, issue_key: str, add_comment: bool = False, comment: str = "#") -> str:
    """The commit-msg step: put the issue key in front of the subject.

    - A subject that already starts with an issue key stays as it is.
    - Merge, squash and fixup subjects stay as they are.
    - A message that consists of nothing but the issue key (prefilled, then left
      untouched in the editor) is emptied, so Git aborts as for any empty message.
    - With ``add_comment`` the body becomes a Jira ``#comment``, unless it has one.
    - ``#time`` is never added.
    """
    message = Message.parse(text, comment)
    if not message.content:
        return text

    subject = message.subject.strip()
    if ISSUE_KEY_RE.fullmatch(subject) and not any(line.strip() for line in message.body):
        message.content = []
        return message.render()

    if is_generated(subject):
        return text

    if not LEADING_ISSUE_KEY_RE.match(subject):
        subject = f"{issue_key} {subject}"

    body = message.body
    if add_comment and body and "#comment" not in "\n".join(body):
        body[0] = f"{issue_key} #comment {body[0]}"

    while body and not body[-1].strip():
        body.pop()

    message.content = [subject] + (["", *body] if body else [])
    return message.render()


def prefill(text: str, issue_key: str, comment: str = "#") -> str:
    """The prepare-commit-msg step: put the issue key into an empty message so it is
    already there when the editor opens. Messages with content stay unchanged."""
    message = Message.parse(text, comment)
    if message.content:
        return text
    message.content = [f"{issue_key} "]
    return message.render()
