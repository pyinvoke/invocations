from invoke import ctask as task


@task(help={
    'module': "Just runs tests/STRING.py.",
    'runner': "Use STRING to run tests instead of 'spec'.",
    'opts': "Extra flags for the test runner",
    'pty': "Whether to run tests under a pseudo-tty",
})
def test(c, module=None, runner=None, opts=None, pty=True):
    """
    Run a Spec or Nose-powered internal test suite.
    """
    runner = runner or 'spec'
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
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
    """
    opts = ""
    if package is not None:
        # TODO: make omission list more configurable
        opts = "--include='{0}/*' --omit='{0}/vendor/*'".format(package)
    test(c, opts="--with-coverage --cover-branches")
    c.run("coverage html {0}".format(opts))
    c.run("open htmlcov/index.html")
