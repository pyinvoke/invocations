"""
Tasks intended for use under Travis-CI, as opposed to run by humans.

To run these, you probably need to define some or all of the following
somewhere in your config setup:

- ``travis.sudo.user``: A username to create & grant passworded sudo to.
- ``travis.sudo.password``: Their password.
"""

import os

from invoke import task

from .packaging.release import publish


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
    cmd = "source $VIRTUAL_ENV/bin/activate && inv coverage"
    c.sudo('bash -c "{0}"'.format(cmd), user=c.travis.sudo.user)


@task
def test_installation(c, package, sanity):
    """
    Test a non-editable pip install of source checkout.

    Catches high level setup.py bugs.

    :param str package: Package name to uninstall.
    :param str sanity: Sanity-check command string to run.
    """
    c.run("pip uninstall -y {0}".format(package))
    c.run("pip install .")
    if sanity:
        c.run(sanity)
    # TODO: merge with test_packaging below somehow, e.g. a subroutine


@task
def test_packaging(c, package, sanity, alt_python=None):
    """
    Execute a wipe-build-install-test cycle for a given packaging config.

    Ideally, tests everything but actual upload to package index.

    When possible, leverages in-process calls to other packaging tasks.

    :param str package: Package name to uninstall before testing installation.
    :param str sanity: Sanity-check command string to run.
    :param str alt_python:
        Path to alternate virtualenv's Python interpreter. If given, will also
        enable a "2 vs 3" mode during wheel installation testing, which will
        select only the interpreter-family-appropriate wheel (going by
        ``$TRAVIS_PYTHON_VERSION``.)
    """
    # Use an explicit directory for building so we can reference after
    path = 'tmp'
    # Echo on please
    c.config.run.echo = True
    # Ensure no GPG signing is attempted.
    c.packaging.sign = False
    # Publish in dry-run context, to explicit (non-tmp) directory.
    publish(c, dry_run=True, directory=path, alt_python=alt_python)
    # Various permutations of nuke->install->sanity test, as needed
    # TODO: normalize sdist so it's actually a config option, rn is kwarg-only
    globs = ['*.tar.gz']
    if c.packaging.wheel:
        if alt_python:
            # TODO: the original .travis.yml was structured with logic this
            # way; I don't recall if it was purposeful or if an 'if/else' would
            # suffice instead.
            travis_ver = os.environ['TRAVIS_PYTHON_VERSION']
            if travis_ver.startswith('3') or travis_ver == 'pypy3':
                globs.append('*py3*.whl')
            if travis_ver.startswith('2') or travis_ver == 'pypy':
                globs.append('*py2*.whl')
        else:
            globs.append('*.whl')
    for glob in globs:
        c.run("pip uninstall -y {0}".format(package), warn=True)
        c.run("pip install tmp/dist/{0}".format(glob))
        c.run(sanity)
