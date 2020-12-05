"""
Text console UI helpers and patterns, e.g. 'Y/n' prompts and the like.
"""

from __future__ import unicode_literals, print_function

import sys

from invoke.vendor.six.moves import input


# NOTE: originally cribbed from fab 1's contrib.console.confirm
def confirm(question, assume_yes=True):
    """
    Ask user a yes/no question and return their response as a boolean.

    ``question`` should be a simple, grammatically complete question such as
    "Do you wish to continue?", and will have a string similar to ``" [Y/n] "``
    appended automatically. This function will *not* append a question mark for
    you.

    By default, when the user presses Enter without typing anything, "yes" is
    assumed. This can be changed by specifying ``assume_yes=False``.

    .. note::
        If the user does not supplies input that is (case-insensitively) equal
        to "y", "yes", "n" or "no", they will be re-prompted until they do.

    :param str question: The question part of the prompt.
    :param bool assume_yes:
        Whether to assume the affirmative answer by default. Default value:
        ``True``.

    :returns: A `bool`.
    """
    # Set up suffix
    if assume_yes:
        suffix = "Y/n"
    else:
        suffix = "y/N"
    # Loop till we get something we like
    # TODO: maybe don't do this? It can be annoying. Turn into 'q'-for-quit?
    while True:
        # TODO: ensure that this is Ctrl-C friendly, ISTR issues with
        # raw_input/input on some Python versions blocking KeyboardInterrupt.
        response = input("{} [{}] ".format(question, suffix))
        response = response.lower().strip()  # Normalize
        # Default
        if not response:
            return assume_yes
        # Yes
        if response in ["y", "yes"]:
            return True
        # No
        if response in ["n", "no"]:
            return False
        # Didn't get empty, yes or no, so complain and loop
        err = "I didn't understand you. Please specify '(y)es' or '(n)o'."
        print(err, file=sys.stderr)
