"""
Python package release tasks.

This module assumes:

- you're using semantic versioning for your releases
- you're using a modern pyproject.toml for packaging metadata
"""

import getpass
import logging
import os
import re
import venv
from functools import partial
from io import StringIO
from pathlib import Path
from shutil import rmtree
from typing import Union

from build._builder import _read_pyproject_toml
from invoke.vendor.lexicon import Lexicon

from blessings import Terminal
from docutils.utils import Reporter
from enum import Enum
from invoke import Collection, task, Exit
from pip import __version__ as pip_version
import readme_renderer.rst  # transitively required via twine in setup.py
from releases.util import parse_changelog
from tabulate import tabulate
from twine.commands.check import check as twine_check

from .semantic_version_monkey import Version

from ..console import confirm
from ..environment import in_ci
from ..util import tmpdir


debug = logging.getLogger("invocations.packaging.release").debug

# Monkeypatch readme_renderer.rst so it acts more like Sphinx re: docutils
# warning levels - otherwise it overlooks (and misrenders) stuff like bad
# header formats etc!
# (The defaults in readme_renderer are halt_level=WARNING and
# report_level=SEVERE)
# NOTE: this only works because we directly call twine via Python and not via
# subprocess.
for key in ("halt_level", "report_level"):
    readme_renderer.rst.SETTINGS[key] = Reporter.INFO_LEVEL


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
          packaging metadata.
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
    # Obtain the project's defined (not installed) version number
    pyproject = Path.cwd() / "pyproject.toml"
    current_version = _read_pyproject_toml(pyproject)["project"]["version"]

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

    actions.all_okay = (
        actions.changelog == Changelog.OKAY
        and actions.version == VersionFile.OKAY
        and actions.tag == Tag.OKAY
    )

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
    actions, state = _converge(c)
    table = []
    # NOTE: explicit 'sensible' sort (in rough order of how things are usually
    # modified, and/or which depend on one another, e.g. tags are near the end)
    for component in "changelog version tag".split():
        table.append((component.capitalize(), actions[component].value))
    print(tabulate(table))
    return actions, state


# TODO: thought we had automatic trailing underscore stripping but...no?
@task(name="all", default=True)
def all_(c, dry_run=False):
    """
    Catchall version-bump/tag/changelog/PyPI upload task.

    :param bool dry_run:
        Handed to all subtasks which themselves have a ``dry_run`` flag.

    .. versionchanged:: 2.1
        Expanded functionality to run ``publish`` and ``push`` as well as
        ``prepare``.
    .. versionchanged:: 2.1
        Added the ``dry_run`` flag.
    """
    prepare(c, dry_run=dry_run)
    publish(c, dry_run=dry_run)
    push(c, dry_run=dry_run)


@task
def prepare(c, dry_run=False):
    """
    Edit changelog & version, git commit, and git tag, to set up for release.

    :param bool dry_run:
        Whether to take any actual actions or just say what might occur. Will
        also non-fatally exit if not on some form of release branch. Default:
        ``False``.

    :returns: ``True`` if short-circuited due to all-ok, ``None`` otherwise.

    .. versionchanged:: 2.1
        Added the ``dry_run`` parameter.
    .. versionchanged:: 2.1
        Generate annotated git tags instead of lightweight ones.
    """
    # Print dry-run/status/actions-to-take data & grab programmatic result
    # TODO: maybe expand the enum-based stuff to have values that split up
    # textual description, command string, etc. See the TODO up by their
    # definition too, re: just making them non-enum classes period.
    # TODO: otherwise, we at least want derived eg changelog/version/etc paths
    # transmitted from status() into here...
    try:
        actions, state = status(c)
    except UndefinedReleaseType:
        if not dry_run:
            raise
        raise Exit(
            code=0,
            message="Can't dry-run release tasks, not on a release branch; skipping.",  # noqa
        )
    # Short-circuit if nothing to do
    if actions.all_okay:
        return True
    # If work to do and not dry-running, make sure user confirms to move ahead
    if not dry_run:
        if not confirm("Take the above actions?"):
            raise Exit("Aborting.")

    # TODO: factor out what it means to edit a file:
    # - $EDITOR or explicit expansion of it in case no shell involved
    # - pty=True and hide=False, because otherwise things can be bad
    # - what else?

    # Changelog! (pty for non shite editing, eg vim sure won't like non-pty)
    if actions.changelog == Changelog.NEEDS_RELEASE:
        # TODO: identify top of list and inject a ready-made line? Requires vim
        # assumption...GREAT opportunity for class/method based tasks!
        cmd = "$EDITOR {.packaging.changelog_file}".format(c)
        c.run(cmd, pty=True, hide=False, dry=dry_run)
    # Version file!
    if actions.version == VersionFile.NEEDS_BUMP:
        cmd = "$EDITOR pyproject.toml"
        c.run(cmd, pty=True, hide=False, dry=dry_run)
    if actions.tag == Tag.NEEDS_CUTTING:
        # Commit, if necessary, so the tag includes everything.
        # NOTE: this strips out untracked files. effort.
        cmd = 'git status --porcelain | egrep -v "^\\?"'
        if c.run(cmd, hide=True, warn=True).ok:
            c.run(
                'git commit -am "Cut {}"'.format(state.expected_version),
                hide=False,
                dry=dry_run,
                echo=True,
            )
        # Tag!
        c.run(
            'git tag -a {} -m ""'.format(state.expected_version),
            hide=False,
            dry=dry_run,
            echo=True,
        )
    # If top-of-task status check wasn't all_okay, it means the code between
    # there and here was expected to alter state. Run another check to make
    # sure those actions actually succeeded!
    if not dry_run and not actions.all_okay:
        actions, state = status(c)
        if not actions.all_okay:
            raise Exit("Something went wrong! Please fix.")


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
    # TODO: yea, this is currently a slightly annoying hole, workaround is to:
    # - be on main still
    # - update your pyproject's version to eg 3.0.0
    # - add the 3.0.0 release entry in your changelog (without that, this
    # module will croak on assumptions)
    # - commit
    # - branch to 3.0
    # - running eg `inv release --dry-run` should now work as expected
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
        versions = [str(x) for x in _versions_from_changelog(changelog)]
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

    Uses the ``packaging.package`` config setting if defined. If not defined,
    fallback is to look for a single top-level Python package (directory
    containing ``__init__.py``). (This search ignores a small blacklist of
    directories like ``tests/``, ``vendor/`` etc.)
    """
    # TODO: try using importlib now it's in stdlib?
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


@task
def build(c, sdist=True, wheel=True, directory=None, python=None, clean=False):
    """
    Build sdist and/or wheel archives, optionally in a temp base directory.

    Uses the `build <https://build.pypa.io/en/stable/>`_ tool from PyPA.

    All parameters/flags honor config settings of the same name, under the
    ``packaging`` tree. E.g. say ``.configure({'packaging': {'wheel':
    False}})`` to disable building wheel archives by default.

    :param bool sdist:
        Whether to build sdists/tgzs. Default: ``True``.

    :param bool wheel:
        Whether to build wheels (requires the ``wheel`` package from PyPI).
        Default: ``True``.

    :param str directory:
        Allows specifying a specific directory in which to perform dist
        creation. Useful when running as a subroutine from ``publish`` which
        sets up a temporary directory. Defaults to the current working
        directory + ``dist/`` (the same as ``pypa/build``'s default behavior,
        albeit explicitly derived to support our own functionality).

    :param clean:
        Whether to remove the dist directory before building.

    :param str python:
        Which Python binary to use when invoking ``-m build``.

        Defaults to ``"python"``.

        If ``wheel=True``, then this Python must have ``wheel`` installed in
        its default ``site-packages`` (or similar) location.

    .. versionchanged:: 2.0
        ``clean`` now defaults to False instead of True, cleans both dist and
        build dirs when True, and honors configuration.
    .. versionchanged:: 2.0
        ``wheel`` now defaults to True instead of False.
    .. versionchanged:: 4.0
        Switched to using ``pypa/build`` and made related changes to args
        (eg, ``directory`` now only controls dist output location).
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
        directory = Path(config.get("directory", Path.cwd() / "dist"))
        if directory.is_absolute():
            directory = directory.relative_to(Path.cwd())
    print(f"Building into {directory}...")
    if python is None:
        python = config.get("python", "python")  # buffalo buffalo
    # Sanity
    if not sdist and not wheel:
        raise Exit(
            "You said no sdists and no wheels..."
            "what DO you want to build exactly?"
        )
    # Start building command
    parts = [python, "-m build"]
    # Set, clean directory as needed
    parts.append(f"--outdir {directory}")
    if clean:
        rmtree(directory, ignore_errors=True)
    if sdist:
        parts.append("--sdist")
    if wheel:
        parts.append("--wheel")
    c.run(" ".join(parts))
    print("Result:")
    c.run(f"ls -l {directory}", echo=True, hide=False)


def find_gpg(c):
    for candidate in "gpg gpg1 gpg2".split():
        if c.run("which {}".format(candidate), hide=True, warn=True).ok:
            return candidate


@task
def publish(
    c,
    sdist=True,
    wheel=True,
    index=None,
    sign=False,
    dry_run=False,
    directory=None,
):
    """
    Publish code to PyPI or index of choice. Wraps ``build`` and ``upload``.

    This uses the ``twine`` command under the hood, both its pre-upload
    ``check`` subcommand (which verifies the archives to be uploaded, including
    checking your PyPI readme) and the ``upload`` one.

    All parameters save ``dry_run`` and ``directory`` honor config settings of
    the same name, under the ``packaging`` tree. E.g. say
    ``.configure({'packaging': {'wheel': True}})`` to force building wheel
    archives by default.

    :param bool sdist:
        Whether to upload sdists/tgzs. Default: ``True``.

    :param bool wheel:
        Whether to upload wheels (requires the ``wheel`` package from PyPI).
        Default: ``True``.

    :param str index:
        Custom upload index/repository name. See ``upload`` help for details.

    :param bool sign:
        Whether to sign the built archive(s) via GPG.

    :param bool dry_run:
        Skip upload step if ``True``.

        This also prevents cleanup of the temporary build/dist directories, so
        you can examine the build artifacts.

        Note that this does not skip the ``twine check`` step, just the final
        upload.

    :param str directory:
        Used for ``build(directory=)`` and thus affects where dists go.

        Defaults to a temporary directory which is cleaned up after the run
        finishes.
    """
    # Don't hide by default, this step likes to be verbose most of the time.
    c.config.run.hide = False
    # Including echoing!
    c.config.run.echo = True
    # Config hooks
    # TODO: this pattern is too widespread. Really needs something in probably
    # Executor that automatically does this on our behalf for any kwargs we
    # indicate should be configurable
    config = c.config.get("packaging", {})
    if index is None and "index" in config:
        index = config["index"]
    if sign is False and "sign" in config:
        sign = config["sign"]
    # Build, into controlled temp dir (avoids attempting to re-upload old
    # files)
    with tmpdir(skip_cleanup=dry_run, explicit=directory) as tmp:
        # Build default archives
        builder = partial(build, c, sdist=sdist, wheel=wheel, directory=tmp)
        builder()
        # Rebuild with env (mostly for Fabric 2)
        # TODO: code smell; implies this really wants to be class/hook based?
        # TODO: or at least invert sometime so it's easier to say "do random
        # stuff to arrive at dists, then test and upload".
        rebuild_with_env = config.get("rebuild_with_env", None)
        if rebuild_with_env:
            old_environ = os.environ.copy()
            os.environ.update(rebuild_with_env)
            try:
                builder()
            finally:
                os.environ.update(old_environ)
                for key in rebuild_with_env:
                    if key not in old_environ:
                        del os.environ[key]
        # Use twine's check command on built artifacts (at present this just
        # validates long_description)
        print(c.config.run.echo_format.format(command="twine check"))
        failure = twine_check(dists=[os.path.join(tmp, "*")])
        if failure:
            raise Exit(1)
        # Test installation of built artifacts into virtualenvs (even during
        # dry run)
        test_install(c, directory=tmp)
        # Do the thing! (Maybe.)
        upload(c, directory=tmp, index=index, sign=sign, dry_run=dry_run)


@task
def test_install(c, directory, verbose=False, skip_import=False):
    """
    Test installation of build artifacts found in ``$directory``.

    Uses the `venv` module to build temporary virtualenvs.

    :param bool verbose: Whether to print subprocess output.
    :param bool skip_import:
        If True, don't try importing the installed module or checking it for
        type hints.
    """
    # TODO: wants contextmanager or similar for only altering a setting within
    # a given scope or block - this may pollute subsequent subroutine calls
    if verbose:
        old_hide = c.config.run.hide
        c.config.run.hide = False

    builder = venv.EnvBuilder(with_pip=True)
    archives = get_archives(directory)
    if not archives:
        raise Exit(f"No archive files found in {directory}!")
    for archive in archives:
        with tmpdir() as tmp:
            # Make temp venv
            builder.create(tmp)
            # Obligatory: make inner pip match outer pip (version obtained from
            # this file's executable env, up in import land); very frequently
            # venv-made envs have a bundled, older pip :(
            envbin = Path(tmp) / "bin"
            pip = envbin / "pip"
            c.run(f"{pip} install pip=={pip_version}")
            # Does the package under test install cleanly?
            c.run(f"{pip} install --disable-pip-version-check {archive}")
            # Can we actually import it? (Will catch certain classes of
            # import-time-but-not-install-time explosions, eg busted dependency
            # specifications or imports).
            if not skip_import:
                package = _find_package(c)
                # Import, generally
                c.run(f"{envbin / 'python'} -c 'import {package}'")
                # Import, typecheck version (ie dependent package typechecking
                # both itself and us). Assumes task is run from project root.
                # TODO: is py.typed still mandatory these days?
                pytyped = Path(package) / "py.typed"
                if pytyped.exists():
                    # TODO: pin a specific mypy version?
                    c.run(f"{envbin / 'pip'} install mypy")
                    # Use some other dir (our cwd is probably the project root,
                    # whose local $package dir may confuse mypy into a false
                    # positive!)
                    with tmpdir() as tmp2:
                        mypy_check = f"{envbin / 'mypy'} -c 'import {package}'"
                        c.run(f"cd {tmp2} && {mypy_check}")

    if verbose:
        c.config.run.hide = old_hide


def get_archives(directory: Union[str, Path]) -> list[Path]:
    """
    Obtain list of archive filenames, then ensure any wheels come first
    so their improved metadata is what PyPI sees initially (otherwise, it
    only honors the sdist's lesser data).
    """
    target = Path(directory)
    return sorted(target.glob("*.whl")) + sorted(target.glob("*.tar.gz"))


@task
def upload(c, directory, index=None, sign=False, dry_run=False):
    """
    Upload (potentially also signing) all artifacts in ``directory/dist``.

    :param str index:
        Custom upload index/repository name.

        By default, uses whatever the invoked ``pip`` is configured to use.
        Modify your ``pypirc`` file to add new named repositories.

    :param bool sign:
        Whether to sign the built archive(s) via GPG.

    :param bool dry_run:
        Skip actual publication step (and dry-run actions like signing) if
        ``True``.

        This also prevents cleanup of the temporary build/dist directories, so
        you can examine the build artifacts.
    """
    archives = get_archives(directory)
    # Sign each archive in turn
    # NOTE: twine has a --sign option but it's not quite flexible enough &
    # doesn't allow you to dry-run or upload manually when API is borked...
    if sign:
        prompt = "Please enter GPG passphrase for signing: "
        passphrase = "" if dry_run else getpass.getpass(prompt)
        input_ = StringIO(passphrase + "\n")
        gpg_bin = find_gpg(c)
        if not gpg_bin:
            raise Exit(
                "You need to have one of `gpg`, `gpg1` or `gpg2` "
                "installed to GPG-sign!"
            )
        for archive in archives:
            cmd = "{} --detach-sign --armor --passphrase-fd=0 --batch --pinentry-mode=loopback {{}}".format(  # noqa
                gpg_bin
            )
            c.run(cmd.format(archive), in_stream=input_, dry=dry_run)
            input_.seek(0)  # So it can be replayed by subsequent iterations
    # Upload
    parts = ["twine", "upload"]
    if index:
        parts.append(f"--repository {index}")
    paths = [str(x) for x in archives]
    if sign and not dry_run:
        paths.append(os.path.join(directory, "*.asc"))
    parts.extend(paths)
    cmd = " ".join(parts)
    if dry_run:
        print(f"Would publish via: {cmd}")
        print("Files that would be published:")
        c.run(f"ls -l {' '.join(paths)}")
    else:
        c.run(cmd)


@task
def push(c, dry_run=False):
    """
    Push current branch and tags to default Git remote.
    """
    # Push tags, not just branches; and at this stage pre-push hooks will be
    # more trouble than they're worth.
    opts = "--follow-tags --no-verify"
    # Dry run: echo, and either tack on git's own dry-run (if not CI) or
    # dry-run the run() itself (if CI - which probably can't push to the remote
    # and might thus error uselessly)
    kwargs = dict()
    if dry_run:
        kwargs["echo"] = True
        if in_ci():
            kwargs["dry"] = True
        else:
            opts += " --dry-run"
    c.run("git push {}".format(opts), **kwargs)


# TODO: still need time to solve the 'just myself pls' problem
ns = Collection(
    "release",
    all_,
    status,
    prepare,
    build,
    publish,
    push,
    test_install,
    upload,
)
# Hide stdout by default, preferring to explicitly enable it when necessary.
ns.configure({"run": {"hide": "stdout"}})
