"""
Tasks for importing external code into a vendor subdirectory.
"""
from os import chdir
from pathlib import Path
from shutil import copy, copytree, rmtree

from invoke import task

from ..util import tmpdir


def _unpack(c, tmp, package, version, git_url=None):
    """
    Download + unpack given package into temp dir ``tmp``.

    Return ``(real_version, source)`` where ``real_version`` is the "actual"
    version downloaded (e.g. if a Git main branch was indicated, it will be the
    SHA of ``main`` HEAD) and ``source`` is the source directory (relative to
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
        cwd = Path.cwd()
        print(f"Moving into temp dir {tmp}")
        chdir(tmp)
        try:
            # Nab from index. Skip wheels; we want to unpack an sdist.
            flags = "--download=. --build=build --no-use-wheel"
            cmd = f"pip install {flags} {package}=={version}"
            c.run(cmd)
            # Identify basename
            # TODO: glob is bad here because pip install --download gets all
            # dependencies too! ugh. Figure out best approach for that.
            globs = []
            globexpr = ""
            for extension, opener in (
                ("zip", "unzip"),
                ("tgz", "tar xzvf"),
                ("tar.gz", "tar xzvf"),
            ):
                globexpr = "*.{}".format(extension)
                globs = cwd.glob(globexpr)
                if globs:
                    break
            archive = globs[0].name
            # TODO: weird how there's no "mega-.stem" in Pathlib, o well
            source, _, _ = archive.rpartition(".{}".format(extension))
            c.run("{} {}".format(opener, globexpr))
        finally:
            chdir(cwd)
    return real_version, source


@task
def vendorize(
    c,
    distribution,
    version,
    vendor_dir,
    package=None,
    git_url=None,
    license=None,
):
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
    with tmpdir() as tmp:
        package = package or distribution
        target = Path(vendor_dir) / package
        # Unpack source
        real_version, source = _unpack(c, tmp, distribution, version, git_url)
        abs_source = tmp / source
        source_package = abs_source / package
        # Ensure source package exists
        if not source_package.exists():
            rel_package = source_package.relative_to(Path.cwd())
            raise ValueError(f"Source package {rel_package} doesn't exist!")
        # Nuke target if exists
        if target.exists():
            print(f"Removing pre-existing vendorized folder {target}")
            rmtree(target)
        # Perform the copy
        print(f"Copying {source_package} => {target}")
        copytree(source_package, target)
        # Explicit license if needed
        if license:
            copy(abs_source / license, target)
        # git commit -a -m "Update $package to $version ($real_version if different)" # noqa
