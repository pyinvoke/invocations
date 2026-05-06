from pytest import fixture
from invoke import MockContext

# Set up icecream globally for convenience.
from icecream import install

install()


@fixture
def ctx():
    c = MockContext(run=True)
    # Patch the INSTANCE, not the CLASS
    type(c).run_command = property(lambda self: self.run.call_args[0][0])
    return c
