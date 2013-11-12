from invoke import ctask as task


@task(help={
    'module': "Just runs tests/STRING.py.",
    'runner': "Use STRING to run tests instead of 'spec'.",
    'opts': "Extra flags for the test runner",
})
def test(ctx, module=None, runner='spec', opts=None):
    """
    Run a Spec or Nose-powered internal test suite.
    """
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
    if opts:
        args += " " + opts
    # Use pty so the spec/nose/Python process buffers "correctly"
    ctx.run(runner + args, pty=True)
