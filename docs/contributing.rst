.. _contributing:

============
Contributing
============

Installing prerequisites
========================

Make sure you have Python_ (2.7 or 3.4+) installed on your system. If
you don't have it yet, follow `these instructions
<https://docs.python.org/3/using/index.html>`__.

.. _Python: https://www.python.org/

Preparing environment
=====================

`Fork <https://help.github.com/articles/fork-a-repo>`__ the main
`Resolwe SDK for Python git repository`_.

If you don't have Git installed on your system, follow `these
instructions <http://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`__.

Clone your fork (replace ``<username>`` with your GitHub account name) and
change directory::

    git clone https://github.com/<username>/resolwe-bio-py.git
    cd resolwe-bio

Prepare Resolwe SDK for Python for development::

    pip install -e .[docs,package,test]

.. note::

    We recommend using `virtualenv <https://virtualenv.pypa.io/>`_ (on
    Python 2.7) or `pyvenv <http://docs.python.org/3/library/venv.html>`_ (on
    Python 3.4+) to create an isolated Python environment.

.. _Resolwe SDK for Python git repository: https://github.com/genialis/resolwe-bio-py

Running tests
=============

Run unit tests::

    py.test

Coverage report
===============

To see the tests' code coverage, use::

    py.test --cov=resdk

To generate a HTML with tests' code coverage, use::

    py.test --cov=resdk --cov-report=html

Building documentation
======================

.. code-block:: none

    python setup.py build_sphinx
