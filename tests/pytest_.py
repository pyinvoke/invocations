from contextlib import contextmanager

from invoke import MockContext
from invocations.pytest import test, coverage
from mock import Mock, call


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
            test(c)

    def can_turn_off_or_change_defaults(self):
        with _expect(flags="--capture=no", kwargs=dict(pty=False)) as c:
            test(c, verbose=False, color=False, pty=False, capture="no")

    def can_passthru_k_x_and_arbitrary_opts(self):
        with _expect(extra_flags="--whatever -man -k 'lmao' -x") as c:
            test(c, k="lmao", x=True, opts="--whatever -man")

    def can_disable_warnings(self):
        with _expect(extra_flags="--disable-warnings") as c:
            test(c, warnings=False)


class coverage_:
    FLAGS = "--cov --no-cov-on-fail --cov-report={}"

    def default_args(self):
        with _expect(extra_flags=self.FLAGS.format("term")) as c:
            coverage(c)

    def report_type(self):
        with _expect(extra_flags=self.FLAGS.format("xml")) as c:
            coverage(c, report="xml")

    def opts(self):
        with _expect(extra_flags=self.FLAGS.format("term") + " --meh") as c:
            coverage(c, opts="--meh")

    def test_function(self):
        c = MockContext()
        faketest = Mock()
        coverage(c, tester=faketest)
        faketest.assert_called_once_with(c, opts=self.FLAGS.format("term"))

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
