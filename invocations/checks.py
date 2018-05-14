"""
Shortcuts for common development check tasks
"""

from __future__ import unicode_literals

from invoke import task


@task(name="blacken", iterable=["folder"])
def blacken(c, line_length=79, folder=None, check=False):
    """Run black on the current source"""

    default_folders = ["."]
    configured_folders = c.config.get("blacken", {}).get(
        "folders", default_folders
    )
    folders = configured_folders if not folder else folder

    black_command_line = "black -l {0}".format(line_length)
    if check:
        black_command_line = "{0} --check".format(black_command_line)

    cmd = "find {0} -name '*.py' | xargs {1}".format(
        " ".join(folders), black_command_line
    )
    c.run(cmd, pty=True)
