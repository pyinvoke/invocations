from invoke import ctask as task


@task(help={
    'module': "Just runs tests/STRING.py.",
    'runner': "Use STRING to run tests instead of 'spec'."
})
def test(ctx, module=None, runner='spec'):
    """
    Run a Spec or Nose-powered internal test suite.
    """
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
    # Use pty so the spec/nose/Python process buffers "correctly"
    ctx.run(runner + args, pty=True)
