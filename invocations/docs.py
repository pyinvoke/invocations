import os

from invoke import ctask as task, Collection


# Underscored func name to avoid shadowing kwargs in build()
@task(name='clean')
def _clean(ctx):
    ctx.run("rm -rf {0}".format(ctx['sphinx.target']))


# Ditto
@task(name='browse')
def _browse(ctx):
    index = os.path.join(ctx['sphinx.target'], 'index.html')
    ctx.run("open {0}".format(index))


@task(default=True)
def build(ctx, clean=False, browse=False):
    if clean:
        _clean(ctx)
    cmd = "sphinx-build {0} {1}".format(
        ctx['sphinx.source'], ctx['sphinx.target']
    )
    ctx.run(cmd, pty=True)
    if browse:
        _browse(ctx)

ns = Collection(_clean, _browse, build)
ns.configure({
    'sphinx.source': 'docs',
    # TODO: allow lazy eval so one attr can refer to another?
    'sphinx.target': os.path.join('docs', '_build'),
})
