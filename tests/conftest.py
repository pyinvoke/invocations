from mock import Mock
from pytest import fixture

from invoke import MockContext, Result


# TODO: figure out how to distribute it in a way not requiring non-testing
# users to have mock installed?!
@fixture
def ctx():
    # TODO: make MockContext more usable in a "don't care about results" mode
    # NOTE: this is ugly but whatever.
    MockContext.run_command = property(lambda self: self.run.call_args[0][0])
    mc = MockContext(run=Result())
    mc._set(run=Mock(wraps=mc.run))
    yield mc
