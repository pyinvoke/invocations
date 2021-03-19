from pytest import fixture
from invoke import MockContext


@fixture
def ctx():
    # TODO: this would be a nice convenience in MockContext itself, though most
    # uses of it really just want responses-style "assert if expected calls did
    # not happen" behavior
    MockContext.run_command = property(lambda self: self.run.call_args[0][0])
    return MockContext(run=True)


# For use in packaging.release.publish tests
@fixture
def fakepub(mocker):
    rmtree = mocker.patch("invocations.util.rmtree")
    upload = mocker.patch("invocations.packaging.release.upload")
    build = mocker.patch("invocations.packaging.release.build")
    mkdtemp = mocker.patch("invocations.util.mkdtemp")
    mkdtemp.return_value = "tmpdir"
    c = MockContext(run=True)
    yield c, mkdtemp, build, upload, rmtree
