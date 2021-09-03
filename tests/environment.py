from mock import patch
from pytest import mark

from invocations.environment import in_ci


@mark.parametrize(
    "environ,expected",
    [
        (dict(), False),
        (dict(WHATEVS="true", SURE_WHYNOT=""), False),
        (dict(CIRCLECI=""), False),
        (dict(TRAVIS=""), False),
        (dict(CIRCLECI="", WHATEVS="yo"), False),
        (dict(CIRCLECI="", TRAVIS=""), False),
        (dict(CIRCLECI="true"), True),
        (dict(CIRCLECI="false"), True),  # yup
        (dict(CIRCLECI="no"), True),
        (dict(CIRCLECI="1"), True),
        (dict(CIRCLECI="0"), True),
        (dict(TRAVIS="true"), True),
        (dict(CIRCLECI="true", TRAVIS=""), True),
        (dict(CIRCLECI="", TRAVIS="true"), True),
        (dict(CIRCLECI="true", TRAVIS="true"), True),
        (dict(CIRCLECI="false", TRAVIS="no"), True),
        (dict(CIRCLECI="true", WHATEVS=""), True),
        (dict(CIRCLECI="true", WHATEVS="huh?"), True),
    ],
)
def in_ci_true_when_any_expected_vars_nonempty(environ, expected):
    with patch("invocations.environment.os.environ", environ):
        assert in_ci() is expected
