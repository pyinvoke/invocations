"""
Tasks intended for use under Travis-CI, as opposed to run by humans.

To run these, you probably need to define some or all of the following
somewhere in your config setup:

- ``travis.sudo.user``: A username to create & grant passworded sudo to.
- ``travis.sudo.password``: Their password.
"""

from __future__ import print_function

import os
import sys

from invoke import task

from .packaging.release import publish
from . import checks


PYTHON = os.environ.get("TRAVIS_PYTHON_VERSION", "")


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
    c.sudo("useradd {} --create-home --groups travis".format(user))
    # Password 'mypass' also arbitrary
    c.run("echo {}:{} | sudo chpasswd".format(user, password))
    # Set up new (glob-sourced) sudoers conf file for our user; easier than
    # attempting to mutate or overwrite main sudoers conf.
    conf = "/etc/sudoers.d/passworded"
    cmd = "echo '{}   ALL=(ALL:ALL) PASSWD:ALL' > {}".format(user, conf)
    c.sudo('sh -c "{}"'.format(cmd))
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
    home = "~{}".format(user)
    # Run sudo() as the new sudo user; means less chown'ing, etc.
    c.config.sudo.user = user
    ssh_dir = "{}/.ssh".format(home)
    # TODO: worth wrapping in 'sh -c' and using '&&' instead of doing this?
    # TODO: uhh isn't this fucking broken
    for cmd in ("mkdir {0}", "chmod 0700 {0}"):
        c.sudo(cmd.format(ssh_dir, user))
    c.sudo('ssh-keygen -f {}/id_rsa -N ""'.format(ssh_dir))
    c.sudo("cp {}/{{id_rsa.pub,authorized_keys}}".format(ssh_dir))


@task
def sudo_run(c, command):
    """
    Run some command under Travis-oriented sudo subshell/virtualenv.

    :param str command:
        Command string to run, e.g. ``inv coverage``, ``inv integration``, etc.
        (Does not necessarily need to be an Invoke task, but...)
    """
    # NOTE: explicit shell wrapper because sourcing the venv works best here;
    # test tasks currently use their own subshell to call e.g. 'pytest --blah',
    # so the tactic of '$VIRTUAL_ENV/bin/inv coverage' doesn't help - only that
    # intermediate process knows about the venv!
    cmd = "source $VIRTUAL_ENV/bin/activate && {}".format(command)
    c.sudo('bash -c "{}"'.format(cmd), user=c.travis.sudo.user)


@task
def sudo_coverage(c):
    """
    Execute the local ``coverage`` task as the configured Travis sudo user.

    Ensures the virtualenv is sourced and that coverage is run in a mode
    suitable for headless/API consumtion (e.g. no HTML report, etc.)
    """
    # TODO: deprecate in favor of just using sudo-run
    sudo_run(c, command="inv coverage")


@task
def test_installation(c, package, sanity):
    """
    Test a non-editable pip install of source checkout.

    Catches high level setup.py bugs.

    :param str package: Package name to uninstall.
    :param str sanity: Sanity-check command string to run.
    """
    c.run("pip uninstall -y {}".format(package))
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
    path = "tmp"
    # Echo on please
    c.config.run.echo = True
    # Ensure no GPG signing is attempted.
    c.packaging.sign = False
    # Publish in dry-run context, to explicit (non-tmp) directory.
    publish(c, dry_run=True, directory=path, alt_python=alt_python)
    # Various permutations of nuke->install->sanity test, as needed
    # TODO: normalize sdist so it's actually a config option, rn is kwarg-only
    globs = ["*.tar.gz"]
    if c.packaging.wheel:
        if alt_python:
            # TODO: the original .travis.yml was structured with logic this
            # way; I don't recall if it was purposeful or if an 'if/else' would
            # suffice instead.
            # TODO: shouldn't we just be able to use internal Python hints
            # about this now anyways (eg `sys.version`)? Will that work for
            # pypy and pypy3?
            if PYTHON.startswith("3") or PYTHON == "pypy3":
                globs.append("*py3*.whl")
            if PYTHON.startswith("2") or PYTHON == "pypy":
                globs.append("*py2*.whl")
        else:
            globs.append("*.whl")
    for glob in globs:
        c.run("pip uninstall -y {}".format(package), warn=True)
        c.run("pip install tmp/dist/{}".format(glob))
        c.run(sanity)


@task
def blacken(c):
    """
    Install and execute ``black`` under appropriate circumstances, with diffs.

    Installs and runs ``black`` under Python 3.6 (the first version it
    supports). Since this sort of CI based task only needs to run once per
    commit (formatting is not going to change between interpreters) this seems
    like a worthwhile tradeoff.

    This task uses black's ``--check`` and ``--fail`` flags, so not only will
    the build fail if it does not conform, but contributors can see exactly
    what they need to change. This is intended as a hedge against the fact that
    not all contributors will be using Python 3.6+.
    """
    if not PYTHON.startswith("3.6"):
        msg = "Not blackening, since Python {} != Python 3.6".format(PYTHON)
        print(msg, file=sys.stderr)
        return
    # Install, allowing config override of hardcoded default version
    config = c.config.get("travis", {}).get("black", {})
    version = config.get("version", "18.5b0")
    c.run("pip install black=={}".format(version))
    # Execute our blacken task, with diff + check, which will both error
    # and emit diffs.
    checks.blacken(c, check=True, diff=True)
