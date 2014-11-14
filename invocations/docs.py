import os

from invoke import ctask as task, Collection


# Underscored func name to avoid shadowing kwargs in build()
@task(name='clean')
def _clean(c):
    c.run("rm -rf {0}".format(c.sphinx.target))


# Ditto
@task(name='browse')
def _browse(c):
    index = os.path.join(c.sphinx.target, c.sphinx.target_file)
    c.run("open {0}".format(index))


@task(default=True, help={'opts': "Extra sphinx-build options/args"})
def build(c, clean=False, browse=False, opts=None):
    if clean:
        _clean(c)
    cmd = "sphinx-build{2} {0} {1}".format(
        c.sphinx.source,
        c.sphinx.target,
        (" " + opts) if opts else "",
    )
    c.run(cmd, pty=True)
    if browse:
        _browse(c)


@task
def tree(c):
    ignore = ".git|*.pyc|*.swp|dist|*.egg-info|_static|_build|_templates"
    c.run("tree -Ca -I \"{0}\" {1}".format(ignore, c.sphinx.source))


ns = Collection(_clean, _browse, build, tree)
ns.configure({
    'sphinx': {
        'source': 'docs',
        # TODO: allow lazy eval so one attr can refer to another?
        'target': os.path.join('docs', '_build'),
        'target_file': 'index.html',
    }
})
