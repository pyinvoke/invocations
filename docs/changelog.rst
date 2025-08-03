=========
Changelog
=========

- :release:`4.0.0 <2025-08-03>`
- :support:`-` Add a ``__version__`` member to the package root module.
- :support:`-` Drop support for Python<3.9 and switch to using pyproject.toml.
- :support:`-` Update ``packaging.release.build`` to use ``pypa/build`` instead
  of ``setup.py``.

  .. warning::
      Backwards compatibility note: the ``--directory`` argument to tasks in
      this module is now ~= ``python -m build --outdir``, meaning it controls
      what is usually named ``dist/``.

      Previously, this option controlled a parent directory, *inside of which*
      was created ``dist/`` and ``build/``. There's no longer any explicit
      ``build/`` (that would be up to your project's build backend) and so this
      is now simply the dist/output dir.

- :support:`-` Mute SyntaxWarnings from older ``semantic_version`` versions
  (temporary measure until we can upgrade to modern versions).
- :release:`3.3.0 <2023-05-12>`
- :feature:`-` Add mypy type-checking variant of the recently added import
  test, in ``packaging.release.test_install``. This helps prove packages
  exposing ``py.typed`` in their source tree are including it in their
  distributions correctly.
- :release:`3.2.0 <2023-05-11>`
- :feature:`-` Minor enhancements to the ``checks`` module:

    - ``blacken`` now has a ``format`` alias (and will likely reverse the real
      name and the alias in 4.0)
    - Added ``lint`` task which currently just runs ``flake8``, will likely
      learn how to be configurable later.
    - Added ``all_`` default task for the collection, which runs both
      ``blacken`` (in regular, not diff-only mode - idea is to be useful for
      devs, not CI, which already does both independently) and ``lint`` in
      series.

- :release:`3.1.0 <2023-05-02>`
- :feature:`-` Updated ``packaging.release.test_install`` to attempt imports of
  freshly test-installed packages, to catch import-time errors on top of
  install-time ones. This can be opted out of by giving the ``skip_import``
  kwarg (aka the ``--skip-import`` flag on the CLI).
- :release:`3.0.2 <2023-04-28>`
- :support:`- backported` Unpin ``tabulate`` in our install requirements, it's
  had many more releases since we instituted a defensive pin vs some bugs in
  its later 0.7 line!
- :release:`3.0.1 <2023-01-06>`
- :bug:`-` We neglected to remove references to ``six`` in a few spots -
  including some that utilized Invoke's old vendor of same; this causes issues
  when trying to use development and upcoming versions of Invoke. Six is now
  truly gone!
- :release:`3.0.0 <2022-12-31>`
- :support:`-` Various fixes and doc updates re: the `~invocations.autodoc`
  module's compatibility with modern Sphinx versions.
- :support:`-` The ``dual_wheels``, ``alt_python``, and ``check_desc``
  arguments/config options for the ``invocations.packaging.release`` module
  have been removed.

  .. warning:: This is a backwards-incompatible change.

  .. note::
      If you were using ``check_desc``, note that the release tasks have been
      using ``twine check`` for a few releases now, as a default part of
      execution, and will continue doing so; ``check_desc`` only impacted the
      use of the older ``setup.py check`` command.

- :support:`-` The ``invocations.travis`` module has been removed. If you
  relied upon it, we may accept PRs to make the newer ``invocations.ci`` module
  more generic.

  .. warning:: This is a backwards-incompatible change.

- :support:`-` Drop Python 2 (and 3.5) support. We now support Python
  3.6+ only. This naturally includes a number of dependency updates (direct and
  indirect) as well.

  .. warning:: This is a backwards-incompatible change.

- :release:`2.6.1 <2022-06-26>`
- :support:`- backported` Remove upper bounds pinning on many deps; this makes
  it easier for related projects to test upgrades, run CI, etc. In general,
  we're moving away from this tactic.
- :release:`2.6.0 <2022-03-25>`
- :feature:`-` Enhance ``packaging.release.test-install`` so it's more flexible
  about the primary directory argument (re: a ``dist`` dir, or a parent of one)
  and errors usefully when you (probably) gave it an incorrect path.
- :feature:`-` Update ``packaging.release.publish`` with a new config option,
  ``rebuild_with_env``, to support a downstream (Fabric) release use-case.
- :release:`2.5.0 <2022-03-25>`
- :feature:`-` Port ``make-sshable`` from the ``travis`` module to the new
  ``ci`` one.
- :release:`2.4.0 <2022-03-17>`
- :feature:`-` Allow supplying additional test runners to ``pytest.coverage``;
  primarily useful for setting up multiple additive test runs before publishing
  reports.
- :feature:`-` Add a new `invocations.ci` task module for somewhat-more-generic
  CI support than the now legacy ``invocations.travis`` tasks.
- :feature:`-` Add additional CLI flags to the use of ``gpg`` when signing
  releases, to support headless passphrase entry. It was found that modern GPG
  versions require ``--batch`` and ``--pinentry-mode=loopback`` for
  ``--passphrase-fd`` to function correctly.
- :release:`2.3.0 <2021-09-24>`
- :bug:`- major` Ensure that the venv used for
  ``packaging.release.test_install`` has its ``pip`` upgraded to match the
  invoking interpreter's version of same; this avoids common pitfalls where the
  "inner" pip is a bundled-with-venv, much-older version incapable of modern
  package installations.
- :support:`-` Overhaul testing and release procedures to use CircleCI & modern
  Invocations.
- :bug:`- major` The ``packaging.release.upload`` task wasn't properly exposed
  externally, even though another task's docstring referenced it. Fixed.
- :release:`2.2.0 <2021-09-03>`
- :bug:`- major` ``packaging.release.status`` (and its use elsewhere, eg
  ``prepare``) didn't adequately reload the local project's version module
  during its second/final recheck; this causes that check to fail when said
  version was edited as part of a ``prepare`` run. It now force-reloads said
  version module.
- :feature:`-` ``packaging.release.push``, in dry-run mode, now dry-runs its
  ``git push`` subcommand -- meaning the subcommand itself is what is
  "dry-ran", instead of truly executing ``git push --dry-run`` -- when a CI
  environment is detected.

  - This prevents spurious errors when the git remote (eg Github) bails out on
    read-only authentication credentials, which is common within CI systems.
  - It's also just not very useful to dry-run a real git push within CI, since
    almost certainly the commands to generate git objects to get pushed will
    themselves not have truly run!

- :feature:`-` Added the ``invocations.environment`` module with top-level
  functions such as `~invocations.environment.in_ci`.
- :release:`2.1.0 <2021-08-27>`
- :feature:`-` Add ``packaging.release.test_install`` task and call it just
  prior to the final step in ``packaging.release.upload`` (so one doesn't
  upload packages which build OK but don't actually install OK).
- :feature:`-` Add Codecov support to ``pytest.coverage``.
- :support:`-` Rely on Invoke 1.6+ for some of its new features.
- :support:`-` ``packaging.release.prepare`` now runs its internal status check
  twice, once at the start (as before) and again at the end (to prove that the
  actions taken did in fact satisfy needs).
- :feature:`-` ``packaging.release.prepare`` grew a ``dry_run`` flag to match
  the rest of its friends.
- :bug:`- major` ``packaging.release.prepare`` now generates annotated Git tags
  instead of lightweight ones. This was a perplexing oversight (Git has always
  intended annotated tags to be used for release purposes) so we're considering
  it a bugfix instead of a backwards incompatible feature change.
- :feature:`-` The ``packaging.release.all_`` task has been expanded to
  actually do "ALL THE THINGS!!!", given a ``dry_run`` flag, and renamed on the
  CLI to ``all`` (no trailing underscore).
- :feature:`-` Add ``packaging.release.push`` for pushing Git objects as part
  of a release.
- :feature:`-` Added ``twine check`` (which validates packaging metadata's
  ``long_description``) as a pre-upload step within
  ``packaging.release.publish``.

  - This includes some tweaking of ``readme_renderer`` behavior (used
    internally by twine) so it correctly spots more malformed RST, as Sphinx
    does.

- :bug:`- major` ``packaging.release.publish`` missed a spot when it grew
  "kwargs beat configuration" behavior - the ``index`` kwarg still got
  overwritten by the config value, if defined. This has been fixed.
- :bug:`- major` Correctly test for ``html`` report type inside of
  ``pytest.coverage`` when deciding whether to run ``open`` at the end.
- :bug:`- major` ``pytest.coverage`` incorrectly concatenated its ``opts``
  argument to internal options; this has been fixed.
- :release:`2.0.0 <2021-01-24>`
- :support:`-` Drop Python 3.4 support. We didn't actually do anything to make
  the code not work on 3.4, but we've removed some 3.4 related runtime (and
  development) dependency limitations. Our CI will also no longer test on 3.4.

    .. warning:: This is technically a backwards incompatible change.

- :support:`12` Upgrade our packaging manifest so tests (also docs,
  requirements files, etc) are included in the distribution archives. Thanks to
  Tomáš Chvátal for the report.
- :support:`21` Only require ``enum34`` under Python 2 to prevent it clashing
  with the stdlib ``enum`` under Python 3. Credit: Alex Gaynor.
- :bug:`- major` ``release.build``'s ``--clean`` flag has been updated:

    - It now honors configuration like the other flags in this task,
      specifically ``packaging.clean``.
    - It now defaults to ``False`` (rationale: most build operations in the
      wild tend to assume no cleaning by default, so defaulting to the opposite
      was sometimes surprising).

      .. warning:: This is a backwards incompatible change.

    - When ``True``, it applies to both build and dist directories, instead of
      just build.

      .. warning:: This is a backwards incompatible change.

- :support:`-` Reverse the default value of ``release.build`` and
  ``release.publish``)'s ``wheel`` argument from ``False`` to ``True``.
  Included in this change is a new required runtime dependency on the ``wheel``
  package.

  Rationale: at this point in time, most users will be expecting wheels to be
  available, and not building wheels is likely to be the uncommon case.

  .. warning:: This is a backwards incompatible change.

- :bug:`- major` ``release.build`` and ``release.publish`` had bad
  kwargs-vs-config logic preventing flags such as ``--wheel`` or ``--python``
  from actually working (config defaults always won out, leading to silent
  ignoring of user input). This has been fixed; config will now only be honored
  unless the CLI appears to be overriding it.
- :support:`-` Replace some old Python 2.6-compatible syntax bits.
- :feature:`-` Add a ``warnings`` kwarg/flag to ``pytest.test``, allowing one
  to call it with ``--no-warnings`` as an inline 'alias' for pytest's own
  ``--disable-warnings`` flag.
- :bug:`- major` Fix minor display bug causing the ``pytest`` task module to
  append a trailing space to the invocation of pytest itself.
- :support:`-` Modify ``release`` task tree to look at ``main`` branches
  in addition to ``master`` ones, for "are we on a feature release line or a
  bugfix one?" calculations, etc.
- :release:`1.4.0 <2018-06-26>`
- :release:`1.3.1 <2018-06-26>`
- :release:`1.2.2 <2018-06-26>`
- :release:`1.1.1 <2018-06-26>`
- :release:`1.0.1 <2018-06-26>`
- :bug:`-` Was missing a 'hide output' flag on a subprocess shell call, the
  result of which was mystery git branch names appearing in the output of
  ``inv release`` and friends. Fixed now.
- :bug:`-` ``checks.blacken`` had a typo regarding its folder selection
  argument; the CLI/function arg was ``folder`` while the configuration value
  was ``folders`` (plural). It's been made consistent: the CLI/function
  argument is now ``folders``.
- :feature:`-` Add a ``find_opts`` argument to ``checks.blacken`` for improved
  control over what files get blackened.
- :release:`1.3.0 <2018-06-20>`
- :feature:`-` Bump Releases requirement up to 1.6 and leverage its new ability
  to load Sphinx extensions, in ``packaging.release.prepare`` (which parses
  Releases changelogs programmatically). Prior to this, projects which needed
  extensions to build their doctree would throw errors when using the
  ``packaging.release`` module.
- :release:`1.2.1 <2018-06-18>`
- :support:`- backported` Remove some apparently non-functional ``setup.py``
  logic around conditionally requiring ``enum34``; it was never getting
  selected and thus breaking a couple modules that relied on it.

  ``enum34`` is now a hard requirement like the other
  semi-optional-but-not-really requirements.
- :release:`1.2.0 <2018-05-22>`
- :feature:`-` Add ``travis.blacken`` which wraps the new ``checks.blacken``
  (in diff+check mode, for test output useful for users who cannot themselves
  simply run black) in addition to performing Travis-oriented Python version
  checks and pip installation.

  This is necessary to remove boilerplate around the fact that ``black`` is not
  even visible to Python versions less than 3.6.
- :feature:`-` Break out a generic form of the ``travis.sudo-coverage`` task
  into ``travis.sudo-run`` which can be used for arbitrary commands run under
  the ssh/sudo capable user generated by
  ``travis.make-sudouser``/``travis.make-sshable``.
- :feature:`-` Add 'missing' arguments to ``pytest.integration`` so its
  signature now largely matches ``pytest.test``, which it wraps.
- :feature:`-` Add the ``checks`` module, containing ``checks.blacken`` which
  executes the `black <https://github.com/ambv/black>`_ code formatter. Thanks
  to Chris Rose.
- :release:`1.1.0 <2018-05-14>`
- :feature:`-` Split out the body of the (sadly incomplete)
  ``packaging.release.all`` task into the better-named
  ``packaging.release.prepare``. (``all`` continues to behave as it did, it
  just now calls ``prepare`` explicitly.)
- :release:`1.0.0 <2018-05-08>`
- :feature:`-` Pre-history / code primarily for internal consumption
