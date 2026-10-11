"""Prompt loading and message layout."""
import pytest

from agent.prompt import EXAMPLES, build_messages, load_prompt


def test_document_goes_in_the_user_message_only():
    system, user = build_messages("RULES", "Nome: Ana\n")
    assert system == "RULES"
    assert user == "<document>\nNome: Ana\n</document>\n"


def test_empty_prompt_file_is_refused(tmp_path):
    empty = tmp_path / "prompt.txt"
    empty.write_text("  \n")
    with pytest.raises(ValueError, match="is empty"):
        load_prompt(empty)


def test_example_prompts_are_usable():
    prompts = sorted(EXAMPLES.glob("*.txt"))
    for path in prompts:
        assert "{{" not in load_prompt(path), path.name
