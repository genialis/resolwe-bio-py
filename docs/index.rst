
.. _index:

======================
Resolwe SDK for Python
======================

Resolwe SDK for Python supports interaction with Resolwe_ server
and its extension `Resolwe Bioinformatics`_. You can use it to upload
and inspect biomedical data sets, contribute annotations, run
analysis, and write pipelines.

.. _Resolwe Bioinformatics: https://github.com/genialis/resolwe-bio
.. _Resolwe: https://github.com/genialis/resolwe

Install
=======

Install from PyPI::

  pip install resdk

If you would like to contribute to the SDK code base, follow the
:ref:`installation steps for developers <contributing>`.

Usage example
=============

In this showcase we will download the aligned reads and their
index (BAM and BAI) from the server:

.. literalinclude:: files/example_index.py
   :lines: 1-13

Both files (BAM and BAI) have downloaded to the working directory.
Check them out. To learn more about the Resolwe SDK continue with
:ref:`tutorial`.

If you do not have access to the Resolwe server, contact us at
info@genialis.com.

Documentation
=============

.. toctree::
   :maxdepth: 2

   tutorial
   intro
   run
   pipelines
   ref
   contributing
