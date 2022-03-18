"""
Tasks intended for use under continuous integration.

Presently, this tends to assume CircleCI, but it is intended to be generic &
we'll accept patches to make any Circle-isms configurable.

Most of it involves setting up to run a test suite under a special user who is
allowed to run ``sudo`` and who also needs a password to do so. This allows
testing sudo-related functionality which would otherwise suffer
false-positives, since most CI environments allow passwordless sudo for the
default user.

Thus, the pattern is:

- use that default user's sudo privileges to generate the special user (if they
  don't already exist in the image)
- as the default user, execute the test suite runner via ``sudo -u <user>``
- the test suite will then at times run its own ``sudo someprogram`` & be
  prompted for its password (which the test suite should read from the config
  data, same as this outer set of tasks does).

.. note::
    This module defines default values for the ``ci.sudo`` config subtree, but
    if you're using an execution environment where the default sudoers group
    isn't ``sudo`` (eg ``wheel``) you'll want to override ``ci.sudo.group`` in
    your own config files.
"""

from invoke import task, Collection


@task
def make_sudouser(c):
    """
    Create a passworded sudo-capable user.

    Used by other tasks to execute the test suite so sudo tests work.
    """
    user = c.ci.sudo.user
    password = c.ci.sudo.password
    groups = c.ci.sudo.groups
    # "--create-home" because we need a place to put conf files, keys etc
    # "--groups xxx" for (non-passwordless) sudo access, eg 'sudo' group on
    # Debian, plus any others, eg shared group membership with regular user for
    # writing out artifact files (assuming $HOME is g+w, which it is on Circle)
    c.sudo(
        "useradd {} --create-home --groups {}".format(user, ",".join(groups))
    )
    # Password set noninteractively via chpasswd (assumes invoking user itself
    # is able to passwordless sudo; this is true on CircleCI)
    c.run("echo {}:{} | sudo chpasswd".format(user, password))


@task
def sudo_run(c, command):
    """
    Run some command under CI-oriented sudo subshell/virtualenv.

    :param str command:
        Command string to run, e.g. ``inv coverage``, ``inv integration``, etc.
        (Does not necessarily need to be an Invoke task, but...)
    """
    # NOTE: due to circle sudoers config, circleci user can't do "sudo -u" w/o
    # password prompt. However, 'sudo su' seems to work just as well...
    # NOTE: well. provided you do this really asinine PATH preservation to work
    # around su's path resetting. no, --preserve-environment doesn't work, even
    # if you have --preserve-environment=PATH on the outer 'sudo' (which does
    # work for what sudo directly calls)
    # TODO: may want to rub --pty on the 'su' but so far seems irrelevant
    c.run(
        'sudo su {} -c "export PATH=$PATH && {}"'.format(
            c.ci.sudo.user, command
        )
    )


ns = Collection(make_sudouser, sudo_run)
ns.configure(
    {
        "ci": {
            "sudo": {
                "user": "invoker",
                "password": "secret",
                "groups": ["sudo", "circleci"],
            }
        }
    }
)
