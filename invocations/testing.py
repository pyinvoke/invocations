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
    # Use pty by default so the spec/nose/Python process buffers "correctly"
    c.run(runner + args, pty=pty)
