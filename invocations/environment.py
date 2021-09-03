"""
Helpers concerning the invoking shell environment.

For example, generalized "do we appear to be on CI?" tests, which may be used
in multiple other modules.
"""

import os


def in_ci():
    """
    Return ``True`` if we appear to be running inside a CI environment.

    Checks for CI system env vars such as ``CIRCLECI`` or ``TRAVIS`` -
    specifically whether they exist and are non-empty. The actual value is not
    currently relevant, as long as it's not the empty string.
    """
    for sentinel in ("CIRCLECI", "TRAVIS"):
        if os.environ.get(sentinel, False):
            return True
    return False
