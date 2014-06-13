import sys
import os.path

from invoke import ctask as task


@task(help={
    'module': "Just runs tests/STRING.py.",
    'runner': "Use STRING to run tests instead of 'spec'.",
    'opts': "Extra flags for the test runner",
    'pty': "Whether to run tests under a pseudo-tty",
    'coverage': "Report coverage information",
})
def test(c, module=None, runner=None, opts=None, pty=True, coverage=True):
    """
    Run a Spec or Nose-powered internal test suite.
    """
    runner = runner or 'spec'
    args = ""
    if coverage:
        full_path = ctx.run("which %s" % runner, hide=True)
        if module:
            cover_opts = "--source=%s" % module
        else:
            cover_opts = ""
        runner = "coverage run {opts} {runner}".format(
            opts=cover_opts, runner=full_path.stdout.strip()
        )
    # Allow selecting specific submodule
    if module:
        test_module = "tests/%s.py" % module
        if os.path.isfile(test_module):
            args += " --tests=%s" % test_module
    if opts:
        args += " " + opts
    # Always enable timing info by default. OPINIONATED
    args += " --with-timing"
    # Use pty by default so the spec/nose/Python process buffers "correctly"
    c.run(runner + args, pty=pty)


@task
def coverage(c, package=None):
    """
    Run tests w/ coverage enabled, generating HTML, & opening it.

    Honors the 'coverage.package' config path, which supplies a default value
    for the ``package`` kwarg if given.
    """
    if not c.run("which coverage", hide=True, warn=True).ok:
        sys.exit("You need to 'pip install coverage' to use this task!")
    opts = ""
    package = c.config.get('coverage', {}).get('package', package)
    if package is not None:
        # TODO: make omission list more configurable
        opts = "--include='{0}/*' --omit='{0}/vendor/*'".format(package)
    test(c, opts="--with-coverage --cover-branches")
    c.run("coverage html {0}".format(opts))
    c.run("open htmlcov/index.html")
