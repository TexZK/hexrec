#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='hexrec',
    version='0.2.3',
    license='BSD 2-Clause License',
    description='Library to handle hexadecimal record files',
    long_description='%s\n%s' % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S)
            .sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))
    ),
    long_description_content_type='text/x-rst',
    author='Andrea Zoppi',
    author_email='texzk@email.it',
    url='https://github.com/TexZK/hexrec',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Software Development',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Utilities',
    ],
    python_requires='>=3.6',
    keywords=[
    ],
    install_requires=[
        'click',
        'Deprecated',
    ],
    extras_require={
        'testing': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'hexrec = hexrec.cli:main',
        ],
        'hexrec_types': [
            'ascii_hex = hexrec.formats.ascii_hex:Record',
            'binary = hexrec.formats.binary:Record',
            'intel = hexrec.formats.intel:Record',
            'mos = hexrec.formats.mos:Record',
            'motorola = hexrec.formats.motorola:Record',
            'tektronix = hexrec.formats.tektronix:Record',
        ],
    },
)
