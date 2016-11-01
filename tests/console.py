from __future__ import unicode_literals

import sys

from mock import patch
from spec import Spec, eq_, ok_, trap, assert_contains

from invocations.console import confirm


class confirm_(Spec):
    @patch('invocations.console.input', return_value='yes')
    def displays_question_with_yes_no_suffix(self, mock_input):
        confirm("Are you sure?")
        eq_(mock_input.call_args[0][0], "Are you sure? [Y/n] ")

    @patch('invocations.console.input')
    def returns_True_for_yeslike_responses(self, mock_input):
        for value in ('y', 'Y', 'yes', 'YES', 'yES', 'Yes'):
            mock_input.return_value = value
            ok_(confirm("Meh") is True)

    @patch('invocations.console.input')
    def returns_False_for_nolike_responses(self, mock_input):
        for value in ('n', 'N', 'no', 'NO', 'nO', 'No'):
            mock_input.return_value = value
            ok_(confirm("Meh") is False)

    @trap
    @patch('invocations.console.input', side_effect=['wat', 'y'])
    def reprompts_on_bad_input(self, mock_input):
        ok_(confirm("O rly?") is True)
        assert_contains(sys.stderr.getvalue(), "I didn't understand you")

    @patch('invocations.console.input', return_value='y')
    def suffix_changes_when_affirmative_False(self, mock_input):
        confirm("Are you sure?", affirmative=False)
        eq_(mock_input.call_args[0][0], "Are you sure? [y/N] ")

    @patch('invocations.console.input', return_value='')
    def default_on_empty_response_is_True_by_default(self, mock_input):
        ok_(confirm("Are you sure?") is True)

    @patch('invocations.console.input', return_value='')
    def default_on_empty_response_is_False_if_affirmative_False(
        self, mock_input
    ):
        ok_(confirm("Are you sure?", affirmative=False) is False)

    @patch('invocations.console.input', return_value=' y ')
    def whitespace_is_trimmed(self, mock_input):
        ok_(confirm("Are you sure?") is True)
