import os

from invoke.tasks import task
from invoke.runner import run


docs_dir = 'docs'
build = os.path.join(docs_dir, '_build')


@task
def clean_docs():
    run("rm -rf %s" % build)


@task
def browse_docs():
    run("open %s" % os.path.join(build, 'index.html'))


@task
def docs(clean=False, browse=False):
    if clean:
        clean_docs()
    run("sphinx-build %s %s" % (docs_dir, build), pty=True)
    if browse:
        browse_docs()
