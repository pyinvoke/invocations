=========
Changelog
=========

- :feature:`-` Break out a generic form of the ``travis.sudo-coverage`` task
  into ``travis.sudo-run``, then build on that to create
  ``travis.sudo-integration`` which runs the integration suite.
- :feature:`-` Add 'missing' arguments to ``pytest.integration`` so its
  signature now largely matches ``pytest.test``, which it wraps.
- :feature:`-` Add the ``checks`` module, containing ``checks.blacken`` which
  executes the `black <https://github.com/ambv/black>`_ code formatter
- :release:`1.1.0 <2018-05-14>`
- :feature:`-` Split out the body of the (sadly incomplete)
  ``packaging.release.all`` task into the better-named
  ``packaging.release.prepare``. (``all`` continues to behave as it did, it
  just now calls ``prepare`` explicitly.)
- :release:`1.0.0 <2018-05-08>`
- :feature:`-` Pre-history / code primarily for internal consumption
