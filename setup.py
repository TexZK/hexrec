#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import io
import os
import re
from glob import glob

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


def read_version():
    path = os.path.join('src', 'hexrec', '__init__.py')
    with open(path, 'rt') as file:
        for line in file:
            if line.startswith('__version__'):
                return eval(line.split('=')[1])
    raise ValueError(f'cannot find __version__ inside of {path}')


setup(
    name='hexrec',
    version=read_version(),
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
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob('src/*.py')],
    include_dirs=['.'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
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
        'bytesparse>=0.0.5',
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
    },
)
