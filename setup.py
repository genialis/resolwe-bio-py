#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages


NAME = 'Resolwe Bioinformatics Python API'
VERSION = '3.0.0'
DESCRIPTION = "Python API for Resolwe Bioinformatics."
LONG_DESCRIPTION = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
AUTHOR = 'Genialis'
AUTHOR_EMAIL = 'dev-team@genialis.com'
URL = 'https://github.com/genialis/resolwe-bio-py/'
LICENSE = 'Apache License (2.0)'

if __name__ == '__main__':
    setup(
        name=NAME,

        version=VERSION,

        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,

        url=URL,

        author=AUTHOR,
        author_email=AUTHOR_EMAIL,

        license=LICENSE,

        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        package_data={},
        install_requires=(
            "requests>=2.6.0",
            "slumber>=0.7.1",
            "appdirs>=1.4.0",
        ),
        extras_require = {
            'docs':  ['sphinx>=1.3.2'],
            'package': [
                'twine',
                'wheel',
            ],
            'test': [
                'coverage>=3.7.1',
                'pep8>=1.6.2',
                'pylint>=1.4.3',
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
