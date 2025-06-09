Changelog
=========

0.4.3 (2025-06-10)
------------------

* Added support for Python 3.13.
* Added support for Python 3.14.
* Building with ``setuptools >= 77.0.3``.


0.4.2 (2024-12-24)
------------------

* Improved loading from / saving to streams.
* ``hexrec.base.FILE_TYPES`` changed into lowercase ``file_types``.


0.4.1 (2024-10-05)
------------------

* Minor workflow and metadata updates.


0.4.0 (2024-03-08)
------------------

* Library rewritten from scratch (not backwards compatible).
* Added new object oriented API, hopefully more user friendly.
* Added *Texas Instruments TI-TXT* file format.
* Improved docs and examples.


0.3.1 (2024-01-23)
------------------

* Added support for Python 3.12.
* Added Motorola header editing.
* Minor fixes and changes.


0.3.0 (2023-02-21)
------------------

* Added support for Python 3.11, removed 3.6.
* Deprecated ``hexrec.blocks`` module entirely.
* Using ``bytesparse`` for virtual memory management.
* Improved repository layout.
* Improved testing and packaging workflow.
* Minor fixes and changes.


0.2.3 (2021-12-30)
------------------

* Removed dependency of legacy pathlib package; using Python's own module instead.
* Added support for Python 3.10.
* Fixed maximum SREC length.
* Changed pattern offset behavior.
* Some alignment to the ``bytesparse.Memory`` API; deprecated code marked as such.


0.2.2 (2020-11-08)
------------------

* Added workaround to register default record types.
* Added support for Python 3.9.
* Fixed insertion bug.
* Added empty space reservation.


0.2.1 (2020-03-05)
------------------

* Fixed flood with empty span.


0.2.0 (2020-02-01)
------------------

* Added support for current Python versions (3.8, PyPy 3).
* Removed support for old Python versions (< 3.6, PyPy 2).
* Major refactoring to allow an easier integration of new record formats.


0.1.0 (2019-08-13)
------------------

* Added support for Python 3.7.


0.0.4 (2018-12-22)
------------------

* New command line interface made with Click.
* More testing and fixing.
* Some refactoring.
* More documentation.


0.0.3 (2018-12-04)
------------------

* Much testing and fixing.
* Some refactoring.
* More documentation.


0.0.2 (2018-08-29)
------------------

* Major refactoring.
* Added most of the documentation.
* Added first drafts to manage blocks of data.
* Added first test suites.


0.0.1 (2018-06-27)
------------------

* First release on PyPI.
* Added first drafts to manage record files.
* Added first emulation of xxd.
