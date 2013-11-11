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


@task(default=True, help={'opts': "Extra sphinx-build options/args"})
def build(ctx, clean=False, browse=False, opts=None):
    if clean:
        _clean(ctx)
    cmd = "sphinx-build{2} {0} {1}".format(
        ctx['sphinx.source'],
        ctx['sphinx.target'],
        (" " + opts) if opts else "",
    )
    ctx.run(cmd, pty=True)
    if browse:
        _browse(ctx)


@task
def tree(ctx):
    ignore = ".git|*.pyc|*.swp|dist|*.egg-info|_static|_build"
    ctx.run("tree -Ca -I \"{0}\" docs".format(ignore))


ns = Collection(_clean, _browse, build, tree)
ns.configure({
    'sphinx.source': 'docs',
    # TODO: allow lazy eval so one attr can refer to another?
    'sphinx.target': os.path.join('docs', '_build'),
})
