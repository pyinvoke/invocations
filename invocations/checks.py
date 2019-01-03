"""
Tasks for common project sanity-checking such as linting or type checking.

.. versionadded:: 1.2
"""

from __future__ import unicode_literals

from invoke import task


@task(name="blacken", iterable=["folders"])
def blacken(
    c, line_length=79, folders=None, check=False, diff=False, find_opts=None
):
    r"""
    Run black on the current source tree (all ``.py`` files).

    .. warning::
        ``black`` only runs on Python 3.6 or above. (However, it can be
        executed against Python 2 compatible code.)

    :param int line_length:
        Line length argument. Default: ``79``.
    :param list folders:
        List of folders (or, on the CLI, an argument that can be given N times)
        to search within for ``.py`` files. Default: ``["."]``. Honors the
        ``blacken.folders`` config option.
    :param bool check:
        Whether to run ``black --check``. Default: ``False``.
    :param bool diff:
        Whether to run ``black --diff``. Default: ``False``.
    :param str find_opts:
        Extra option string appended to the end of the internal ``find``
        command. For example, skip a vendor directory with ``"-and -not -path
        ./vendor\*"``, add ``-mtime N``, or etc. Honors the
        ``blacken.find_opts`` config option.

    .. versionadded:: 1.2
    .. versionchanged:: 1.4
        Added the ``find_opts`` argument.
    """
    config = c.config.get("blacken", {})
    default_folders = ["."]
    configured_folders = config.get("folders", default_folders)
    folders = folders or configured_folders

    default_find_opts = ""
    configured_find_opts = config.get("find_opts", default_find_opts)
    find_opts = find_opts or configured_find_opts

    black_command_line = "black -l {}".format(line_length)
    if check:
        black_command_line = "{} --check".format(black_command_line)
    if diff:
        black_command_line = "{} --diff".format(black_command_line)
    if find_opts:
        find_opts = " {}".format(find_opts)
    else:
        find_opts = ""

    cmd = "find {} -name '*.py'{} | xargs {}".format(
        " ".join(folders), find_opts, black_command_line
    )
    c.run(cmd, pty=True)
