from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, call

from pytest import fixture
from invoke import MockContext

# Set up icecream globally for convenience.
from icecream import install

install()


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


# For use in packaging.release.test_install tests
@fixture
def install():
    with patch("invocations.packaging.release.pip_version", "lmao"), patch(
        "invocations.util.rmtree", Mock("rmtree")
    ), patch(
        "invocations.packaging.release._find_package", lambda c: "foo"
    ), patch(
        "venv.EnvBuilder"
    ) as builder, patch(
        "invocations.util.mkdtemp"
    ) as mkdtemp, patch(
        "invocations.packaging.release.get_archives"
    ) as get_archives, patch(
        "invocations.packaging.release.Path"
    ) as fakePath:
        # Setup & run
        c = MockContext(run=True, repeat=True)
        mkdtemp.return_value = "tmpdir"
        get_archives.return_value = ["foo.tgz", "foo.whl"]

        # I hate this but don't see a cleaner way to mock out a nested
        # 'exists()' w/o breaking everything else, or using a real tmpdir.
        def set_exists(value):
            def fakediv(self, arg):
                root = Path(mkdtemp.return_value)
                bindir = root / "bin"
                if arg == "bin":
                    return bindir
                elif arg == "pip":
                    return bindir / "pip"
                elif arg == "python":
                    return bindir / "python"
                elif arg == "py.typed":
                    path = Path("foo") / "py.typed"
                    ret = MagicMock(wraps=path)
                    ret.exists.return_value = value
                    return ret

            fakePath.return_value.__truediv__ = fakediv

        c.set_exists = set_exists  # so caller can run it
        c.set_exists(False)  # default
        yield c
        # Create factory
        builder.assert_called_once_with(with_pip=True)
        # Used helper to get artifacts
        get_archives.assert_called_once_with("whatever")
        # venv factory ran twice in some temp dir
        builder.return_value.create.assert_has_calls(
            [call("tmpdir"), call("tmpdir")]
        )
        pip_base = "tmpdir/bin/pip install --disable-pip-version-check"
        for wanted in (
            # Pip installed to same version as running interpreter's pip
            call("tmpdir/bin/pip install pip==lmao"),
            # Archives installed into venv
            call("{} foo.tgz".format(pip_base)),
            call("{} foo.whl".format(pip_base)),
        ):
            assert wanted in c.run.mock_calls
