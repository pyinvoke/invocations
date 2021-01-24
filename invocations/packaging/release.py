"""
Python package release tasks.

This module assumes:

- you're using semantic versioning for your releases
- you maintain a file called ``$package/_version.py`` containing normal version
  conventions (``__version_info__`` tuple and ``__version__`` string).
"""

from __future__ import unicode_literals, print_function

import getpass
import itertools
import logging
import os
import re
import sys
from glob import glob
from shutil import rmtree

from invoke.vendor.six import StringIO

from invoke.vendor.six import text_type, binary_type, PY2
from invoke.vendor.lexicon import Lexicon

from blessings import Terminal
from enum import Enum
from invoke import Collection, task, Exit
from releases.util import parse_changelog
from tabulate import tabulate

from .semantic_version_monkey import Version

from ..util import tmpdir
from ..console import confirm


debug = logging.getLogger("invocations.packaging.release").debug


# TODO: this could be a good module to test out a more class-centric method of
# organizing tasks. E.g.:
# - 'Checks'/readonly things like 'should_changelog' live in a base class
# - one subclass defines dry-run actions for the 'verbs', and is used for
# sanity checking or dry-running
# - another subclass defines actual, mutating actions for the 'verbs', and is
# used for actual release management
# - are those classes simply arbitrary tasky classes used *by*
# actual task functions exposing them; or are they the collections themselves
# (as per #347)?
# - if the latter, how should one "switch" between the subclasses when dry
# running vs real running?
# - what's the CLI "API" look like for that?
#   - Different subcollections, e.g. `inv release.dry-run(.all/changelog/etc)`
#   vs `inv release.all`?
#   - Dry-run flag (which feels more natural/obvious/expected)? How
#   would/should that flag affect collection/task loading/selection?
#       - especially given task load concerns are typically part of core, but
#       this dry-run-or-not behavior clearly doesn't want to be in core?


#
# State junk
#

# Blessings Terminal object for ANSI colorization.
# NOTE: mildly uncomfortable with the instance living at module level, but also
# pretty sure it's unlikely to change meaningfully over time, between
# threads/etc - and it'd be otherwise a PITA to cart around/re-instantiate.
t = Terminal()
check = "\u2714"
ex = "\u2718"

# Types of releases/branches
Release = Enum("Release", "BUGFIX FEATURE UNDEFINED")

# Actions to take for various components - done as enums whose values are
# useful one-line status outputs.


class Changelog(Enum):
    OKAY = t.green(check + " no unreleased issues")
    NEEDS_RELEASE = t.red(ex + " needs :release: entry")


class VersionFile(Enum):
    OKAY = t.green(check + " version up to date")
    NEEDS_BUMP = t.red(ex + " needs version bump")


class Tag(Enum):
    OKAY = t.green(check + " all set")
    NEEDS_CUTTING = t.red(ex + " needs cutting")


# Bits for testing branch names to determine release type
BUGFIX_RE = re.compile(r"^\d+\.\d+$")
BUGFIX_RELEASE_RE = re.compile(r"^\d+\.\d+\.\d+$")
# TODO: allow tweaking this if folks use different branch methodology:
# - same concept, different name, e.g. s/main/dev/
# - different concept entirely, e.g. no main-ish, only feature branches
FEATURE_RE = re.compile(r"^(main|master)$")


class UndefinedReleaseType(Exception):
    pass


def _converge(c):
    """
    Examine world state, returning data on what needs updating for release.

    :param c: Invoke ``Context`` object or subclass.

    :returns:
        Two dicts (technically, dict subclasses, which allow attribute access),
        ``actions`` and ``state`` (in that order.)

        ``actions`` maps release component names to variables (usually class
        constants) determining what action should be taken for that component:

        - ``changelog``: members of `.Changelog` such as ``NEEDS_RELEASE`` or
          ``OKAY``.
        - ``version``: members of `.VersionFile`.

        ``state`` contains the data used to calculate the actions, in case the
        caller wants to do further analysis:

        - ``branch``: the name of the checked-out Git branch.
        - ``changelog``: the parsed project changelog, a `dict` of releases.
        - ``release_type``: what type of release the branch appears to be (will
          be a member of `.Release` such as ``Release.BUGFIX``.)
        - ``latest_line_release``: the latest changelog release found for
          current release type/line.
        - ``latest_overall_release``: the absolute most recent release entry.
          Useful for determining next minor/feature release.
        - ``current_version``: the version string as found in the package's
          ``__version__``.
    """
    #
    # Data/state gathering
    #

    # Get data about current repo context: what branch are we on & what kind of
    # release does it appear to represent?
    branch, release_type = _release_line(c)
    # Short-circuit if type is undefined; we can't do useful work for that.
    if release_type is Release.UNDEFINED:
        raise UndefinedReleaseType(
            "You don't seem to be on a release-related branch; "
            "why are you trying to cut a release?"
        )
    # Parse our changelog so we can tell what's released and what's not.
    # TODO: below needs to go in something doc-y somewhere; having it in a
    # non-user-facing subroutine docstring isn't visible enough.
    """
    .. note::
        Requires that one sets the ``packaging.changelog_file`` configuration
        option; it should be a relative or absolute path to your
        ``changelog.rst`` (or whatever it's named in your project).
    """
    # TODO: allow skipping changelog if not using Releases since we have no
    # other good way of detecting whether a changelog needs/got an update.
    # TODO: chdir to sphinx.source, import conf.py, look at
    # releases_changelog_name - that way it will honor that setting and we can
    # ditch this explicit one instead. (and the docstring above)
    changelog = parse_changelog(
        c.packaging.changelog_file, load_extensions=True
    )
    # Get latest appropriate changelog release and any unreleased issues, for
    # current line
    line_release, issues = _release_and_issues(changelog, branch, release_type)
    # Also get latest overall release, sometimes that matters (usually only
    # when latest *appropriate* release doesn't exist yet)
    overall_release = _versions_from_changelog(changelog)[-1]
    # Obtain the project's main package & its version data
    current_version = load_version(c)
    # Grab all git tags
    tags = _get_tags(c)

    state = Lexicon(
        {
            "branch": branch,
            "release_type": release_type,
            "changelog": changelog,
            "latest_line_release": Version(line_release)
            if line_release
            else None,
            "latest_overall_release": overall_release,  # already a Version
            "unreleased_issues": issues,
            "current_version": Version(current_version),
            "tags": tags,
        }
    )
    # Version number determinations:
    # - latest actually-released version
    # - the next version after that for current branch
    # - which of the two is the actual version we're looking to converge on,
    # depends on current changelog state.
    latest_version, next_version = _latest_and_next_version(state)
    state.latest_version = latest_version
    state.next_version = next_version
    state.expected_version = latest_version
    if state.unreleased_issues:
        state.expected_version = next_version

    #
    # Logic determination / convergence
    #

    actions = Lexicon()

    # Changelog: needs new release entry if there are any unreleased issues for
    # current branch's line.
    # TODO: annotate with number of released issues [of each type?] - so not
    # just "up to date!" but "all set (will release 3 features & 5 bugs)"
    actions.changelog = Changelog.OKAY
    if release_type in (Release.BUGFIX, Release.FEATURE) and issues:
        actions.changelog = Changelog.NEEDS_RELEASE

    # Version file: simply whether version file equals the target version.
    # TODO: corner case of 'version file is >1 release in the future', but
    # that's still wrong, just would be a different 'bad' status output.
    actions.version = VersionFile.OKAY
    if state.current_version != state.expected_version:
        actions.version = VersionFile.NEEDS_BUMP

    # Git tag: similar to version file, except the check is existence of tag
    # instead of comparison to file contents. We even reuse the
    # 'expected_version' variable wholesale.
    actions.tag = Tag.OKAY
    if state.expected_version not in state.tags:
        actions.tag = Tag.NEEDS_CUTTING

    #
    # Return
    #

    return actions, state


@task
def status(c):
    """
    Print current release (version, changelog, tag, etc) status.

    Doubles as a subroutine, returning the return values from its inner call to
    ``_converge`` (an ``(actions, state)`` two-tuple of Lexicons).
    """
    # TODO: wants some holistic "you don't actually HAVE any changes to
    # release" final status - i.e. all steps were at no-op status.
    actions, state = _converge(c)
    table = []
    # NOTE: explicit 'sensible' sort (in rough order of how things are usually
    # modified, and/or which depend on one another, e.g. tags are near the end)
    for component in "changelog version tag".split():
        table.append((component.capitalize(), actions[component].value))
    print(tabulate(table))
    return actions, state


@task(default=True)
def all_(c):
    """
    Catchall version-bump/tag/changelog/PyPI upload task.
    """
    prepare(c)
    # TODO: below
    # push(c)
    # build(c)
    # publish(c) # TODO: update publish() to accept some of our state and do
    # things with it like be idempotent?


@task
def prepare(c):
    """
    Edit changelog & version, git commit, and git tag, to set up for release.
    """
    # Print dry-run/status/actions-to-take data & grab programmatic result
    # TODO: maybe expand the enum-based stuff to have values that split up
    # textual description, command string, etc. See the TODO up by their
    # definition too, re: just making them non-enum classes period.
    # TODO: otherwise, we at least want derived eg changelog/version/etc paths
    # transmitted from status() into here...
    actions, state = status(c)
    # TODO: unless nothing-to-do in which case just say that & exit 0
    if not confirm("Take the above actions?"):
        raise Exit("Aborting.")

    # TODO: factor out what it means to edit a file:
    # - $EDITOR or explicit expansion of it in case no shell involved
    # - pty=True and hide=False, because otherwise things can be bad
    # - what else?

    # Changelog! (pty for non shite editing, eg vim sure won't like non-pty)
    if actions.changelog is Changelog.NEEDS_RELEASE:
        # TODO: identify top of list and inject a ready-made line? Requires vim
        # assumption...GREAT opportunity for class/method based tasks!
        cmd = "$EDITOR {.packaging.changelog_file}".format(c)
        c.run(cmd, pty=True, hide=False)
    # TODO: add a step for checking reqs.txt / setup.py vs virtualenv contents
    # Version file!
    if actions.version == VersionFile.NEEDS_BUMP:
        # TODO: suggest the bump and/or overwrite the entire file? Assumes a
        # specific file format. Could be bad for users which expose __version__
        # but have other contents as well.
        version_file = os.path.join(
            _find_package(c),
            c.packaging.get("version_module", "_version") + ".py",
        )
        cmd = "$EDITOR {}".format(version_file)
        c.run(cmd, pty=True, hide=False)
    if actions.tag == Tag.NEEDS_CUTTING:
        # Commit, if necessary, so the tag includes everything.
        # NOTE: this strips out untracked files. effort.
        cmd = 'git status --porcelain | egrep -v "^\\?"'
        if c.run(cmd, hide=True, warn=True).ok:
            c.run(
                'git commit -am "Cut {}"'.format(state.expected_version),
                hide=False,
            )
        # Tag!
        c.run("git tag {}".format(state.expected_version), hide=False)
        # TODO: print something to clarify/confirm tag was cut, if not just
        # adding echo=True to above


def _release_line(c):
    """
    Examine current repo state to determine what type of release to prep.

    :returns:
        A two-tuple of ``(branch-name, line-type)`` where:

        - ``branch-name`` is the current branch name, e.g. ``1.1``, ``main``,
          ``gobbledygook`` (or, usually, ``HEAD`` if not on a branch).
        - ``line-type`` is a symbolic member of `.Release` representing what
          "type" of release the line appears to be for:

            - ``Release.BUGFIX`` if on a bugfix/stable release line, e.g.
              ``1.1``.
            - ``Release.FEATURE`` if on a feature-release branch (typically
              ``main``).
            - ``Release.UNDEFINED`` if neither of those appears to apply
              (usually means on some unmerged feature/dev branch).
    """
    # TODO: I don't _think_ this technically overlaps with Releases (because
    # that only ever deals with changelog contents, and therefore full release
    # version numbers) but in case it does, move it there sometime.
    # TODO: this and similar calls in this module may want to be given an
    # explicit pointer-to-git-repo option (i.e. if run from outside project
    # context).
    # TODO: major releases? or are they big enough events we don't need to
    # bother with the script? Also just hard to gauge - when is main the next
    # 1.x feature vs 2.0?
    branch = c.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()
    type_ = Release.UNDEFINED
    if BUGFIX_RE.match(branch):
        type_ = Release.BUGFIX
    if FEATURE_RE.match(branch):
        type_ = Release.FEATURE
    return branch, type_


def _latest_feature_bucket(changelog):
    """
    Select 'latest'/'highest' unreleased feature bucket from changelog.

    :returns: a string key from ``changelog``.
    """
    unreleased = [x for x in changelog if x.startswith("unreleased_")]
    return sorted(
        unreleased, key=lambda x: int(x.split("_")[1]), reverse=True
    )[0]


# TODO: this feels like it should live in Releases, though that would imply
# adding semantic_version as a dep there, grump
def _versions_from_changelog(changelog):
    """
    Return all released versions from given ``changelog``, sorted.

    :param dict changelog:
        A changelog dict as returned by ``releases.util.parse_changelog``.

    :returns: A sorted list of `semantic_version.Version` objects.
    """
    versions = [Version(x) for x in changelog if BUGFIX_RELEASE_RE.match(x)]
    return sorted(versions)


# TODO: may want to live in releases.util eventually
def _release_and_issues(changelog, branch, release_type):
    """
    Return most recent branch-appropriate release, if any, and its contents.

    :param dict changelog:
        Changelog contents, as returned by ``releases.util.parse_changelog``.

    :param str branch:
        Branch name.

    :param release_type:
        Member of `Release`, e.g. `Release.FEATURE`.

    :returns:
        Two-tuple of release (``str``) and issues (``list`` of issue numbers.)

        If there is no latest release for the given branch (e.g. if it's a
        feature or main branch), it will be ``None``.
    """
    # Bugfix lines just use the branch to find issues
    bucket = branch
    # Features need a bit more logic
    if release_type is Release.FEATURE:
        bucket = _latest_feature_bucket(changelog)
    # Issues is simply what's in the bucket
    issues = changelog[bucket]
    # Latest release is undefined for feature lines
    release = None
    # And requires scanning changelog, for bugfix lines
    if release_type is Release.BUGFIX:
        versions = [text_type(x) for x in _versions_from_changelog(changelog)]
        release = [x for x in versions if x.startswith(bucket)][-1]
    return release, issues


def _get_tags(c):
    """
    Return sorted list of release-style tags as semver objects.
    """
    tags_ = []
    for tagstr in c.run("git tag", hide=True).stdout.strip().split("\n"):
        try:
            tags_.append(Version(tagstr))
        # Ignore anything non-semver; most of the time they'll be non-release
        # tags, and even if they are, we can't reason about anything
        # non-semver anyways.
        # TODO: perhaps log these to DEBUG
        except ValueError:
            pass
    # Version objects sort semantically
    return sorted(tags_)


def _latest_and_next_version(state):
    """
    Determine latest version for current branch, and its increment.

    E.g. on the ``1.2`` branch, we take the latest ``1.2.x`` release and
    increment its tertiary number, so e.g. if the previous release was
    ``1.2.2``, this function returns ``1.2.3``. If on ``main`` and latest
    overall release was ``1.2.2``, it returns ``1.3.0``.

    :param dict state:
        The ``state`` dict as returned by / generated within `converge`.

    :returns: 2-tuple of ``semantic_version.Version``.
    """
    if state.release_type == Release.FEATURE:
        previous_version = state.latest_overall_release
        next_version = previous_version.next_minor()
    else:
        previous_version = state.latest_line_release
        next_version = previous_version.next_patch()
    return previous_version, next_version


def _find_package(c):
    """
    Try to find 'the' One True Package for this project.

    Mostly for obtaining the ``_version`` file within it.

    Uses the ``packaging.package`` config setting if defined. If not defined,
    fallback is to look for a single top-level Python package (directory
    containing ``__init__.py``). (This search ignores a small blacklist of
    directories like ``tests/``, ``vendor/`` etc.)
    """
    # TODO: is there a way to get this from the same place setup.py does w/o
    # setup.py barfing (since setup() runs at import time and assumes CLI use)?
    configured_value = c.get("packaging", {}).get("package", None)
    if configured_value:
        return configured_value
    # TODO: tests covering this stuff here (most logic tests simply supply
    # config above)
    packages = [
        path
        for path in os.listdir(".")
        if (
            os.path.isdir(path)
            and os.path.exists(os.path.join(path, "__init__.py"))
            and path not in ("tests", "integration", "sites", "vendor")
        )
    ]
    if not packages:
        raise Exit("Unable to find a local Python package!")
    if len(packages) > 1:
        raise Exit("Found multiple Python packages: {!r}".format(packages))
    return packages[0]


def load_version(c):
    package_name = _find_package(c)
    version_module = c.packaging.get("version_module", "_version")
    # NOTE: have to explicitly give it a bytestr (Python 2) or unicode (Python
    # 3) because https://bugs.python.org/issue21720 HOORAY
    cast = binary_type if PY2 else text_type
    package = __import__(package_name, fromlist=[cast(version_module)])
    # TODO: explode nicely if it lacks a _version/etc, or a __version__
    # TODO: make this a Version()?
    return getattr(package, version_module).__version__


@task
def build(c, sdist=True, wheel=True, directory=None, python=None, clean=False):
    """
    Build sdist and/or wheel archives, optionally in a temp base directory.

    All parameters/flags honor config settings of the same name, under the
    ``packaging`` tree. E.g. say ``.configure({'packaging': {'wheel':
    False}})`` to disable building wheel archives by default.

    :param bool sdist:
        Whether to build sdists/tgzs. Default: ``True``.

    :param bool wheel:
        Whether to build wheels (requires the ``wheel`` package from PyPI).
        Default: ``True``.

    :param str directory:
        Allows specifying a specific directory in which to perform builds and
        dist creation. Useful when running as a subroutine from ``publish``
        which sets up a temporary directory.

        Up to two subdirectories may be created within this directory: one for
        builds (if building wheels), and one for the dist archives.

        When ``None`` or another false-y value (which is the default), the
        current working directory is used (and thus, local ``dist/`` and
        ``build/`` subdirectories).

    :param str python:
        Which Python binary to use when invoking ``setup.py``.

        Defaults to ``"python"``.

        If ``wheel=True``, then this Python must have ``wheel`` installed in
        its default ``site-packages`` (or similar) location.

    :param clean:
        Whether to clean out the build and dist directories before building.

    .. versionchanged:: 2.0
        ``clean`` now defaults to False instead of True, cleans both dist and
        build dirs when True, and honors configuration.
    .. versionchanged:: 2.0
        ``wheel`` now defaults to True instead of False.
    """
    # Config hooks
    config = c.config.get("packaging", {})
    # Check bool flags to see if they were overridden by config.
    # TODO: this wants something explicit at the Invoke layer, technically this
    # prevents someone from giving eg --sdist on CLI to override a falsey
    # config value for it.
    if sdist is True and "sdist" in config:
        sdist = config["sdist"]
    if wheel is True and "wheel" in config:
        wheel = config["wheel"]
    if clean is False and "clean" in config:
        clean = config["clean"]
    if directory is None:
        directory = config.get("directory", "")
    if python is None:
        python = config.get("python", "python")  # buffalo buffalo
    # Sanity
    if not sdist and not wheel:
        raise Exit(
            "You said no sdists and no wheels..."
            "what DO you want to build exactly?"
        )
    # Directory path/arg logic
    dist_dir = os.path.join(directory, "dist")
    dist_arg = "-d {}".format(dist_dir)
    build_dir = os.path.join(directory, "build")
    build_arg = "-b {}".format(build_dir)
    # Clean
    if clean:
        for target in (dist_dir, build_dir):
            rmtree(target, ignore_errors=True)
    # Build
    parts = [python, "setup.py"]
    if sdist:
        parts.extend(("sdist", dist_arg))
    if wheel:
        # Manually execute build in case we are using a custom build dir.
        # Doesn't seem to be a way to tell bdist_wheel to do this directly.
        parts.extend(("build", build_arg))
        parts.extend(("bdist_wheel", dist_arg))
    c.run(" ".join(parts))


def find_gpg(c):
    for candidate in "gpg gpg1 gpg2".split():
        if c.run("which {}".format(candidate), hide=True, warn=True).ok:
            return candidate


# TODO: open some PRs for twine to push things like dual wheels, better
# dry-run/cleanroom directory concerns, etc into it.
# TODO: consider making this idempotent re: checking if the 'current release'
# already exists on PyPI. Or just hope PyPI response on error is sufficiently
# useful and trap/print that.
@task
def publish(
    c,
    sdist=True,
    wheel=True,
    index=None,
    sign=False,
    dry_run=False,
    directory=None,
    dual_wheels=False,
    alt_python=None,
    check_desc=False,
):
    """
    Publish code to PyPI or index of choice.

    All parameters save ``dry_run`` and ``directory`` honor config settings of
    the same name, under the ``packaging`` tree. E.g. say
    ``.configure({'packaging': {'wheel': True}})`` to force building wheel
    archives by default.

    :param bool sdist:
        Whether to upload sdists/tgzs.

    :param bool wheel:
        Whether to upload wheels (requires the ``wheel`` package from PyPI).

    :param str index:
        Custom upload index/repository name. See ``upload`` help for details.

    :param bool sign:
        Whether to sign the built archive(s) via GPG.

    :param bool dry_run:
        Skip actual publication step if ``True``.

        This also prevents cleanup of the temporary build/dist directories, so
        you can examine the build artifacts.

    :param str directory:
        Base directory within which will live the ``dist/`` and ``build/``
        directories.

        Defaults to a temporary directory which is cleaned up after the run
        finishes.

    :param bool dual_wheels:
        When ``True``, builds individual wheels for Python 2 and Python 3.

        Useful for situations where you can't build universal wheels, but still
        want to distribute for both interpreter versions.

        Requires that you have a useful ``python3`` (or ``python2``, if you're
        on Python 3 already) binary in your ``$PATH``. Also requires that this
        other python have the ``wheel`` package installed in its
        ``site-packages``; usually this will mean the global site-packages for
        that interpreter.

        See also the ``alt_python`` argument.

    :param str alt_python:
        Path to the 'alternate' Python interpreter to use when
        ``dual_wheels=True``.

        When ``None`` (the default) will be ``python3`` or ``python2``,
        depending on the currently active interpreter.

    :param bool check_desc:
        Whether to run ``setup.py check -r -s`` (uses ``readme_renderer``)
        before trying to publish - catches long_description bugs. Default:
        ``False``.
    """
    # Don't hide by default, this step likes to be verbose most of the time.
    c.config.run.hide = False
    # Config hooks
    config = c.config.get("packaging", {})
    index = config.get("index", index)
    if sign is False and "sign" in config:
        sign = config["sign"]
    if dual_wheels is False and "dual_wheels" in config:
        dual_wheels = config["dual_wheels"]
    if check_desc is False and "check_desc" in config:
        check_desc = config["check_desc"]
    # Initial sanity check, if needed. Will die usefully.
    if check_desc:
        c.run("python setup.py check -r -s")
    # Build, into controlled temp dir (avoids attempting to re-upload old
    # files)
    with tmpdir(skip_cleanup=dry_run, explicit=directory) as tmp:
        # Build default archives
        build(c, sdist=sdist, wheel=wheel, directory=tmp)
        # Build opposing interpreter archive, if necessary
        if dual_wheels:
            if not alt_python:
                alt_python = "python2"
                if sys.version_info[0] == 2:
                    alt_python = "python3"
            build(c, sdist=False, wheel=True, directory=tmp, python=alt_python)
        # Do the thing!
        upload(c, directory=tmp, index=index, sign=sign, dry_run=dry_run)


def upload(c, directory, index=None, sign=False, dry_run=False):
    """
    Upload (potentially also signing) all artifacts in ``directory``.

    :param str index:
        Custom upload index/repository name.

        By default, uses whatever the invoked ``pip`` is configured to use.
        Modify your ``pypirc`` file to add new named repositories.

    :param bool sign:
        Whether to sign the built archive(s) via GPG.

    :param bool dry_run:
        Skip actual publication step if ``True``.

        This also prevents cleanup of the temporary build/dist directories, so
        you can examine the build artifacts.
    """
    # Obtain list of archive filenames, then ensure any wheels come first
    # so their improved metadata is what PyPI sees initially (otherwise, it
    # only honors the sdist's lesser data).
    archives = list(
        itertools.chain.from_iterable(
            glob(os.path.join(directory, "dist", "*.{}".format(extension)))
            for extension in ("whl", "tar.gz")
        )
    )
    # Sign each archive in turn
    # TODO: twine has a --sign option; but the below is still nice insofar
    # as it lets us dry-run, generate for web upload when pypi's API is
    # being cranky, etc. Figure out which is better.
    if sign:
        prompt = "Please enter GPG passphrase for signing: "
        input_ = StringIO(getpass.getpass(prompt) + "\n")
        gpg_bin = find_gpg(c)
        if not gpg_bin:
            raise Exit(
                "You need to have one of `gpg`, `gpg1` or `gpg2` "
                "installed to GPG-sign!"
            )
        for archive in archives:
            cmd = "{} --detach-sign -a --passphrase-fd 0 {{}}".format(
                gpg_bin
            )  # noqa
            c.run(cmd.format(archive), in_stream=input_)
            input_.seek(0)  # So it can be replayed by subsequent iterations
    # Upload
    parts = ["twine", "upload"]
    if index:
        index_arg = "--repository {}".format(index)
    if index:
        parts.append(index_arg)
    paths = archives[:]
    if sign:
        paths.append(os.path.join(directory, "dist", "*.asc"))
    parts.extend(paths)
    cmd = " ".join(parts)
    if dry_run:
        print("Would publish via: {}".format(cmd))
        print("Files that would be published:")
        c.run("ls -l {}".format(" ".join(paths)))
    else:
        c.run(cmd)


# Stitch together current partway-rewritten stuff into public namespace.
# TODO: reconsider once fully done; may end up looking a lot like this anyways.
ns = Collection("release", all_, status, prepare, build, publish)
# Hide stdout by default, preferring to explicitly enable it when necessary.
ns.configure({"run": {"hide": "stdout"}})
