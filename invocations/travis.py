"""
Tasks intended for use under Travis-CI, as opposed to run by humans.

To run these, you probably need to define some or all of the following
somewhere in your config setup:

- ``travis.sudo.user``: A username to create & grant passworded sudo to.
- ``travis.sudo.password``: Their password.
"""

from invoke import task


@task
def make_sudouser(c):
    """
    Create a passworded sudo-capable user.

    Used by other tasks to execute the test suite so sudo tests work.
    """
    user = c.travis.sudo.user
    password = c.travis.sudo.password
    # --create-home because we need a place to put conf files, keys etc
    # --groups travis because we must be in the Travis group to access the
    # (created by Travis for us) virtualenv and other contents within
    # /home/travis.
    c.sudo("useradd {0} --create-home --groups travis".format(user))
    # Password 'mypass' also arbitrary
    c.run("echo {0}:{1} | sudo chpasswd".format(user, password))
    # Set up new (glob-sourced) sudoers conf file for our user; easier than
    # attempting to mutate or overwrite main sudoers conf.
    conf = "/etc/sudoers.d/passworded"
    cmd = "echo '{0}   ALL=(ALL:ALL) PASSWD:ALL' > {1}".format(user, conf)
    c.sudo("sh -c \"{0}\"".format(cmd))
    # Grant travis group write access to /home/travis as some integration tests
    # may try writing conf files there. (TODO: shouldn't running the tests via
    # 'sudo -H' mean that's no longer necessary?)
    c.sudo("chmod g+w /home/travis")


# TODO: good place to depend on make_sudouser but only if it doesn't seem to
# have been run already (not just in this session but ever)
@task
def make_sshable(c):
    """
    Set up passwordless SSH keypair & authorized_hosts access to localhost.
    """
    user = c.travis.sudo.user
    home = "~{0}".format(user)
    # Run sudo() as the new sudo user; means less chown'ing, etc.
    c.config.sudo.user = user
    ssh_dir = "{0}/.ssh".format(home)
    # TODO: worth wrapping in 'sh -c' and using '&&' instead of doing this?
    for cmd in ('mkdir {0}', 'chmod 0700 {0}'):
        c.sudo(cmd.format(ssh_dir, user))
    c.sudo('ssh-keygen -f {0}/id_rsa -N ""'.format(ssh_dir))
    c.sudo('cp {0}/{{id_rsa.pub,authorized_keys}}'.format(ssh_dir))


@task
def sudo_coverage(c):
    """
    Execute the local ``coverage`` task as the configured Travis sudo user.

    Ensures the virtualenv is sourced and that coverage is run in a mode
    suitable for headless/API consumtion (e.g. no HTML report, etc.)
    """
    # NOTE: explicit shell wrapper because sourcing the venv works best here;
    # test tasks currently use their own subshell to call e.g. 'spec --blah',
    # so the tactic of '$VIRTUAL_ENV/bin/inv coverage' doesn't help - only that
    # intermediate process knows about the venv!
    cmd = "source $VIRTUAL_ENV/bin/activate && inv coverage --no-html"
    c.sudo('bash -c "{0}"'.format(cmd), user=c.travis.sudo.user)


@task
def test_installation(c, package, sanity=None):
    """
    Test a non-editable pip install of source checkout.

    Catches high level setup.py bugs.

    :param str package:
        Package name to uninstall.

    :param str sanity:
        Sanity-check command string to run. Optional.

        If given, will be appended to ``$VIRTUAL_ENV/bin/`` so it runs in the
        Travis test virtualenv.
    """
    c.run("echo echoing VIRTUAL_ENV: $VIRTUAL_ENV")
    pip = "$VIRTUAL_ENV/bin/pip"
    c.run("{0} uninstall -y {1}".format(pip, package))
    c.run("{0} install .".format(pip))
    if sanity:
        c.run("$VIRTUAL_ENV/bin/{0}".format(sanity))
