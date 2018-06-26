"""
Tasks for common project sanity-checking such as linting or type checking.

.. versionadded:: 1.2
"""

from __future__ import unicode_literals

from invoke import task


@task(name="blacken", iterable=["folder"])
def blacken(
    c, line_length=79, folder=None, check=False, diff=False, find_opts=None
):
    """
    Run black on the current source tree (all ``.py`` files).

    .. warning::
        ``black`` only runs on Python 3.6 or above. (However, it can be
        executed against Python 2 compatible code.)

    :param int line_length:
        Line length argument. Default: ``79``.
    :param str folder:
        Folder(s) to search within for ``.py`` files. May be given multiple
        times to search N folders. Default: ``["."]``. Honors the
        ``blacken.folders`` config option.
    :param bool check:
        Whether to run ``black --check``. Default: ``False``.
    :param bool diff:
        Whether to run ``black --diff``. Default: ``False``.
    :param str find_opts:
        Extra option string appended to the end of the internal ``find``
        command. For example, skip a vendor directory with ``"-and -not -path
        ./vendor\*"``, add ``-mtime N``, or etc.

    .. versionadded:: 1.2
    .. versionchanged:: 1.4
        Added the ``find_opts`` argument.
    """
    default_folders = ["."]
    configured_folders = c.config.get("blacken", {}).get(
        "folders", default_folders
    )
    folders = configured_folders if not folder else folder

    black_command_line = "black -l {}".format(line_length)
    if check:
        black_command_line = "{} --check".format(black_command_line)
    if diff:
        black_command_line = "{} --diff".format(black_command_line)
    if find_opts is not None:
        find_opts = " {}".format(find_opts)
    else:
        find_opts = ""

    cmd = "find {} -name '*.py'{} | xargs {}".format(
        " ".join(folders), find_opts, black_command_line
    )
    c.run(cmd, pty=True)
