import os

from invoke import ctask as task, Collection


@task(aliases=['c'])
def _clean(ctx):
    ctx.run("rm -rf {0}".format(ctx['sphinx.target']))


@task(aliases=['b'])
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

ns = Collection(clean=_clean, browse=_browse, build=build)
ns.configure({
    'sphinx.source': 'docs',
    # TODO: allow lazy eval so one attr can refer to another?
    'sphinx.target': os.path.join('docs', '_build'),
})
