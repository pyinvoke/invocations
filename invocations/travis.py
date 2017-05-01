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
    c.sudo('ssh-keygen -f ~/.ssh/id_rsa -N ""', user=user)
    c.sudo('cp ~/.ssh/{id_rsa.pub,authorized_keys}', user=user)


@task
def sudo_coverage(c):
    """
    Execute the local ``coverage`` task as the configured Travis sudo user.

    Ensures the virtualenv is sourced and that coverage is run in a mode
    suitable for headless/API consumtion (e.g. no HTML report, etc.)
    """
    # TODO: do we need an explicit sh wrapper??
    # TODO: is workon available?
    cmd = "source $VIRTUAL_ENV/bin/activate && inv coverage --no-html"
    c.sudo(cmd, user=c.travis.sudo.user)
