"""
Tasks for common project sanity-checking such as linting or type checking.
"""

from __future__ import unicode_literals

from invoke import task


@task(name="blacken", iterable=["folder"])
def blacken(c, line_length=79, folder=None, check=False):
    """
    Run black on the current source tree (all ``.py`` files).

    .. warning::
        ``black`` only runs on Python 3.6 or above. (However, it can be
        executed against Python 2 compatible code.)
    """
    default_folders = ["."]
    configured_folders = c.config.get("blacken", {}).get(
        "folders", default_folders
    )
    folders = configured_folders if not folder else folder

    black_command_line = "black -l {}".format(line_length)
    if check:
        black_command_line = "{} --check".format(black_command_line)

    cmd = "find {} -name '*.py' | xargs {}".format(
        " ".join(folders), black_command_line
    )
    c.run(cmd, pty=True)
