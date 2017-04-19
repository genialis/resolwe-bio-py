#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resolwe SDK for Python

See: https://github.com/genialis/resolwe-bio-py

"""
from codecs import open  # Use codecs' open for a consistent encoding
from os import path

from setuptools import find_packages, setup

base_dir = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(base_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Get package metadata from 'resolwe.__about__.py' file
about = {}
with open(path.join(base_dir, 'resdk', '__about__.py'), encoding='utf-8') as f:
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

    packages=find_packages(exclude=['tests', 'tests.*', '*.tests', '*.tests.*']),

    zip_safe=False,
    install_requires=(
        'requests>=2.6.0',
        'slumber>=0.7.1',
        'appdirs>=1.4.0',
        'six>=1.10.0',
        'pyyaml>=3.11',
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
            'isort',
            'mock==1.3.0',
            'pycodestyle>=2.1.0',
            'pydocstyle>=1.0.0',
            'pylint~=1.7.0',
            'pytest-cov',
            'readme_renderer',
        ],
    },

    entry_points={
        'console_scripts': [
            'resolwe-sequp = resdk.scripts:sequp',
            'resolwe-upload-reads = resdk.scripts:upload_reads',
            'resolwe-update-kb = resdk.scripts:update_knowledge_base',
        ],
    },

    test_suite='resdk.tests.unit',

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

    keywords='bioinformatics resolwe bio pipelines dataflow django python sdk',
)
