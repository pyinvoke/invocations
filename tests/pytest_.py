from contextlib import contextmanager

from invoke import MockContext

from invocations.pytest import test


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
