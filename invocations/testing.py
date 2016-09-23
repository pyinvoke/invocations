import sys

from invoke import task

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
    override = " --tests=integration/"
    if module:
        override += "{0}.py".format(module)
    opts += override
    test(c, runner=runner, opts=opts, pty=pty)


@task
def watch_tests(c, module=None, opts=None):
    """
    Watch source tree and test tree for changes, rerunning tests as necessary.

    Honors ``tests.package`` setting re: which source directory to watch for
    changes.
    """
    package = c.config.get('tests', {}).get('package')
    patterns = ['\./tests/']
    if package:
        patterns.append('\./{0}/'.format(package))
    kwargs = {'module': module, 'opts': opts}
    # Kick things off with an initial test (making sure it doesn't exit on its
    # own if tests currently fail)
    c.config.run.warn = True
    test(c, **kwargs)
    # Then watch
    watch(c, test, patterns, ['.*/\..*\.swp'], **kwargs)


@task
def coverage(c, html=True, integration_=True):
    """
    Run tests w/ coverage enabled, optionally generating HTML & opening it.

    :param bool html:
        Whether to generate & open an HTML report. Default: ``True``.

    :param bool integration_:
        Whether to run integration test suite (``integration/``) in addition to
        unit test suite (``tests/``). Default: ``True``.
    """
    if not c.run("which coverage", hide=True, warn=True).ok:
        sys.exit("You need to 'pip install coverage' to use this task!")
    # Generate actual coverage data. NOTE: this will honor a local .coveragerc
    test_opts = "--with-coverage"
    test(c, opts=test_opts)
    # Coverage naturally accumulates unless --cover-erase is used - so the
    # resulting .coverage file parsed by 'coverage html' will contain the union
    # of both suites, if integration suite is run too.
    if integration_:
        integration(c, opts=test_opts)
    if html:
        c.run("coverage html && open htmlcov/index.html")
