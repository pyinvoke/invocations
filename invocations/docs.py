import os

from invoke import task, run, Collection


docs_dir = 'docs'
build_dir = os.path.join(docs_dir, '_build')


@task
def _clean():
    run("rm -rf %s" % build_dir)


@task
def _browse():
    run("open %s" % os.path.join(build_dir, 'index.html'))


@task(default=True)
def build(clean=False, browse=False):
    if clean:
        _clean()
    run("sphinx-build %s %s" % (docs_dir, build_dir), pty=True)
    if browse:
        _browse()

ns = Collection(clean=_clean, browse=_browse, build=build)
