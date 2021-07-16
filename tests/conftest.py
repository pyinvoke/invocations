from pytest import fixture
from invoke import MockContext


@fixture
def ctx():
    # TODO: this would be a nice convenience in MockContext itself, though most
    # uses of it really just want responses-style "assert if expected calls did
    # not happen" behavior
    MockContext.run_command = property(lambda self: self.run.call_args[0][0])
    return MockContext(run=True)


class Mocks:
    pass


# For use in packaging.release.publish tests
@fixture
def fakepub(mocker):
    mocks = Mocks()
    mocks.rmtree = mocker.patch("invocations.util.rmtree")
    mocks.twine_check = mocker.patch(
        "invocations.packaging.release.twine_check", return_value=False
    )
    mocks.upload = mocker.patch("invocations.packaging.release.upload")
    mocks.build = mocker.patch("invocations.packaging.release.build")
    mocks.test_install = mocker.patch(
        "invocations.packaging.release.test_install"
    )
    mocks.mkdtemp = mocker.patch("invocations.util.mkdtemp")
    mocks.mkdtemp.return_value = "tmpdir"
    c = MockContext(run=True)
    yield c, mocks
