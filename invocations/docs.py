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
def api_docs(target, output="api", exclude=""):
    """
    Runs ``sphinx-apidoc`` to autogenerate your API docs.

    Must give target directory/package as ``target``. Results are written out
    to ``docs/<output>`` (``docs/api`` by default).

    To exclude certain output files from the final build give ``exclude`` as a
    comma separated list of file paths.
    """
    output = os.path.join('docs', output)
    # Have to make these absolute or apidoc is dumb :(
    exclude = map(
        lambda x: os.path.abspath(os.path.join(os.getcwd(), x)),
        exclude.split(',')
    )
    run("sphinx-apidoc -f -o %s %s %s" % (output, target, ' '.join(exclude)))


@task
def docs(clean=False, browse=False):
    """
    Build Sphinx docs, optionally ``clean``ing and/or ``browse``ing.
    """
    if clean:
        clean_docs.body()
    run("sphinx-build %s %s" % (docs_dir, build), pty=True)
    if browse:
        browse_docs.body()
