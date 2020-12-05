"""
Tasks for managing Sphinx documentation trees.
"""

from os.path import join, isdir
from tempfile import mkdtemp
from shutil import rmtree
import sys

from invoke import task, Collection, Context

from .watch import make_handler, observe


# Underscored func name to avoid shadowing kwargs in build()
@task(name="clean")
def _clean(c):
    """
    Nuke docs build target directory so next build is clean.
    """
    if isdir(c.sphinx.target):
        rmtree(c.sphinx.target)


# Ditto
@task(name="browse")
def _browse(c):
    """
    Open build target's index.html in a browser (using 'open').
    """
    index = join(c.sphinx.target, c.sphinx.target_file)
    c.run("open {}".format(index))


@task(
    default=True,
    help={
        "opts": "Extra sphinx-build options/args",
        "clean": "Remove build tree before building",
        "browse": "Open docs index in browser after building",
        "nitpick": "Build with stricter warnings/errors enabled",
        "source": "Source directory; overrides config setting",
        "target": "Output directory; overrides config setting",
    },
)
def build(
    c,
    clean=False,
    browse=False,
    nitpick=False,
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
    if nitpick:
        opts += " -n -W -T"
    cmd = "sphinx-build{} {} {}".format(
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
    """
    Display documentation contents with the 'tree' program.
    """
    ignore = ".git|*.pyc|*.swp|dist|*.egg-info|_static|_build|_templates"
    c.run('tree -Ca -I "{}" {}'.format(ignore, c.sphinx.source))


# Vanilla/default/parameterized collection for normal use
ns = Collection(_clean, _browse, build, tree, doctest)
ns.configure(
    {
        "sphinx": {
            "source": "docs",
            # TODO: allow lazy eval so one attr can refer to another?
            "target": join("docs", "_build"),
            "target_file": "index.html",
        }
    }
)


# Multi-site variants, used by various projects (fabric, invoke, paramiko)
# Expects a tree like sites/www/<sphinx> + sites/docs/<sphinx>,
# and that you want 'inline' html build dirs, e.g. sites/www/_build/index.html.


def _site(name, help_part):
    _path = join("sites", name)
    # TODO: turn part of from_module into .clone(), heh.
    self = sys.modules[__name__]
    coll = Collection.from_module(
        self,
        name=name,
        config={"sphinx": {"source": _path, "target": join(_path, "_build")}},
    )
    coll.__doc__ = "Tasks for building {}".format(help_part)
    coll["build"].__doc__ = "Build {}".format(help_part)
    return coll


# Usage doc/API site (published as e.g. docs.myproject.org)
docs = _site("docs", "the API docs subsite.")
# Main/about/changelog site (e.g. (www.)?myproject.org)
www = _site("www", "the main project website.")


@task
def sites(c):
    """
    Build both doc sites w/ maxed nitpicking.
    """
    # TODO: This is super lolzy but we haven't actually tackled nontrivial
    # in-Python task calling yet, so we do this to get a copy of 'our' context,
    # which has been updated with the per-collection config data of the
    # docs/www subcollections.
    docs_c = Context(config=c.config.clone())
    www_c = Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    www_c.update(**www.configuration())
    # Must build both normally first to ensure good intersphinx inventory files
    # exist =/ circular dependencies ahoy! Do it quietly to avoid pulluting
    # output; only super-serious errors will bubble up.
    # TODO: wants a 'temporarily tweak context settings' contextmanager
    # TODO: also a fucking spinner cuz this confuses me every time I run it
    # when the docs aren't already prebuilt
    # TODO: this is still bad because it means the actually displayed build
    # output "looks like" nothing was built (due to that first pass building
    # most pages)
    docs_c["run"].hide = True
    www_c["run"].hide = True
    docs["build"](docs_c)
    www["build"](www_c)
    docs_c["run"].hide = False
    www_c["run"].hide = False
    # Run the actual builds, with nitpick=True (nitpicks + tracebacks)
    docs["build"](docs_c, nitpick=True)
    www["build"](www_c, nitpick=True)


@task
def watch_docs(c):
    """
    Watch both doc trees & rebuild them if files change.

    This includes e.g. rebuilding the API docs if the source code changes;
    rebuilding the WWW docs if the README changes; etc.

    Reuses the configuration values ``packaging.package`` or ``tests.package``
    (the former winning over the latter if both defined) when determining which
    source directory to scan for API doc updates.
    """
    # TODO: break back down into generic single-site version, then create split
    # tasks as with docs/www above. Probably wants invoke#63.

    # NOTE: 'www'/'docs' refer to the module level sub-collections. meh.

    # Readme & WWW triggers WWW
    www_c = Context(config=c.config.clone())
    www_c.update(**www.configuration())
    www_handler = make_handler(
        ctx=www_c,
        task_=www["build"],
        regexes=[r"\./README.rst", r"\./sites/www"],
        ignore_regexes=[r".*/\..*\.swp", r"\./sites/www/_build"],
    )

    # Code and docs trigger API
    docs_c = Context(config=c.config.clone())
    docs_c.update(**docs.configuration())
    regexes = [r"\./sites/docs"]
    package = c.get("packaging", {}).get("package", None)
    if package is None:
        package = c.get("tests", {}).get("package", None)
    if package:
        regexes.append(r"\./{}/".format(package))
    api_handler = make_handler(
        ctx=docs_c,
        task_=docs["build"],
        regexes=regexes,
        ignore_regexes=[r".*/\..*\.swp", r"\./sites/docs/_build"],
    )

    observe(www_handler, api_handler)
