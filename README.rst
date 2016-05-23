======================
Resolwe SDK for Python
======================

|build| |docs| |pypi_version| |pypi_pyversions| |pypi_downloads|

.. |build| image:: https://travis-ci.org/genialis/resolwe-bio-py.svg?branch=master
    :target: https://travis-ci.org/genialis/resolwe-bio-py
    :alt: Build Status

.. |docs| image:: https://readthedocs.org/projects/resdk/badge/?version=latest
    :target: http://resdk.readthedocs.io/
    :alt: Documentation Status

.. |pypi_version| image:: https://img.shields.io/pypi/v/resdk.svg
    :target: https://pypi.python.org/pypi/resdk
    :alt: Version on PyPI

.. |pypi_pyversions| image:: https://img.shields.io/pypi/pyversions/resdk.svg
    :target: https://pypi.python.org/pypi/resdk
    :alt: Supported Python versions

.. |pypi_downloads| image:: https://img.shields.io/pypi/dm/resdk.svg
    :target: https://pypi.python.org/pypi/resdk
    :alt: Number of downloads from PyPI

Resolwe_ is a dataflow package for the `Django framework`_.
`Resolwe Bioinformatics`_ is an extension of Resolwe that provides
bioinformatics pipelines. Resolwe SDK for Python supports writing
dataflow pipelines for Resolwe and Resolwe Bioinformatics.

.. _Resolwe Bioinformatics: https://github.com/genialis/resolwe-bio
.. _Resolwe: https://github.com/genialis/resolwe
.. _Django framework: https://www.djangoproject.com/

Docs & Help
===========

Read the detailed description in documentation_.

.. _documentation: http://resolwe-bio-py.readthedocs.io/

Install
=======

Install from PyPI::

  pip install resdk

To install for development, `fork on Github`_ and run::

  git clone https://github.com/<GITHUB_USER>/resolwe-bio-py.git
  cd resolwe-bio-py
  pip install -e .[docs,package,test]

.. _fork on Github: https://github.com/genialis/resolwe-bio-py

Quick Start
===========

Connect to a Resolwe server:

.. literalinclude:: docs/files/resdk-example.py
   :lines: 1-5

If you do not have access to the Resolwe server, contact us at
info@genialis.com.

Get sample by ID and download the aligned reads (BAM file):

.. literalinclude:: docs/files/resdk-example.py
   :lines: 7-8

Find human samples and download all aligned reads (BAM files):

.. literalinclude:: docs/files/resdk-example.py
   :lines: 10-12

Primary analysis (*e.g.,* filtering, alignment, expression estimation)
starts automatically when samples are annotated. A step in primary
analysis is represented as ``Data`` object, attached to the sample.
A ``Sample`` object includes sample annotation. A ``Data`` object
includes input parameters, results and analysis annotation. Print the
steps in primary analysis pipeline:

.. literalinclude:: docs/files/resdk-example.py
   :lines: 14-17

Find ROSE2 analysis results and download a super-enhancer rank plot of
the first ROSE2 analysis Data object:

.. literalinclude:: docs/files/resdk-example.py
   :lines: 19-21

Run Bowtie2 mapping on the reads ``Data`` object of the above sample:

.. literalinclude:: docs/files/resdk-example.py
   :lines: 23-31

After a while you can check if the alignment has finished:

.. literalinclude:: docs/files/resdk-example.py
   :lines: 33-34

Continue in the `Getting Started`_ section of Documentation, where we
explain how to upload files, create samples and provide details about
the Resolwe backend. Bioinformaticians can learn how to develop
pipelines in `Writing Pipelines`_.

.. _Getting Started: http://resdk.readthedocs.io/en/latest/intro.html
.. _Writing Pipelines: http://resdk.readthedocs.io/en/latest/pipelines.html
