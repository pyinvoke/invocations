import sys
import time
from collections import defaultdict
from invoke.vendor.six import iteritems
from invoke.vendor.six.moves import range

from invoke import task
from tqdm import tqdm

from .watch import watch


@task(
    help={
        "module": "Just runs tests/STRING.py.",
        "runner": "Use STRING to run tests instead of 'spec'.",
        "opts": "Extra flags for the test runner",
        "pty": "Whether to run tests under a pseudo-tty",
    }
)
def test(c, module=None, runner=None, opts=None, pty=True):
    """
    Run a Spec or Nose-powered internal test suite.
    """
    runner = runner or "spec"
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = specific_module if module else ""
    if opts:
        args += " " + opts
    # Always enable timing info by default. OPINIONATED
    args += " --with-timing"
    # Allow client to configure some other Nose-related things.
    logformat = c.config.get("tests", {}).get("logformat", None)
    if logformat is not None:
        args += " --logging-format='{}'".format(logformat)
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
        override += "{}.py".format(module)
    opts += override
    test(c, runner=runner, opts=opts, pty=pty)


@task
def watch_tests(c, module=None, opts=None):
    """
    Watch source tree and test tree for changes, rerunning tests as necessary.

    Honors ``tests.package`` setting re: which source directory to watch for
    changes.
    """
    package = c.config.get("tests", {}).get("package")
    patterns = [r"\./tests/"]
    if package:
        patterns.append(r"\./{}/".format(package))
    kwargs = {"module": module, "opts": opts}
    # Kick things off with an initial test (making sure it doesn't exit on its
    # own if tests currently fail)
    c.config.run.warn = True
    test(c, **kwargs)
    # Then watch
    watch(c, test, patterns, [r".*/\..*\.swp"], **kwargs)


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


# TODO: rename to like find_errors or something more generic
@task
def count_errors(c, command, trials=10, verbose=False, fail_fast=False):
    """
    Run ``command`` multiple times and tally statistics about failures.

    Use Ctrl-C or other SIGINT to abort early (also see ``fail_fast``.)

    :param str command:
        The command to execute. Make sure to escape special shell characters!

    :param int trials:
        Number of trials to execute (default 10.)

    :param bool verbose:
        Whether to emit stdout/err from failed runs at end of execution.
        Default: ``False``.

    :param bool fail_fast:
        Whether to exit after the first error (i.e. "count runs til error is
        exhibited" mode.) Default: ``False``.

    Say ``verbose=True`` to see stderr from failed runs at the end.

    Say ``--fail-fast`` to error out, with error output, on the first error.
    """
    # TODO: allow defining failure as something besides "exited 1", e.g.
    # "stdout contained <sentinel>" or whatnot
    goods, bads = [], []
    prev_error = time.time()
    for num_runs in tqdm(range(trials), unit="trial"):
        result = c.run(command, hide=True, warn=True)
        if result.failed:
            now = time.time()
            result.since_prev_error = int(now - prev_error)
            prev_error = now
            bads.append(result)
            # -2 is typically indicative of SIGINT in most shells
            if fail_fast or result.exited == -2:
                break
        else:
            goods.append(result)
    num_runs += 1  # for count starting at 1, not 0
    if verbose or fail_fast:
        # TODO: would be nice to show interwoven stdout/err but I don't believe
        # we track that at present...
        for result in bads:
            print("")
            print(result.stdout)
            print(result.stderr)
    # Stats! TODO: errors only jeez
    successes = len(goods)
    failures = len(bads)
    overall = "{}/{} trials failed".format(failures, num_runs)
    # Short-circuit if no errors
    if not bads:
        print(overall)
        return
    periods = [x.since_prev_error for x in bads]
    # Period mean
    mean = int(sum(periods) / float(len(periods)))
    # Period mode
    # TODO: use collections.Counter now that we've dropped 2.6
    counts = defaultdict(int)
    for period in periods:
        counts[period] += 1
    mode = sorted((value, key) for key, value in iteritems(counts))[-1][1]
    # Emission of stats!
    if fail_fast:
        print("First failure occurred after {} successes".format(successes))
    else:
        print(overall)
    print(
        "Stats: min={}s, mean={}s, mode={}s, max={}s".format(
            min(periods), mean, mode, max(periods)
        )
    )
