import sys

from invoke import ctask as task

from .watch import watch


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
    # Allow client to configure some other Nose-related things.
    logformat = c.config.get('tests', {}).get('logformat', None)
    if logformat is not None:
        args += " --logging-format='{0}'".format(logformat)
    # Use pty by default so the spec/nose/Python process buffers "correctly"
    c.run(runner + args, pty=pty)


@task(help=test.help)
def integration(c, module=None, runner=None, opts=None, pty=True):
    """
    Run the integration test suite. May be slow!
    """
    opts = opts or ""
    opts += " --tests=integration/"
    test(c, module, runner, opts, pty)


@task
def watch_tests(c, module=None):
    """
    Watch source tree and test tree for changes, rerunning tests as necessary.

    Honors ``tests.package`` setting re: which source directory to watch for
    changes.
    """
    package = c.config.get('tests', {}).get('package')
    patterns = ['\./tests/']
    if package:
        patterns.append('\./{0}/'.format(package))
    watch(
        c, test, patterns, ['.*/\..*\.swp'], module=module
    )


@task
def coverage(c, package=None):
    """
    Run tests w/ coverage enabled, generating HTML, & opening it.

    Honors the ``tests.package`` config path, which supplies a default value
    for the ``package`` kwarg if given.
    """
    if not c.run("which coverage", hide=True, warn=True).ok:
        sys.exit("You need to 'pip install coverage' to use this task!")
    opts = ""
    package = c.config.get('tests', {}).get('package', package)
    if package is not None:
        # TODO: make omission list more configurable
        opts = "--include='{0}/*' --omit='{0}/vendor/*'".format(package)
    test(c, opts="--with-coverage --cover-branches")
    c.run("coverage html {0}".format(opts))
    c.run("open htmlcov/index.html")
