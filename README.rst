|version| |python| |license| |ci| |coverage|

.. |version| image:: https://img.shields.io/pypi/v/invocations
    :target: https://pypi.org/project/invocations/
    :alt: PyPI - Package Version
.. |python| image:: https://img.shields.io/pypi/pyversions/invocations
    :target: https://pypi.org/project/invocations/
    :alt: PyPI - Python Version
.. |license| image:: https://img.shields.io/pypi/l/invocations
    :target: https://github.com/pyinvoke/invocations/blob/main/LICENSE
    :alt: PyPI - License
.. |ci| image:: https://img.shields.io/circleci/build/github/pyinvoke/invocations/main
    :target: https://app.circleci.com/pipelines/github/pyinvoke/invocations
    :alt: CircleCI
.. |coverage| image:: https://img.shields.io/codecov/c/gh/pyinvoke/invocations
    :target: https://app.codecov.io/gh/pyinvoke/invocations
    :alt: Codecov

What is this?
=============

Invocations is a collection of reusable `Invoke <http://pyinvoke.org>`_ tasks,
task collections and helper functions. Originally sourced from the Invoke
project's own project-management tasks file, they are now highly configurable
and used across a number of projects, with the intent to become a clearinghouse
for implementing common best practices.

Currently implemented topics include (but are not limited to):

- management of Sphinx documentation trees
- Python project release lifecycles
- dependency vendoring
- running test suites (unit, integration, coverage-oriented, etc)
- console utilities such as confirmation prompts

and more.

Roadmap
=======

While Invocations has been released with a major version number to signal
adherence to semantic versioning, it's somewhat early in development and has
not fully achieved its design vision yet.

We expect it to gain maturity in tandem with the adoption and development of
Invoke post-1.x. It's also highly likely that Invocations will see a few major
releases as its API (and those of its sister library, `patchwork
<https://fabric-patchwork.readthedocs.io>`_) matures.

For a high level roadmap re: when Invocations will get significant updates, see
the maintainer's `roadmap page <http://bitprophet.org/projects#roadmap>`_.

Development
===========

This project uses the same dev methodology as Invoke proper - please see its
development page `here <https://www.pyinvoke.org/development.html>`_.
