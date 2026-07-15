from __future__ import annotations

import questionary

from bfabric_scripts.cli.interactive import resolve_choice, select_choice, select_or_input


class TestResolveChoice:
    def test_returns_explicit_value_verbatim(self, mocker):
        # An explicit value short-circuits: no interactivity check, no prompt.
        select = mocker.patch("bfabric_scripts.cli.interactive.select_choice")
        assert resolve_choice("TEST", ["PROD", "TEST"], message="Pick") == "TEST"
        select.assert_not_called()

    def test_returns_none_when_not_interactive(self, mocker):
        mocker.patch("bfabric_scripts.cli.interactive.is_interactive", return_value=False)
        assert resolve_choice(None, ["PROD", "TEST"], message="Pick") is None

    def test_interactive_uses_select_choice(self, mocker):
        mocker.patch("bfabric_scripts.cli.interactive.is_interactive", return_value=True)
        select = mocker.patch("bfabric_scripts.cli.interactive.select_choice", return_value="PROD")
        assert resolve_choice(None, ["PROD", "TEST"], message="Pick", default="PROD") == "PROD"
        select.assert_called_once_with("Pick", ["PROD", "TEST"], default="PROD", describe=None, search=False)

    def test_allow_new_uses_select_or_input(self, mocker):
        mocker.patch("bfabric_scripts.cli.interactive.is_interactive", return_value=True)
        prompt = mocker.patch("bfabric_scripts.cli.interactive.select_or_input", return_value="NEW")
        assert resolve_choice(None, ["PROD"], message="Pick", allow_new=True) == "NEW"
        prompt.assert_called_once_with("Pick", ["PROD"], default=None)


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

    def test_returns_typed_value(self, mocker):
        question = mocker.MagicMock()
        question.ask.return_value = "NEW"
        autocomplete = mocker.patch("bfabric_scripts.cli.interactive.questionary.autocomplete", return_value=question)
        assert select_or_input("Pick", ["PROD"], default="X") == "NEW"
        autocomplete.assert_called_once_with("Pick", choices=["PROD"], default="X")
