=========
Changelog
=========

- :support:`- backported` Remove some apparently non-functional ``setup.py``
  logic around conditionally requiring ``enum34``; it was never getting
  selected and thus breaking a couple modules that relied on it.

  ``enum34`` is now a hard requirement like the other
  semi-optional-but-not-really requirements.
- :release:`1.0.0 <2018-05-08>`
- :feature:`-` Pre-history / code primarily for internal consumption
