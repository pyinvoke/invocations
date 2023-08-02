from contextlib import contextmanager

from invoke import MockContext
from invocations.pytest import test as _test_task, coverage
from unittest.mock import Mock, call


@contextmanager
def _expect(flags=None, extra_flags=None, kwargs=None):
    if kwargs is None:
        kwargs = dict(pty=True)
    flags = flags or "--verbose --color=yes --capture=sys"
    if extra_flags is not None:
        flags = flags + " " + extra_flags
    c = MockContext(run=True)
    yield c
    c.run.assert_called_once_with("pytest {}".format(flags), **kwargs)


class test_:
    def defaults_to_verbose_color_and_syscapture_with_pty_True(self):
        # Relies on default flags within expect helper
        with _expect() as c:
            _test_task(c)

    def can_turn_off_or_change_defaults(self):
        with _expect(flags="--capture=no", kwargs=dict(pty=False)) as c:
            _test_task(c, verbose=False, color=False, pty=False, capture="no")

    def can_passthru_k_x_and_arbitrary_opts(self):
        with _expect(extra_flags="--whatever -man -k 'lmao' -x") as c:
            _test_task(c, k="lmao", x=True, opts="--whatever -man")

    def can_disable_warnings(self):
        with _expect(extra_flags="--disable-warnings") as c:
            _test_task(c, warnings=False)


class coverage_:
    _FLAGS = "--cov --no-cov-on-fail --cov-report={}"

    def default_args(self):
        with _expect(extra_flags=self._FLAGS.format("term")) as c:
            coverage(c)

    def report_type(self):
        with _expect(extra_flags=self._FLAGS.format("xml")) as c:
            coverage(c, report="xml")

    def opts(self):
        with _expect(extra_flags=self._FLAGS.format("term") + " --meh") as c:
            coverage(c, opts="--meh")

    def test_function(self):
        c = MockContext()
        faketest = Mock()
        coverage(c, tester=faketest)
        faketest.assert_called_once_with(c, opts=self._FLAGS.format("term"))

    def can_append_additional_test_tasks(self):
        c = MockContext(run=True, repeat=True)
        faketest1, faketest2 = Mock(), Mock()
        coverage(c, additional_testers=[faketest1, faketest2])
        # Uses coverage-appending arg to pytest-cov
        flags = self._FLAGS.format("term") + " --cov-append"
        faketest1.assert_called_once_with(c, opts=flags)
        faketest2.assert_called_once_with(c, opts=flags)

    def open_html_report(self):
        c = MockContext(run=True, repeat=True)
        coverage(c, report="html")
        print(c.run.mock_calls)
        c.run.assert_any_call("open htmlcov/index.html")

    class codecov_support:
        def defaults_False(self):
            c = MockContext(run=True, repeat=True)
            coverage(c)
            assert call("codecov") not in c.run.mock_calls

        def runs_xml_and_codecov_when_True(self):
            c = MockContext(run=True, repeat=True)
            coverage(c, codecov=True)
            c.run.assert_has_calls([call("coverage xml"), call("codecov")])
