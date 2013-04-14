from invoke import ctask as task, run


@task
def test(ctx, module=None, runner='spec'):
    """
    Run a Spec or Nose-powered internal test suite.

    Say ``--module=foo``/``-m foo`` to just run ``tests/foo.py``.

    Defaults to running the ``spec`` tool; may override by saying e.g.
    ``runner='nosetests'``.
    """
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
    # Use pty so the spec/nose/Python process buffers "correctly"
    ctx.run(runner + args, pty=True)
