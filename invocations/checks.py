"""
Shortcuts for common development check tasks
"""

from __future__ import unicode_literals

from invoke import task

@task(name='blacken', iterable=['folder'])
def blacken(c, line_length=79, folder=None):
    """Run black on the current source"""

    folders = ['.'] if not folder else folder

    black_command_line = "black -l {0}".format(line_length)
    cmd = "find {0} -name '*.py' | xargs {1}".format(
        " ".join(folders), black_command_line
    )
    c.run(cmd, pty=True)
