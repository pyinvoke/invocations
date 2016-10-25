"""
Python package release tasks.

This module assumes:

- you're using semantic versioning for your releases
- you maintain a file called ``$package/_version.py`` containing normal version
  conventions (``__version_info__`` tuple and ``__version__`` string).
"""

import getpass
import itertools
import os
import re
import sys
from glob import glob
from shutil import rmtree

from invoke.vendor.six import StringIO

from invoke.vendor.six import text_type

# TODO: really not a fan of these optional requirements. Given nothing so far
# is C-extension based, maybe just suck it up & add them all as true
# requirements?

try:
    from enum import Enum
except ImportError:
    sys.exit("Need the 'enum' library and you seem to be on Python<3.4; please 'pip install enum34'!") # noqa

from invoke import Collection, task
try:
    from semantic_version import Version
except ImportError:
    sys.exit("Use of the packaging.release collection requires the `semantic_version` package; please install it!") # noqa
try:
    from releases.util import parse_changelog
except ImportError:
    sys.exit("Use of the packaging.release collection requires the `releases` package; please install it!") # noqa

from ..util import tmpdir


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

# TODO: I always feel a bit icky when I see the enum pattern, or the related
# one of "define a bunch of module level constants as integers". Feels
# non-Pythonic. But not sure what's truly better given the pitfalls of
# comparing strings as values. (String *keys* are typically much safer thanks
# to KeyError, but "if actions['changelog'] == 'needs_releas'" [note typo] is
# far easier to run into.)

# TODO: these enums kinda-sorta wants to grow and eat related functionality,
# e.g. Changelog.update(), Changelog.determine_state(), etc etc. In that case,
# probably switch (back) to regular classes with constants equal to their name
# strings (for debugging etc, as Enum does).

Release = Enum('Release', "BUGFIX FEATURE UNDEFINED")
Changelog = Enum('Changelog', "OKAY NEEDS_RELEASE")
VersionFile = Enum('VersionFile', "OKAY NEEDS_BUMP")

BUGFIX_RE = re.compile("^\d+\.\d+$")
BUGFIX_RELEASE_RE = re.compile("^\d+\.\d+\.\d+$")
# TODO: allow tweaking this if folks use different branch methodology:
# - same concept, different name, e.g. s/master/dev/
# - different concept entirely, e.g. no master-ish, only feature branches
FEATURE_RE = re.compile("^master$")

class UndefinedReleaseType(Exception):
    pass


def converge(c):
    """
    Examine world state, returning data on what needs updating for release.

    :param c: Invoke ``Context`` object or subclass.

    :returns:
        Two dicts, ``actions`` and ``state`` (in that order.)

        ``actions`` maps release component names to variables (usually class
        constants) determining what action should be taken for that component:

        - ``changelog``: members of `.Changelog` such as ``NEEDS_RELEASE`` or
          ``OKAY``.
        - ...

        ``state`` contains the data used to calculate the actions, in case the caller wants to do further analysis:

        - ``branch``: the name of the checked-out Git branch.
        - ``changelog``: the parsed project changelog, a `dict` of releases.
        - ``release_type``: what type of release the branch appears to be (will
          be a member of `.Release` such as ``Release.BUGFIX``.)
    """
    #
    # Data/state gathering
    #

    # Get data about current repo context: what branch are we on & what kind of
    # release does it appear to represent?
    branch, release_type = release_line(c)
    # Short-circuit if type is undefined; we can't do useful work for that.
    if release_type is Release.UNDEFINED:
        raise UndefinedReleaseType("You don't seem to be on a release-related branch; why are you trying to cut a release?") # noqa
    # Parse our changelog so we can tell what's released and what's not.
    # TODO: below needs to go in something doc-y somewhere; having it in a
    # non-user-facing subroutine docstring isn't visible enough.
    """
    .. note::
        Requires that one sets the ``packaging.changelog_file`` configuration
        option; it should be a relative or absolute path to your
        ``changelog.rst`` (or whatever it's named in your project).
    """
    # TODO: chdir to sphinx.source, import conf.py, look at
    # releases_changelog_name - that way it will honor that setting and we can
    # ditch this explicit one instead. (and the docstring above)
    changelog = parse_changelog(c.packaging.changelog_file)
    # Get latest changelog release and any unreleased issues, for current line
    release, issues = release_and_issues( changelog, branch, release_type)
    # Obtain the project's main package & its version data
    # TODO: explode nicely if it lacks a _version
    package = __import__(find_package(c), fromlist=['_version'])
    # TODO: probably make this & 'release' Version()s here
    current_version = package._version.__version__ # buffalo buffalo

    #
    # Logic determination / convergence
    #

    actions = {}

    # Changelog: needs new release entry if there are any unreleased issues for
    # current branch's line.
    actions['changelog'] = Changelog.OKAY
    if release_type in (Release.BUGFIX, Release.FEATURE) and issues:
        actions['changelog'] = Changelog.NEEDS_RELEASE

    # Version file: more complex - see subroutine.
    actions['version'] = VersionFile.OKAY
    if should_version(release, issues, current_version):
        actions['version'] = VersionFile.NEEDS_BUMP

    #
    # Return
    #

    state = {
        'branch': branch,
        'release_type': release_type,
        'changelog': changelog,
    }

    return actions, state


@task(name='all')
def all_(c, dry_run=False):
    """
    Catchall version-bump/tag/changelog/PyPI upload task.
    """

    #
    # Dry run display
    #

    # TODO: wants some holistic "you don't actually HAVE any changes to
    # release" final status - i.e. all steps were at no-op status.
    # TODO: color? if can do be done very quickly...see fabric#101 I think
    # TODO: tabulate (without column separators tho) - find that one I used at
    # UA
    # TODO: switch to future unicode_literals import!!
    check = u"\u2714"
    ex = u"\u2718"
    status = u"{0} up-to-date".format(check)
    # TODO: allow skipping changelog if not using Releases since we have no
    # other good way of detecting whether a changelog needs/got an update.
    if changelog_wants_release:
        status = u"{0} wants a :release: entry".format(ex)
    print(u"Changelog: {0}".format(status))

    # TODO: add a step for checking reqs.txt / setup.py vs virtualenv contents
    version(c)
    tag(c)
    push(c)
    build(c)
    publish(c)

    #
    # Actions
    #

    # TODO: probably want to always show dry-run, then when not
    # just-dry-running, display default-Y prompt saying "should I remedy this?"


def release_line(c):
    """
    Examine current repo state to determine what type of release to prep.

    :returns:
        A two-tuple of ``(branch-name, line-type)`` where:

        - ``branch-name`` is the current branch name, e.g. ``1.1``, ``master``,
          ``gobbledygook`` (or, usually, ``HEAD`` if not on a branch).
        - ``line-type`` is a symbolic member of `.Release` representing what
          "type" of release the line appears to be for:

            - ``Release.BUGFIX`` if on a bugfix/stable release line, e.g.
              ``1.1``.
            - ``Release.FEATURE`` if on a feature-release branch (typically
              ``master``).
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
    # bother with the script? Also just hard to gauge - when is master the next
    # 1.x feature vs 2.0?
    branch = c.run("git rev-parse --abbrev-ref HEAD").stdout.strip()
    type_ = Release.UNDEFINED
    if BUGFIX_RE.match(branch):
        type_ = Release.BUGFIX
    if FEATURE_RE.match(branch):
        type_ = Release.FEATURE
    return branch, type_


def latest_feature_bucket(changelog):
    """
    Select 'latest'/'highest' unreleased feature bucket from changelog.

    :returns: a string key from ``changelog``.
    """
    unreleased = [x for x in changelog if x.startswith('unreleased_')]
    return sorted(
        unreleased,
        key=lambda x: int(x.split('_')[1]),
        reverse=True,
    )[0]


# TODO: may want to live in releases.util eventually
def release_and_issues(changelog, branch, release_type):
    # Bugfix lines just use the branch to find issues
    bucket = branch
    # Features need a bit more logic
    if release_type is Release.FEATURE:
        bucket = latest_feature_bucket(changelog)
    # Issues is simply what's in the bucket
    issues = changelog[bucket]
    # Latest release is undefined for feature lines
    release = None
    # And requires scanning changelog, for bugfix lines
    if release_type is Release.BUGFIX:
        versions = []
        for x in changelog:
            if x.startswith(bucket) and BUGFIX_RELEASE_RE.match(x):
                versions.append(Version(x))
        release = text_type(sorted(versions)[-1]) # TODO: unicode-friendly?
    return release, issues


@task
def changelog(c, target='docs/changelog.rst'):
    """
    Update changelog with new release entry.
    """
    # TODO: work in should_changelog() so we short-circuit unless needed.
    pass


def tags(c):
    """
    Return sorted list of release-style tags as semver objects.
    """
    tags_ = []
    for tagstr in c.run("git tag", hide=True).stdout.strip().split('\n'):
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


def should_version(latest_release, issues, current_version):
    """
    Whether the project's packaging version needs to be updated.
    """
    latest_release = Version(latest_release)
    current_version = Version(current_version)
    # Possibilities:
    # - no pending changelog changes
    #   - changelog latest release == current version val: no action required
    #   - cl latest release > current version: need update (to the cl value -
    #   auto insert/replace??) TODO: how best to pass that kind of info between
    #   'should' and action func??
    #   - cl latest release < current version: shouldn't happen...implies bug
    #   or version got bumped too high
    # - pending changelog changes
    if issues:
    #   - changelog latest release == current version val: both need updating
    #   (to the derived next version number)
        if current_version == latest_release:
            return True
    #   - CL > version: wat. should not get here
    #   - CL < version: implies version has already been updated (& changelog
    #   wants that version)
    # TODO: when we fully control situation and user has done nothing besides
    # commit fixes, which of the two do we update first?


@task
def version(c):
    """
    Update stored project version (e.g. a ``_version.py``.)
    """
    # - version already > latest release-style tag
    #   - typically means we can no-op/short-circuit
    # tags_ =
    # - version == latest tag, & there's commits since then
    #   - implies version needs bump
    #   - likely has some annoying false positives...?
    pass


def find_package(c):
    """
    Try to find 'the' One True Package for this project.

    Mostly for obtaining the `_version` file within it.

    Uses the ``packaging.package`` config setting if defined. If not defined,
    fallback is to look for a single top-level Python package (directory
    containing ``__init__.py``). (This search ignores a small blacklist of
    directories like ``tests/``, ``vendor/`` etc.)
    """
    # TODO: is there a way to get this from the same place setup.py does w/o
    # setup.py barfing (since setup() runs at import time and assumes CLI use)?
    configured_value = c.get('packaging', {}).get('package', None)
    if configured_value:
        return configured_value
    # TODO: tests covering this stuff here (most logic tests simply supply
    # config above)
    packages = [
        path
        for path in os.listdir('.')
        if (
            os.path.isdir(path)
            and os.path.exists(os.path.join(path, '__init__.py'))
            and path not in ('tests', 'integration', 'sites', 'vendor')
        )
    ]
    if not packages:
        sys.exit("Unable to find a local Python package!")
    if len(packages) > 1:
        sys.exit("Found multiple Python packages: {0!r}".format(packages))
    return packages[0]


@task
def tag(c, dry_run=False):
    """
    Create a release tag in git, if one doesn't appear to already exist.

    You should already have 'bumped' your version prior to calling this - it
    compares to your existing list of git tags.

    :param bool dry_run: Whether to dry-run instead of actually tagging.
    """
    name = find_package(c)
    package = __import__("{0}".format(name), fromlist=['_version'])
    current_version = Version(package._version.__version__) # buffalo buffalo
    msg = "Found package {0.__name__!r} at version {1}"
    # TODO: use logging for this sometime
    print(msg.format(package, current_version))
    latest_tag = tags(c)[-1]
    # TODO: pre-task/call to version() task; perhaps use its return value to
    # determine whether it got updated or not.
    if latest_tag != current_version:
        msg = "Current version {0} != latest tag {1}, creating new tag"
        print(msg.format(current_version, latest_tag))
        # TODO: annotate!! -a or even GPG sign
        cmd = "git tag {0}".format(current_version)
        # TODO: use eventual run() dry-run feature
        if dry_run:
            print("Would run: {0}".format(cmd))
        else:
            c.run(cmd)
    else:
        msg = "Already see a tag for {0}, doing nothing"
        print(msg.format(current_version))


@task
def push(c):
    """
    Push tag/changelog/version changes to Git origin.
    """
    # TODO: or should this be distributed amongst the appropriate tasks?
    pass


@task
def build(c, sdist=True, wheel=False, directory=None, python=None, clean=True):
    """
    Build sdist and/or wheel archives, optionally in a temp base directory.

    All parameters save ``directory`` honor config settings of the same name,
    under the ``packaging`` tree. E.g. say ``.configure({'packaging': {'wheel':
    True}})`` to force building wheel archives by default.

    :param bool sdist:
        Whether to build sdists/tgzs.

    :param bool wheel:
        Whether to build wheels (requires the ``wheel`` package from PyPI).

    :param str directory:
        Allows specifying a specific directory in which to perform builds and
        dist creation. Useful when running as a subroutine from ``publish``
        which sets up a temporary directory.

        Two subdirectories will be created within this directory: one for
        builds, and one for the dist archives.

        When ``None`` or another false-y value, the current working directory
        is used (and thus, local ``dist/`` and ``build/`` subdirectories).

    :param str python:
        Which Python binary to use when invoking ``setup.py``.

        Defaults to just ``python``.

        If ``wheel=True``, then this Python must have ``wheel`` installed in
        its default ``site-packages`` (or similar) location.

    :param bool clean:
        Whether to clean out the local ``build/`` folder before building.
    """
    # Config hooks
    config = c.config.get('packaging', {})
    # TODO: update defaults to be None, then flip the below so non-None runtime
    # beats config.
    sdist = config.get('sdist', sdist)
    wheel = config.get('wheel', wheel)
    python = config.get('python', python or 'python') # buffalo buffalo
    # Sanity
    if not sdist and not wheel:
        sys.exit("You said no sdists and no wheels...what DO you want to build exactly?") # noqa
    # Directory path/arg logic
    if not directory:
        directory = "" # os.path.join() doesn't like None
    dist_dir = os.path.join(directory, "dist")
    dist_arg = "-d {0}".format(dist_dir)
    build_dir = os.path.join(directory, "build")
    build_arg = "-b {0}".format(build_dir)
    # Clean
    if clean:
        if os.path.exists(build_dir):
            rmtree(build_dir)
        # NOTE: not cleaning dist_dir, since this may be called >1 time within
        # publish() trying to build up multiple wheels/etc.
        # TODO: separate clean-build/clean-dist args? Meh
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
        if c.run("which {0}".format(candidate), hide=True, warn=True).ok:
            return candidate


# TODO: open some PRs for twine to push things like dual wheels, better
# dry-run/cleanroom directory concerns, etc into it.
@task(aliases=['upload'])
def publish(c, sdist=True, wheel=False, index=None, sign=False, dry_run=False,
    directory=None, dual_wheels=False, alt_python=None):
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
        Custom upload index URL.

        By default, uses whatever the invoked ``pip`` is configured to use.

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
    """
    # Config hooks
    config = c.config.get('packaging', {})
    index = config.get('index', index)
    sign = config.get('sign', sign)
    dual_wheels = config.get('dual_wheels', dual_wheels)
    # Build, into controlled temp dir (avoids attempting to re-upload old
    # files)
    with tmpdir(skip_cleanup=dry_run, explicit=directory) as tmp:
        # Build default archives
        build(c, sdist=sdist, wheel=wheel, directory=tmp)
        # Build opposing interpreter archive, if necessary
        if dual_wheels:
            if not alt_python:
                alt_python = 'python2'
                if sys.version_info[0] == 2:
                    alt_python = 'python3'
            build(c, sdist=False, wheel=True, directory=tmp, python=alt_python)
        # Obtain list of archive filenames, then ensure any wheels come first
        # so their improved metadata is what PyPI sees initially (otherwise, it
        # only honors the sdist's lesser data).
        archives = list(itertools.chain.from_iterable(
            glob(os.path.join(tmp, 'dist', '*.{0}'.format(extension)))
            for extension in ('whl', 'tar.gz')
        ))
        # Sign each archive in turn
        # TODO: twine has a --sign option; but the below is still nice insofar
        # as it lets us dry-run, generate for web upload when pypi's API is
        # being cranky, etc. Figure out which is better.
        if sign:
            prompt = "Please enter GPG passphrase for signing: "
            input_ = StringIO(getpass.getpass(prompt) + "\n")
            gpg_bin = find_gpg(c)
            if not gpg_bin:
                sys.exit("You need to have one of `gpg`, `gpg1` or `gpg2` installed to GPG-sign!") # noqa
            for archive in archives:
                cmd = "{0} --detach-sign -a --passphrase-fd 0 {{0}}".format(gpg_bin) # noqa
                c.run(cmd.format(archive), in_stream=input_)
                input_.seek(0) # So it can be replayed by subsequent iterations
        # Upload
        parts = ["twine", "upload"]
        if index:
            index_arg = "-r {0}".format(index)
        if index:
            parts.append(index_arg)
        paths = archives + [os.path.join(tmp, 'dist', "*.asc")]
        parts.extend(paths)
        cmd = " ".join(parts)
        if dry_run:
            print("Would publish via: {0}".format(cmd))
            print("Files that would be published:")
            c.run("ls -l {0}".format(" ".join(paths)))
        else:
            c.run(cmd)


release = Collection('release')#,
#    build,
#    changelog,
#    #dry_run,
#    publish,
#    push,
#    should_changelog,
#    should_version,
#    tag,
#    version,
#)
# TODO: why are we doing this this way exactly? Issues when importing it into
# external namespaces? Feels bad.
# TODO: even if this is somehow necessary, it should ride on top of the
# "generate collection from this module" feature and then just rename 'all' or
# whatever.
release.add_task(all_, default=True)
# Hide stdout by default, preferring to explicitly enable it when necessary.
release.configure({'run': {'hide': 'stdout'}})
