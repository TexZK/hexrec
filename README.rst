================
WORK IN PROGRESS
================

Author's notice
===============

** THIS REPOSITORY IS BEING CREATED IN MY SPARE TIME. I WILL REMOVE THIS NOTICE WHEN FULLY FUNCTIONAL. **

This is also my first true Python package, so I am still learning how to do it *The Right Way (TM)*.

I am figuring out how to configure all the stuff the mighty `cookiecutter-pylibrary <https://github.com/ionelmc/cookiecutter-pylibrary>`_ created for me.

TODO
====

Stuff to do to have a working repository:

#.  Write some tests for `pytest`.
#.  Configure and verify `tox`.
#.  Write the documentation for `sphinx`.
#.  Drop any current CLI (based on `argparse` and very rough) and add a CLI with `click`.
#.  Configure and verify `travis` and stuff
#.  Configure and verify `ReadTheDocs` and stuff
#.  Remove this stuff from the readme.
#.  Integrate with `PyPI`


========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/hexrec/badge/?style=flat
    :target: https://readthedocs.org/projects/hexrec
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/TexZK/hexrec.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/TexZK/hexrec

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/TexZK/hexrec?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/TexZK/hexrec

.. |requires| image:: https://requires.io/github/TexZK/hexrec/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/TexZK/hexrec/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/TexZK/hexrec/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/TexZK/hexrec

.. |version| image:: https://img.shields.io/pypi/v/hexrec.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/hexrec

.. |commits-since| image:: https://img.shields.io/github/commits-since/TexZK/hexrec/v0.0.1.svg
    :alt: Commits since latest release
    :target: https://github.com/TexZK/hexrec/compare/v0.0.1...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/hexrec.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/hexrec

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hexrec.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/hexrec

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hexrec.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/hexrec


.. end-badges

Library to handle hexadecimal record files

* Free software: BSD 2-Clause License

Installation
============

::

    pip install hexrec

Documentation
=============

https://hexrec.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
