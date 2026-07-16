from __future__ import annotations

import questionary

from bfabric_scripts.cli.interactive import confirm, select_choice, select_or_input, text_input


class TestSelectChoice:
    def test_delegates_to_questionary_select(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "TEST"
        select = mocker.patch("bfabric_scripts.cli.interactive.questionary.select", return_value=question)
        assert select_choice("Pick", ["PROD", "TEST"], default="TEST") == "TEST"
        select.assert_called_once_with(
            "Pick", choices=["PROD", "TEST"], default="TEST", use_search_filter=False, use_jk_keys=True
        )

    def test_describe_builds_labelled_choices_but_returns_plain_value(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "PROD"
        select = mocker.patch("bfabric_scripts.cli.interactive.questionary.select", return_value=question)
        assert select_choice("Pick", ["PROD", "TEST"], describe=lambda c: f"{c} info") == "PROD"
        passed = select.call_args.kwargs["choices"]
        assert all(isinstance(choice, questionary.Choice) for choice in passed)
        assert [choice.title for choice in passed] == ["PROD info", "TEST info"]
        assert [choice.value for choice in passed] == ["PROD", "TEST"]

    def test_search_flag_enables_live_filter(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "PROD"
        select = mocker.patch("bfabric_scripts.cli.interactive.questionary.select", return_value=question)
        select_choice("Pick", ["PROD", "TEST"], search=True)
        assert select.call_args.kwargs["use_search_filter"] is True
        # j/k must be released as navigation keys so they can be typed into the filter.
        assert select.call_args.kwargs["use_jk_keys"] is False


class TestSelectOrInput:
    def test_maps_empty_answer_to_none(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = ""
        mocker.patch("bfabric_scripts.cli.interactive.questionary.autocomplete", return_value=question)
        assert select_or_input("Pick", ["PROD"]) is None

    def test_returns_typed_value_and_hints_tab_when_choices_present(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "NEW"
        autocomplete = mocker.patch("bfabric_scripts.cli.interactive.questionary.autocomplete", return_value=question)
        assert select_or_input("Pick", ["PROD"], default="X") == "NEW"
        # The Tab-autocomplete hint is appended when there are suggestions to complete.
        autocomplete.assert_called_once_with("Pick (Tab to autocomplete)", choices=["PROD"], default="X")

    def test_no_hint_when_no_choices(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "NEW"
        autocomplete = mocker.patch("bfabric_scripts.cli.interactive.questionary.autocomplete", return_value=question)
        assert select_or_input("Pick", []) == "NEW"
        autocomplete.assert_called_once_with("Pick", choices=[], default="")


class TestConfirm:
    def test_returns_true_when_confirmed(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = True
        confirm_prompt = mocker.patch("bfabric_scripts.cli.interactive.questionary.confirm", return_value=question)
        assert confirm("Delete?") is True
        confirm_prompt.assert_called_once_with("Delete?", default=False)

    def test_returns_false_when_declined(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = False
        mocker.patch("bfabric_scripts.cli.interactive.questionary.confirm", return_value=question)
        assert confirm("Delete?") is False

    def test_cancel_returns_none(self, mocker):
        # Ctrl-C / Esc yields None from questionary; confirm surfaces it so callers can tell an
        # aborted prompt apart from an explicit "no".
        question = mocker.MagicMock()
        question.ask.return_value = None
        mocker.patch("bfabric_scripts.cli.interactive.questionary.confirm", return_value=question)
        assert confirm("Delete?") is None


class TestTextInput:
    def test_returns_entered_value(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "api:read foo"
        text = mocker.patch("bfabric_scripts.cli.interactive.questionary.text", return_value=question)
        assert text_input("Scopes", default="api:read") == "api:read foo"
        text.assert_called_once_with("Scopes", default="api:read")

    def test_maps_empty_answer_to_none(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = ""
        mocker.patch("bfabric_scripts.cli.interactive.questionary.text", return_value=question)
        assert text_input("Scopes") is None
