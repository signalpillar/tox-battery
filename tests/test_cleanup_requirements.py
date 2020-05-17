from toxbat.requirements import cleanup_requirements_content
import pytest


@pytest.mark.parametrize(
    "expected, raw",
    [
        # Ignore empty lines
        ("a\nb", "\n\na\n\nb"),
        # The lines are stripped
        ("a", "a   \n"),
        # The comments are ignored
        ("a\nb", "#a\na\n#b\nb"),
        # The items are sorted
        ("a\nb\nc", "#c\nc\nb\n#a\na"),
    ],
)
def test_cleanup(expected, raw):
    assert expected == cleanup_requirements_content(raw)
