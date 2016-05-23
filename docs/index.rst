
.. _index:

======================
Resolwe SDK for Python
======================

Resolwe_ is a dataflow package for the `Django framework`_.
`Resolwe Bioinformatics`_ is an extension of Resolwe that provides
bioinformatics pipelines. Resolwe SDK for Python supports writing
dataflow pipelines for Resolwe and Resolwe Bioinformatics.

.. _Resolwe Bioinformatics: https://github.com/genialis/resolwe-bio
.. _Resolwe: https://github.com/genialis/resolwe
.. _Django framework: https://www.djangoproject.com/

Install
=======

Install from PyPI::

  pip install resdk

To install for development, `fork on Github`_ and run::

  git clone https://github.com/<GITHUB_USER>/resolwe-bio-py.git
  cd resolwe-bio-py
  pip install -e .[docs,package,test]

.. _fork on Github: https://github.com/genialis/resolwe-bio-py

Usage example
=============

Connect to a Resolwe server, get sample by ID and download the
aligned reads (BAM file):

.. literalinclude:: files/resdk-example.py
   :lines: 1-8

If you do not have access to the Resolwe server, contact us at
info@genialis.com.

Documentation
=============

.. toctree::
   :maxdepth: 2

   intro
   pipelines
   ref
   contributing
