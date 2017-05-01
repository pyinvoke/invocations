"""
Tasks intended for use under Travis-CI, as opposed to run by humans.

.. note::
    Where possible, other tasks such as in the ``testing`` submodule include
    Travis detection & options inline; this module is specifically for
    automating command execution that would otherwise live at the top level in
    a ``.travis.yml`` (such as running things under ``sudo``.)
"""

from invoke import task


# TODO: does it make any sense to store these in a config and try using that to
# communicate with the tests that consume these values? For now harcoding is
# fine, but.
USER = 'sudouser'
PASSWD = 'mypass'


@task
def make_sudouser(c):
    """
    Create a passworded sudo-capable user.

    Used by other tasks to execute the test suite so sudo tests work.
    """
    # --create-home because we need a place to put conf files, keys etc
    # --groups travis because we must be in the Travis group to access the
    # (created by Travis for us) virtualenv and other contents within
    # /home/travis.
    c.sudo("useradd {0} --create-home --groups travis".format(USER))
    # Password 'mypass' also arbitrary
    c.run("echo {0}:{1} | sudo chpasswd".format(USER, PASSWD))
    # Set up new (glob-sourced) sudoers conf file for our user; easier than
    # attempting to mutate or overwrite main sudoers conf.
    conf = "/etc/sudoers.d/passworded"
    c.sudo("echo '{0}   ALL=(ALL:ALL) PASSWD:ALL' > {1}".format(USER, conf))
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
    c.sudo('ssh-keygen -f ~/.ssh/id_rsa -N ""', user=USER)
    c.sudo('cp ~/.ssh/{id_rsa.pub,authorized_keys}', user=USER)
