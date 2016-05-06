#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Python API for Resolwe Bioinformatics.
See:
https://github.com/genialis/resolwe-bio-py
"""

from setuptools import setup, find_packages
# Use codecs' open for a consistent encoding
from codecs import open
from os import path


base_dir = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(base_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Get package metadata from 'resolwe.__about__.py' file
about = {}
with open(path.join(base_dir, 'resolwe_api', '__about__.py'), encoding='utf-8') as f:
    exec(f.read(), about)

setup(
    name=about['__title__'],

    version=about['__version__'],

    description=about['__summary__'],
    long_description=long_description,

    url=about['__url__'],

    author=about['__author__'],
    author_email=about['__email__'],

    license=about['__license__'],

    packages=find_packages(),
    package_data={
        'resolwe_api': ['tests/files/*'],
    },

    zip_safe=False,
    install_requires=(
        "requests>=2.6.0",
        "slumber>=0.7.1",
        "appdirs>=1.4.0",
    ),
    extras_require={
        'docs': [
            'sphinx>=1.4.1',
            'sphinx_rtd_theme>=0.1.9',
        ],
        'package': [
            'twine',
            'wheel',
        ],
        'test': [
            'check-manifest',
            'coverage>=3.7.1',
            'mock==1.3.0',
            'pep8>=1.6.2',
            'pylint>=1.4.3',
            'readme_renderer',
        ],
    },

    entry_points={
        'console_scripts': [
            'resolwe-sequp = resolwe_api.scripts:sequp',
            'resolwe-upload-reads = resolwe_api.scripts:readsup',
            'resolwe-upload-reads-batch = resolwe_api.scripts:readsup_batch',
        ],
    },

    test_suite='resolwe_api.tests',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',

        'License :: OSI Approved :: Apache Software License',

        'Operating System :: OS Independent',

        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    keywords='bioinformatics resolwe bio pipelines dataflow django python api',
)
