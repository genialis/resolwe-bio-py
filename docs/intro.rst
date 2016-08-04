.. _introduction:

============
Introduction
============

We will explain some basic concepts about Resolwe. Remember them well
as they will be used through documentation.

About Resolwe, Resolwe Bio and SDK for Python
=============================================

`Resolwe`_ is an open source dataflow package for the
`Django framework`_. `Resolwe Bioinformatics`_ is an extension of
Resolwe that provides bioinformatics pipelines. Together, they can
handle large quantities of biological data, perform complex data
analysis, organize results and automatically document your work in
a reproducible fashion.

Resolwe SDK for Python allows you to access Resolwe and Resolwe Bio from
Python. It supports accessing, modifying, uploading and downloading the
data, and writing dataflow pipelines.

.. _Resolwe Bioinformatics: https://github.com/genialis/resolwe-bio
.. _Resolwe: https://github.com/genialis/resolwe
.. _Django framework: https://www.djangoproject.com/


.. figure:: images/resolwe_resdk.jpg
   :width: 100 %

Resolwe and Resolwe Bio run on servers with strong computational
capabilities. ``resdk`` is a Python package on a local computer
that interacts with Resolwe through a RESTful API. The power of
``resdk`` is its lightweight character. It is installed with one
simple command, but supports the manipulation of large data sets
and heavy computation on a remote computer cluster.

Connect to Resolwe
------------------

We have a test Resolwe server on ``https://torta.bcm.genialis.com``.
If you do not have access to Torta, contact us at info@genialis.com.
The user name and password are ``admin/admin``.

.. literalinclude:: files/example_index.py
   :lines: 1-7

If you are working with ``resdk`` in an interactive session, the
logging feature prints useful messages. They will let you know
what is happening behind the scenes. Read more about
:ref:`how the logging is configured in resdk<resdk_resdk_logger>`
or about `Python logging`_ in general.

.. _`Python logging`: https://docs.python.org/2/howto/logging.html

Resolwe basics---resources
==========================

In Resolwe, meta-data is stored in the PostgreSQL database tables:
Data, Sample, Collection, Study, Process, DescriptorSchema, Storage,
User and Group. We support the data management through the `REST API`_.
Each table is represented as a REST resource with a corresponding
endpoint. The Sample table is a special case, represented by two
resources: ``sample`` and ``presample``. More details on samples will
be given later.

In ``resdk`` each REST API endpoint has a corresponding class, with
the same name as in Resolwe: :class:`Process<resdk.resources.Process>`,
:class:`Data<resdk.resources.Data>`,
:class:`Sample<resdk.resources.Sample>` and
:class:`Collection<resdk.resources.Collection>`. Most resources
are implemented in resdk as subclasses of
:class:`BaseResource<resdk.resources.base.BaseResource>`.

.. _REST API: https://torta.bcm.genialis.com/api/

Process and Data
----------------

Two most important resources in Resolwe are *process* and *data*.
Process stores an algorithm that transforms inputs into outputs. It
is a *blueprint* for one step in the analysis. A Data object is an
instance of a process. It is a *complete record* of the process step.

**Example use case:** you have a file with NGS read sequences
(``reads.fastq``) and want to map them to the human genome
(``hg38.fasta``) with the *Bowtie* aligner. All you have to do is
create a Data object---set the process and inputs. When a Data object
is created, the platform automatically runs the given process with
provided inputs. A Data object is a complete record of the processing.
It remembers the inputs (files, arguments, parameters...), the process
(the algorithm) and the outputs (files, images, numbers...). In
addition, Data objects store some useful meta data. This makes it
easy to reproduce the dataflow as well as simply access information.

.. note::

   In the documentation we will refer to process in two different
   contexts. The first has just been presented: the blueprint for
   data objects. In this respect, data object is an instance of a
   process. However, when talking about specific data object, we
   may wish to refer to the algorithm that turned inputs to
   outputs---on this specific data object. We sometimes call
   this as a process as well.

Groups of Data objects
----------------------

Eventually, you will have many Data objects and want to
organize them. Resolwe includes several structures to help you group
Data objects: *Sample*, *Collection* and *Study*.

**Sample** represents a biological entity. It includes user annotations
(GEO compliant) and Data objects associated with this biological entity.
In practice, all Data objects on the sample are derived from an initial
single Data object. A Data object can belong to only one sample.
Typically a sample would contain the following data: raw reads,
aligned reads, and expressions. Two distinct samples can not
contain the same Data object

**Collection** is a working (user-defined, *ad hoc*) group of samples.
In addition to samples and their data, collections may contain
Data objects that store analysis results (*e.g.,* differential
expressions). Samples and Data objects may be in multiple collections.

**Study** is an *upgraded* collection with some additional metadata.
Study relates the provenance or reason samples were generated. Each
sample can belong to only one study.

.. figure:: images/collections_relation.jpg
   :width: 100 %

   Relations between samples, collections and studies. Samples
   are groups of Data objects originating from the same biological
   sample—all Data objects in a sample are derived from a single NGS
   reads file. Collections are arbitrary groups of samples
   and Data objects that store analysis results.

Samples, collections and studies have their own annotations, and
the Data objects they contain have separate annotations. An example
of the annotation field on a Study is ``organism`` and an example
of the annotation field on a Sample is a ``barcode``. The annotation
for sample (also collection and study) represents all Data objects
attached to it.

.. TODO: Image where clear distinction between Resolwe models /
         endpoints and resdk classes is presented.

Query resources
===============

The :class:`resdk.Resolwe` class provides interfaces to the
corresponding resource endpoints:

* ``process``
* ``data``
* ``sample``
* ``collection``
* ``study``

Each endpoint has a corresponding class in Resolwe. Interfaces
support ``get()`` and ``filter()`` methods that enable users
to access the resources:

.. code-block:: python

    resdk.Resolwe.<interface>.get(uid)
    resdk.Resolwe.<interface>.filter(**fields)

The :any:`get()<ResolweQuerry.filter>` method searches by a unique
identifier: ``id`` or ``slug``. It returns a single object of type
``<interface>``.


.. literalinclude:: files/example_intro.py
   :lines: 3-7

The :any:`filter(**fields)<ResolweQuerry.filter>` method returns a list
of objects of type ``<interface>``:

.. literalinclude:: files/example_intro.py
   :lines: 9-13

But the real power of the ``filter()`` method is in combining multiple
filter parameters:

.. literalinclude:: files/example_intro.py
   :lines: 15-16

In a single line we have obtained all data objects that:

* were successfully created (no errors)
* were using the process with name "Aligner (Bowtie 1.0.0)"

Additionally we ordered results by creation time and limited the
number of returned results to three.

Access annotation and download files
------------------------------------

We have learned how to query the resources with ``get`` and ``filter``.
Now we will look at how to access the information in these resources.
All the resources share some common attributes like ``name``, ``id``,
``slug``, ``created`` and ``permissions``. You can access them like any
other Python class attributes.

.. literalinclude:: files/example_intro.py
   :lines: 18-31

Besides these attributes, each resource class has some specific
attributes and methods. For example, resource classes ``Data``,
``Sample``, ``Collection`` and ``Study`` have methods ``files()``
and ``download()``.

The ``files()`` method returns a list of all files on the resource:

 .. literalinclude:: files/example_intro.py
    :lines: 33-43

Method ``download()`` downloads the resource files. Optional parameters
``file_name`` and ``field_name`` have the same effect as in the
``files`` method. There is additional parameter ``download_dir`` -
that allows you to specify the download directory:

.. literalinclude:: files/example_intro.py
   :lines: 45-49

You can find the complete reference for each resource class and their
corresponding attributes and methods in the :doc:`Reference<ref>`.

.. note::

   Some attributes and methods are defined in
   :obj:`BaseCollection<resdk.resources.collection.BaseCollection>`
   and :obj:`BaseResource<resdk.resources.base.BaseResource>`
   classes. :obj:`BaseResource<resdk.resources.base.BaseResource>`
   is the parent of all resource classes in :obj:`resdk`.
   :obj:`BaseCollection<resdk.resources.collection.BaseCollection>`
   is the parent of all collection-like classes:
   :obj:`Sample<resdk.resources.Sample>`,
   :obj:`Collection<resdk.resources.Collection>` and
   :obj:`Study<resdk.resources.Study>`.

You have learned about the resources and how to access data. Continue
with the :ref:`run`.
