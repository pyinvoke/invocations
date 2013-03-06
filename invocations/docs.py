import os

from invoke.tasks import task
from invoke.runner import run


docs_dir = 'docs'
build = os.path.join(docs_dir, '_build')


@task
def clean():
    run("rm -rf %s" % build)


@task
def browse():
    run("open %s" % os.path.join(build, 'index.html'))


@task(default=True)
def build(clean=False, browse=False):
    if clean:
        clean()
    run("sphinx-build %s %s" % (docs_dir, build), pty=True)
    if browse:
        browse()
