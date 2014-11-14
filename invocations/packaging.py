from glob import glob
import os
from shutil import rmtree, copy, copytree
from tempfile import mkdtemp

from invoke import ctask as task, Collection


def unpack(c, tmp, package, version, git_url=None):
    """
    Download + unpack given package into temp dir ``tmp``.

    Return ``(real_version, source)`` where ``real_version`` is the "actual"
    version downloaded (e.g. if a Git master was indicated, it will be the SHA
    of master HEAD) and ``source`` is the source directory (relative to
    unpacked source) to import into ``<project>/vendor``.
    """
    real_version = version[:]
    source = None
    if git_url:
        pass
    #   git clone into tempdir
    #   git checkout <version>
    #   set target to checkout
    #   if version does not look SHA-ish:
    #       in the checkout, obtain SHA from that branch
    #       set real_version to that value
    else:
        cwd = os.getcwd()
        print("Moving into temp dir %s" % tmp)
        os.chdir(tmp)
        try:
            # Nab from index
            flags = "--download-cache= --download=. --build=build"
            cmd = "pip install %s %s==%s" % (flags, package, version)
            c.run(cmd)
            # Identify basename
            # TODO: glob is bad here because pip install --download gets all
            # dependencies too! ugh.
            zipfile = os.path.basename(glob("*.zip")[0])
            source = os.path.splitext(zipfile)[0]
            # Unzip
            c.run("unzip *.zip")
        finally:
            os.chdir(cwd)
    return real_version, source


@task
def vendorize(c, distribution, version, vendor_dir, package=None,
    git_url=None, license=None):
    """
    Vendorize Python package ``distribution`` at version/SHA ``version``.

    Specify the vendor folder (e.g. ``<mypackage>/vendor``) as ``vendor_dir``.

    For Crate/PyPI releases, ``package`` should be the name of the software
    entry on those sites, and ``version`` should be a specific version number.
    E.g. ``vendorize('lexicon', '0.1.2')``.

    For Git releases, ``package`` should be the name of the package folder
    within the checkout that needs to be vendorized and ``version`` should be a
    Git identifier (branch, tag, SHA etc.) ``git_url`` must also be given,
    something suitable for ``git clone <git_url>``.

    For SVN releases: xxx.

    For packages where the distribution name is not the same as the package
    directory name, give ``package='name'``.

    By default, no explicit license seeking is done -- we assume the license
    info is in file headers or otherwise within the Python package vendorized.
    This is not always true; specify ``license=/path/to/license/file`` to
    trigger copying of a license into the vendored folder from the
    checkout/download (relative to its root.)
    """
    tmp = mkdtemp()
    package = package or distribution
    target = os.path.join(vendor_dir, package)
    try:
        # Unpack source
        real_version, source = unpack(c, tmp, distribution, version, git_url)
        abs_source = os.path.join(tmp, source)
        source_package = os.path.join(abs_source, package)
        # Ensure source package exists
        if not os.path.exists(source_package):
            rel_package = os.path.join(source, package)
            raise ValueError("Source package %s doesn't exist!" % rel_package)
        # Nuke target if exists
        if os.path.exists(target):
            print("Removing pre-existing vendorized folder %s" % target)
            rmtree(target)
        # Perform the copy
        print("Copying %s => %s" % (source_package, target))
        copytree(source_package, target)
        # Explicit license if needed
        if license:
            copy(os.path.join(abs_source, license), target)
        # git commit -a -m "Update $package to $version ($real_version if different)"
    finally:
        rmtree(tmp)


@task(name='all')
def all_(c):
    """
    Catchall version-bump/tag/changelog/PyPI upload task.
    """


@task
def changelog(c, target='docs/changelog.rst'):
    """
    Update changelog with new release entry.
    """
    pass


@task
def version(c):
    """
    Update stored project version (e.g. a ``_version.py``.)

    Requires configuration to be effective (since version file is usually kept
    within a project-named directory.
    """
    pass


@task
def tag(c):
    """
    Create a release tag.

    May set a config option for a prefix, e.g. 'v1.0.0' vs just '1.0.0'. This
    is unset/blank by default.
    """
    pass


@task
def push(c):
    """
    Push tag/changelog/version changes to Git origin.
    """
    # TODO: or should this be distributed amongst the appropriate tasks?
    pass


@task
def publish(c, wheel=False):
    """
    Publish code to PyPI.
    """
    # TODO: Use twine.
    parts = ["python", "setup.py", "sdist"]
    if wheel:
        parts.append("bdist_wheel")
    parts.append("register")
    parts.append("upload")
    c.run(" ".join(parts))


release = Collection('release', changelog, version, tag, push)
release.add_task(all_, default=True)
