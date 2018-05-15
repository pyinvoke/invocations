=========
Changelog
=========

- :feature:`-` Add ``-x`` and ``-k`` flags to ``pytest.integration`` to match
  ``pytest.test`` (they're simple passthroughs).
- :feature:`-` Add the ``checks`` module, containing ``checks.blacken`` which
  executes the `black <https://github.com/ambv/black>`_ code formatter
- :release:`1.1.0 <2018-05-14>`
- :feature:`-` Split out the body of the (sadly incomplete)
  ``packaging.release.all`` task into the better-named
  ``packaging.release.prepare``. (``all`` continues to behave as it did, it
  just now calls ``prepare`` explicitly.)
- :release:`1.0.0 <2018-05-08>`
- :feature:`-` Pre-history / code primarily for internal consumption
