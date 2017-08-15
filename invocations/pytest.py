"""
Pytest-using variant of testing.py. Will eventually replace the latter.
"""

from invoke import task


@task
def test(c, verbose=True, color=True, capture='sys', opts=''):
    """
    Run pytest with given options.

    :param bool verbose:
        Whether to run tests in verbose mode.

    :param bool color:
        Whether to request colorized output (typically only works when
        ``verbose=True``.)

    :param str capture:
        What type of stdout/err capturing pytest should use. Defaults to
        ``sys`` since pytest's own default, ``fd``, tends to trip up
        subprocesses trying to detect PTY status. Can be set to ``no`` for no
        capturing / useful print-debugging / etc.

    :param str opts:
        Extra runtime options to hand to ``pytest``.
    """
    # TODO: really need better tooling around these patterns
    # TODO: especially the problem of wanting to be configurable, but
    # sometimes wanting to override one's config via kwargs; and also needing
    # non-None defaults in the kwargs to inform the parser (or have to
    # configure it explicitly...?)
    flags = []
    if verbose:
        flags.append('--verbose')
    if color:
        flags.append('--color=yes')
    flags.append('--capture={0}'.format(capture))
    if opts is not None:
        flags.append(opts)
    c.run("pytest {0}".format(" ".join(flags)), pty=True)


@task(help=test.help)
def integration(c, opts=None, pty=True):
    """
    Run the integration test suite. May be slow!
    """
    opts = opts or ""
    override = " --tests=integration/"
    opts += override
    test(c, opts=opts, pty=pty)


@task
def coverage(c, report='term', opts=''):
    """
    Run pytest with coverage enabled.

    Assumes the ``pytest-cov`` pytest plugin is installed.

    :param str report:
        Coverage report style to use. If 'html', will also open in browser.

    :param str opts:
        Extra runtime opts to pass to pytest.
    """
    opts += "--cov --no-cov-on-fail --cov-report={0}".format(report)
    test(c, opts=opts)
    if report is 'html':
        c.run("open htmlcov/index.html")
