======================
Resolwe SDK for Python
======================

|build| |coverage| |docs| |pypi_version| |pypi_pyversions|

.. |build| image:: https://travis-ci.org/genialis/resolwe-bio-py.svg?branch=master
    :target: https://travis-ci.org/genialis/resolwe-bio-py
    :alt: Build Status

.. |coverage| image:: https://img.shields.io/codecov/c/github/genialis/resolwe-bio-py/master.svg
    :target: http://codecov.io/github/genialis/resolwe-bio-py?branch=master
    :alt: Coverage Status

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

Resolwe SDK for Python supports interaction with Resolwe_ server
and its extension `Resolwe Bioinformatics`_. You can use it to upload
and inspect biomedical data sets, contribute annotations, run
analysis, and write pipelines.

.. _Resolwe Bioinformatics: https://github.com/genialis/resolwe-bio
.. _Resolwe: https://github.com/genialis/resolwe

Docs & Help
===========

Read the detailed description in documentation_.

.. _documentation: http://resdk.readthedocs.io/

Install
=======

Install from PyPI::

  pip install resdk

If you would like to contribute to the SDK codebase, follow the
`installation steps for developers`_.

.. _installation steps for developers: http://resdk.readthedocs.io/en/latest/contributing.html

Quick Start
===========

In this showcase we will download the aligned reads and their
index (BAM and BAI) from the server:

.. code-block:: python

   import resdk

   # Create a Resolwe object to interact with the server
   res = resdk.Resolwe('admin', 'admin', 'https://torta.bcm.genialis.com')

   # Print command details to stdout
   resdk.start_logging()

   # Get sample meta-data from the server
   sample = res.sample.get('human-example-chr22')

   # Download files associated with the sample
   sample.download()

Both files (BAM and BAI) have downloaded to the working directory.
Check them out. To learn more about the Resolwe SDK continue with
`Getting started`_.

.. _Getting started: http://resdk.readthedocs.io/en/latest/tutorial.html

If you do not have access to the Resolwe server, contact us at
info@genialis.com.
