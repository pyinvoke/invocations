from os.path import join, isdir
from tempfile import mkdtemp
from shutil import rmtree
import sys

from invoke import task, Collection, Context

from .watch import make_handler, observe


# Underscored func name to avoid shadowing kwargs in build()
@task(name='clean')
def _clean(c):
    """
    Nuke docs build target directory so next build is clean.
    """
    if isdir(c.sphinx.target):
        rmtree(c.sphinx.target)


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
    'source': "Source directory; overrides config setting",
    'target': "Output directory; overrides config setting",
})
def build(c,
    clean=False,
    browse=False,
    warn=False,
    opts=None,
    source=None,
    target=None,
):
    """
    Build the project's Sphinx docs.
    """
    if clean:
        _clean(c)
    if opts is None:
        opts = ""
    if warn:
        opts += " -n -W"
    cmd = "sphinx-build{0} {1} {2}".format(
        (" " + opts) if opts else "",
        source or c.sphinx.source,
        target or c.sphinx.target,
    )
    c.run(cmd, pty=True)
    if browse:
        _browse(c)


@task
def doctest(c):
    """
    Run Sphinx' doctest builder.

    This will act like a test run, displaying test results & exiting nonzero if
    all tests did not pass.

    A temporary directory is used for the build target, as the only output is
    the text file which is automatically printed.
    """
    tmpdir = mkdtemp()
    try:
        opts = "-b doctest"
        target = tmpdir
        build(c, clean=True, target=target, opts=opts)
    finally:
        rmtree(tmpdir)


@task
def tree(c):
    ignore = ".git|*.pyc|*.swp|dist|*.egg-info|_static|_build|_templates"
    c.run("tree -Ca -I \"{0}\" {1}".format(ignore, c.sphinx.source))


# Vanilla/default/parameterized collection for normal use
ns = Collection(_clean, _browse, build, tree, doctest)
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


@task
def sites(c):
    """
    Build both doc sites w/ maxed nitpicking.
    """
    # Turn warnings into errors, emit warnings about missing references.
    # This gives us a maximally noisy docs build.
    # Also enable tracebacks for easier debuggage.
    opts = "-W -n -T"
    # This is super lolzy but we haven't actually tackled nontrivial in-Python
    # task calling yet, so...
    docs_c = Context(config=c.config.clone())
    www_c = Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    www_c.update(**www.configuration())
    docs['build'](docs_c, opts=opts)
    www['build'](www_c, opts=opts)


@task
def watch_docs(c):
    """
    Watch both doc trees & rebuild them if files change.

    This includes e.g. rebuilding the API docs if the source code changes;
    rebuilding the WWW docs if the README changes; etc.
    """
    # TODO: break back down into generic single-site version, then create split
    # tasks as with docs/www above. Probably wants invoke#63.

    # NOTE: 'www'/'docs' refer to the module level sub-collections. meh.

    # Readme & WWW triggers WWW
    www_c = Context(config=c.config.clone())
    www_c.update(**www.configuration())
    www_handler = make_handler(
        ctx=www_c,
        task_=www['build'],
        regexes=['\./README.rst', '\./sites/www'],
        ignore_regexes=['.*/\..*\.swp', '\./sites/www/_build'],
    )

    # Code and docs trigger API
    docs_c = Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    api_handler = make_handler(
        ctx=docs_c,
        task_=docs['build'],
        regexes=['\./invoke/', '\./sites/docs'],
        ignore_regexes=['.*/\..*\.swp', '\./sites/docs/_build'],
    )

    observe(www_handler, api_handler)
