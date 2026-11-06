import pytest

from auto_smart_commit.message import Message, finalize, is_generated, issue_key_from_branch, prefill


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("PROJ-123_fix-login", "PROJ-123"),
        ("feature/SHOP-42_checkout-total", "SHOP-42"),
        ("WEB2-7_header", "WEB2-7"),
        ("AB_CD-12_something", "AB_CD-12"),
        ("PROJ-12-and-PROJ-13", "PROJ-12"),
        ("main", None),
        ("develop", None),
        ("fix-123", None),
        ("feature/proj-123-login", None),
        ("XPROJ-1x", None),
        ("", None),
    ],
)
def test_issue_key_from_branch(branch: str, expected: str | None) -> None:
    assert issue_key_from_branch(branch) == expected


def test_issue_key_from_branch_ignore_case() -> None:
    assert issue_key_from_branch("feature/proj-123-login", ignore_case=True) == "PROJ-123"


class TestFinalize:
    def test_prefixes_subject(self) -> None:
        assert finalize("Add login form\n", "PROJ-1") == "PROJ-1 Add login form\n"

    def test_keeps_subject_that_starts_with_a_key(self) -> None:
        assert finalize("SHOP-9 Fix typo\n", "PROJ-1") == "SHOP-9 Fix typo\n"

    def test_prefixes_subject_that_only_mentions_a_key(self) -> None:
        assert finalize("Revert SHOP-9 change\n", "PROJ-1") == "PROJ-1 Revert SHOP-9 change\n"

    def test_leaves_subject_text_alone(self) -> None:
        assert finalize("fix the thing.\n", "PROJ-1") == "PROJ-1 fix the thing.\n"

    def test_never_adds_time(self) -> None:
        assert finalize("Subject\n\nBody text.\n", "PROJ-1") == "PROJ-1 Subject\n\nBody text.\n"

    def test_keeps_an_explicit_time_line(self) -> None:
        text = "PROJ-1 Subject\n\nBody.\n\nPROJ-1 #time 1h 25m PROJ-1 Subject\n"
        assert finalize(text, "PROJ-1") == text

    def test_comment_is_opt_in(self) -> None:
        result = finalize("Subject\n\nBody.\n", "PROJ-1", add_comment=True)
        assert result == "PROJ-1 Subject\n\nPROJ-1 #comment Body.\n"

    def test_comment_is_not_added_twice(self) -> None:
        text = "PROJ-1 Subject\n\nPROJ-1 #comment Body.\n"
        assert finalize(text, "PROJ-1", add_comment=True) == text

    def test_comment_without_body_does_nothing(self) -> None:
        assert finalize("Subject\n", "PROJ-1", add_comment=True) == "PROJ-1 Subject\n"

    def test_empty_message_stays_empty(self) -> None:
        text = "\n# Please enter the commit message for your changes.\n"
        assert finalize(text, "PROJ-1") == text

    def test_untouched_prefill_is_emptied(self) -> None:
        text = "PROJ-1 \n\n# Please enter the commit message for your changes.\n"
        assert finalize(text, "PROJ-1") == "# Please enter the commit message for your changes.\n"

    def test_untouched_prefill_without_comments_is_emptied(self) -> None:
        assert finalize("PROJ-1\n", "PROJ-1") == ""

    def test_key_with_body_is_kept(self) -> None:
        assert finalize("PROJ-1\n\nOnly a body.\n", "PROJ-1") == "PROJ-1\n\nOnly a body.\n"

    @pytest.mark.parametrize(
        "subject",
        [
            "fixup! PROJ-1 Add login form",
            "squash! Add login form",
            "amend! Add login form",
            "Merge branch 'main' into PROJ-1_login",
            "Merge remote-tracking branch 'origin/main'",
            "Merge pull request #12 from someone/branch",
            "Merge tag 'v1.0.0'",
            "Squashed commit of the following:",
        ],
    )
    def test_generated_subjects_stay(self, subject: str) -> None:
        text = f"{subject}\n"
        assert finalize(text, "PROJ-1") == text

    def test_verbose_diff_below_scissors_is_untouched(self) -> None:
        text = (
            "Subject\n\n"
            "# Please enter the commit message.\n"
            "# ------------------------ >8 ------------------------\n"
            "# Do not modify or remove the line above.\n"
            "diff --git a/x b/x\n"
            "+Subject line inside the diff\n"
        )
        result = finalize(text, "PROJ-1")
        assert result.startswith("PROJ-1 Subject\n\n# Please enter")
        assert result.endswith("diff --git a/x b/x\n+Subject line inside the diff\n")

    def test_custom_comment_string(self) -> None:
        assert finalize("Subject\n\n; help\n", "PROJ-1", comment=";") == "PROJ-1 Subject\n\n; help\n"

    def test_strips_surrounding_blank_lines(self) -> None:
        assert finalize("\n\nSubject\n\n\nBody\n\n\n", "PROJ-1") == "PROJ-1 Subject\n\nBody\n"

    def test_is_idempotent(self) -> None:
        once = finalize("Subject\n\nBody.\n", "PROJ-1", add_comment=True)
        assert finalize(once, "PROJ-1", add_comment=True) == once


class TestPrefill:
    def test_fills_empty_message(self) -> None:
        text = "\n# Please enter the commit message.\n"
        assert prefill(text, "PROJ-1") == "PROJ-1 \n\n# Please enter the commit message.\n"

    def test_fills_completely_empty_file(self) -> None:
        assert prefill("", "PROJ-1") == "PROJ-1 \n"

    def test_keeps_existing_content(self) -> None:
        text = "Given with -m\n"
        assert prefill(text, "PROJ-1") == text

    def test_prefill_then_untouched_editor_ends_empty(self) -> None:
        text = "\n# Please enter the commit message.\n"
        assert finalize(prefill(text, "PROJ-1"), "PROJ-1") == "# Please enter the commit message.\n"


def test_message_render_without_comments() -> None:
    assert Message(content=["a", "", "b"], comments=[]).render() == "a\n\nb\n"


def test_is_generated() -> None:
    assert is_generated("fixup! x")
    assert not is_generated("Fix merge conflict handling")
