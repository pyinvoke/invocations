=========
Changelog
=========

- :release:`1.0.1 <2018-06-26>`
- :bug:`-` Was missing a 'hide output' flag on a subprocess shell call, the
  result of which was mystery git branch names appearing in the output of
  ``inv release`` and friends. Fixed now.
- :support:`- backported` Remove some apparently non-functional ``setup.py``
  logic around conditionally requiring ``enum34``; it was never getting
  selected and thus breaking a couple modules that relied on it.

  ``enum34`` is now a hard requirement like the other
  semi-optional-but-not-really requirements.
- :release:`1.1.0 <2018-05-14>`
- :feature:`-` Split out the body of the (sadly incomplete)
  ``packaging.release.all`` task into the better-named
  ``packaging.release.prepare``. (``all`` continues to behave as it did, it
  just now calls ``prepare`` explicitly.)
- :release:`1.0.0 <2018-05-08>`
- :feature:`-` Pre-history / code primarily for internal consumption
