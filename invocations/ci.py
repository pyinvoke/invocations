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
    group = c.ci.sudo.group
    # "--create-home" because we need a place to put conf files, keys etc
    # "--groups xxx" for (non-passwordless) sudo access, eg 'sudo' group on
    # Debian.
    # TODO: may need circleci group for access to its homedir etc??
    c.sudo("useradd {} --create-home --groups {}".format(user, group))
    # Password set noninteractively via chpasswd (assumes invoking user itself
    # is able to passwordless sudo; this is true on CircleCI)
    c.run("echo {}:{} | sudo chpasswd".format(user, password))
    # TODO: nix below?
    # Grant travis group write access to /home/travis as some integration tests
    # may try writing conf files there. (TODO: shouldn't running the tests via
    # 'sudo -H' mean that's no longer necessary?)
    #c.sudo("chmod g+w /home/travis")


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
    c.run('sudo su {} -c "export PATH=$PATH && {}"'.format(c.ci.sudo.user, command))


# TODO: good place to depend on make_sudouser but only if it doesn't seem to
# have been run already (not just in this session but ever)
@task
def make_sshable(c):
    """
    Set up passwordless SSH keypair & authorized_hosts access to localhost.
    """
    user = c.ci.sudo.user
    home = "~{}".format(user)
    # Run sudo() as the new sudo user; means less chown'ing, etc.
    c.config.sudo.user = user
    ssh_dir = "{}/.ssh".format(home)
    # TODO: worth wrapping in 'sh -c' and using '&&' instead of doing this?
    for cmd in ("mkdir {0}", "chmod 0700 {0}"):
        c.sudo(cmd.format(ssh_dir, user))
    c.sudo('ssh-keygen -f {}/id_rsa -N ""'.format(ssh_dir))
    c.sudo("cp {}/{{id_rsa.pub,authorized_keys}}".format(ssh_dir))


ns = Collection(make_sudouser, sudo_run, make_sshable)
ns.configure({
    "ci": {
        "sudo": {
            "user": "invoker",
            "password": "secret",
            "group": "sudo",
        }
    }
})
