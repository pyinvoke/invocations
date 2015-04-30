from os.path import join
import sys

from invoke import ctask as task, Collection


# Underscored func name to avoid shadowing kwargs in build()
@task(name='clean')
def _clean(c):
    """
    Nuke docs build target directory so next build is clean.
    """
    c.run("rm -rf {0}".format(c.sphinx.target))


# Ditto
@task(name='browse')
def _browse(c):
    """
    Open build target's index.html in a browser (using 'open').
    """
    index = join(c.sphinx.target, c.sphinx.target_file)
    c.run("open {0}".format(index))


@task(default=True, help={
    'opts': "Extra sphinx-build options/args",
    'clean': "Remove build tree before building",
    'browse': "Open docs index in browser after building",
    'warn': "Build with stricter warnings/errors enabled",
})
def build(c, clean=False, browse=False, warn=False, opts=None):
    """
    Build the project's Sphinx docs.
    """
    if clean:
        _clean(c)
    if opts is None:
        opts = ""
    if warn:
        opts += " -n -W"
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


# Vanilla/default/parameterized collection for normal use
ns = Collection(_clean, _browse, build, tree)
ns.configure({
    'sphinx': {
        'source': 'docs',
        # TODO: allow lazy eval so one attr can refer to another?
        'target': join('docs', '_build'),
        'target_file': 'index.html',
    }
})


# Multi-site variants, used by various projects (fabric, invoke, paramiko)
# Expects a tree like sites/www/<sphinx> + sites/docs/<sphinx>,
# and that you want 'inline' html build dirs, e.g. sites/www/_build/index.html.

def _site(name, build_help):
    _path = join('sites', name)
    # TODO: turn part of from_module into .clone(), heh.
    self = sys.modules[__name__]
    coll = Collection.from_module(self, name=name, config={
        'sphinx': {
            'source': _path,
            'target': join(_path, '_build')
        }
    })
    coll['build'].__doc__ = build_help
    return coll


# Usage doc/API site (published as e.g. docs.myproject.org)
docs = _site('docs', "Build the API docs subsite.")
# Main/about/changelog site (e.g. (www.)?myproject.org)
www = _site('www', "Build the main project website.")
