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
    :target: https://pypi.org/project/hexrec/

.. |commits-since| image:: https://img.shields.io/github/commits-since/TexZK/hexrec/v0.0.2.svg
    :alt: Commits since latest release
    :target: https://github.com/TexZK/hexrec/compare/v0.0.2...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/hexrec.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/hexrec/

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hexrec.svg
    :alt: Supported versions
    :target: https://pypi.org/project/hexrec/

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hexrec.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/hexrec/


.. end-badges

Library to handle hexadecimal record files

* Free software: BSD 2-Clause License


Installation
============

From PIP::

    pip install hexrec

From source::

    python setup.py install


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
