from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp


@contextmanager
def tmpdir(skip_cleanup=False, explicit=None):
    """
    Context-manage a temporary directory.

    Can be given ``skip_cleanup`` to skip cleanup, and ``explicit`` to choose a
    specific location.

    (If both are given, this is basically not doing anything, but it allows
    code that normally requires a secure temporary directory to 'dry run'
    instead.)
    """
    tmp = explicit if explicit is not None else mkdtemp()
    try:
        yield tmp
    finally:
        if not skip_cleanup:
            rmtree(tmp)
