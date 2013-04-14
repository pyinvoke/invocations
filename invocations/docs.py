import os

from invoke import ctask as task, run, Collection


docs_dir = 'docs'
build_dir = os.path.join(docs_dir, '_build')


@task(aliases=['c'])
def _clean(ctx):
    ctx.run("rm -rf %s" % build_dir)


@task(aliases=['b'])
def _browse(ctx):
    ctx.run("open %s" % os.path.join(build_dir, 'index.html'))


@task(default=True)
def build(ctx, clean=False, browse=False):
    if clean:
        _clean(ctx)
    ctx.run("sphinx-build %s %s" % (docs_dir, build_dir), pty=True)
    if browse:
        _browse(ctx)

ns = Collection(clean=_clean, browse=_browse, build=build)
