.. _tutorial:

===============
Getting started
===============

This tutorial is for bioinformaticians. It will help you install the SDK
and showcase some basic commands. We will connect to a Resolwe server,
upload a BAM file, and identify a chromosome with the most aligned
reads. Before we begin, make sure you have SSH access to the
`Torta server`_.

.. _Torta server: https://torta.bcm.genialis.com

Installation
============

Installing is easy, just make sure you have Python_ and pip_ installed
on your computer. Run this command in the terminal (CMD on Windows)::

  pip install resdk

.. _Python: https://www.python.org/downloads/
.. _pip: https://pip.pypa.io/en/stable/installing/

Set the ``TOOLS_REMOTE_HOST`` environment variable in your terminal:

.. code-block:: bash

    export TOOLS_REMOTE_HOST=<username>@torta.bcmt.bcm.edu://genialis/tools

This address will be used to automatically copy your scripts to the
Resolwe server. Make sure to set the ``TOOLS_REMOTE_HOST`` environment
variable in all terminal windows where you run Python.

Tutorial
========

Run Python interpreter (type ``python`` in the terminal) and connect
to the Resolwe server:

.. literalinclude:: files/example_index.py
   :lines: 1-7

Upload a BAM file with the `upload-bam`_ process (you can
`download a test BAM file from here`_):

.. _upload-bam: https://github.com/genialis/resolwe-bio/blob/master/resolwe_bio/processes/import_data/bam.yml
.. _download a test BAM file from here: https://torta.bcm.genialis.com/data/494/human_example_chr22.bam?force_download=1

.. code-block:: python

    # Upload a BAM file
    bam = res.run('upload-bam', input={'src': '/path/to/file/test.bam'})

What just happened? We have assigned a BAM file path to the process'
input field ``src``. Each process has a defined set of input and
output fields. Inputs should be given at execution. Then the
process runs its algorithm that transforms inputs into outputs. In the
above case, the BAM file is uploaded, indexed with ``samtools``, and
saved into output fields ``bam`` and ``bai``. Many other processes
are available, they are listed in the `Process catalog`_ of the
`Resolwe Bioinformatics documentation`_.

.. _Process catalog: http://resolwe-bio.readthedocs.io/en/latest/catalog.html
.. _Resolwe Bioinformatics documentation: http://resolwe-bio.readthedocs.io

Uploading a BAM creates an object that can be referenced by ID or slug.
This objects can have annotations that are used in searches.

.. code-block:: python

   bam.id  # unique identifier
   bam.slug  # a human readable unique identifier

This abstracts the concept of paths. Paths are not needed because
objects can be retrieved or referenced in inputs by IDs. For instance,
we can get the same object from the server:

.. code-block:: python

   # Retrieve the object that we have just created
   bam2 = res.data.get(bam.id)

   # Retrieve the same object by slug
   bam3 = res.data.get(bam.slug)

All three Python objects point to the same data object on the server:

.. code-block:: python

   # All reference the same data object
   print(bam.id, bam2.id, bam3.id)

Let's think about what is happening to the data object on the server.
Did the processing finish? Check the status of the bam object:

.. code-block:: python

   # Get the latest meta data from the server
   bam.update()

   # Print the status
   bam.status

Status ``OK`` indicates the processing has finished successfuly.
The commands that were executed on the server can be inspected by:

.. code-block:: python

   # Print the process' standard output
   print(bam.stdout())

The output is long but exceedingly useful for debugging. Lines 34
and 40 are particularly interesting. They tell us that the uploaded
file has been assigned a temporary name for upload, then moved,
renamed and indexed.

.. code-block:: console
   :lineno-start: 34
   :emphasize-lines: 1,7

   + mv /home/biolinux/upload/e4756869f32d3f5e411a80c7daafcc4bbf336c41 human_example_chr22.bam
   + testrc
   + RC=0
   + '[' ']'
   + '[' 0 -gt 0 ']'
   + echo '{"proc.progress":0.3}'
   + samtools index human_example_chr22.bam

Files that are on the server are referenced in the object output:

.. code-block:: python

   # Files are referenced in object output
   bam.output

You can download them to your computer simply as:

.. code-block:: python

   # Download all files of the object
   bam.download()

The BAM object on the server can now be used in further processing
steps by any other process that use a compatible input type
(`e.g.,` ``data:alignment:bam:upload``). For instance we can compute
a BigWig coverage track:

.. code-block:: python

   # Compute a BigWig coverage
   bigwig = res.run('jbrowse-bam-coverage', input={'bam': bam.id})

You will have to wait about 5 min to compute the coverage.
Check the output from time to time.

.. code-block:: python

   # Check the status of the BigWig process
   bigwig.update(); bigwig.status

The ``PR`` status means processing. Wait for the status to turn ``OK``,
then download the coverage track.

.. code-block:: python

   # Download the coverage track
   bigwig.download()

You can write your own analysis processes that run on the server.
Let's write a process that takes a BAM object and reports which
chromosome has the largest number of aligned reads.

.. code-block:: yaml

    - slug: max-reads            # User readable unique identifier
      name: Max reads            # Process name
      data_name: Chromosome      # The name of data objects created by the process
      version: 1.0.0             # Process version
      type: data:bam:stats       # The type of the process and data objects created by it
      input:
        - name: bam
          label: BAM file
          type: data:alignment:bam
      output:
        - name: stats
          label: Stats
          type: basic:file
        - name: chr
          label: Chr (max reads)
          type: basic:string
      run:                       # The algorithm in bash using Django template tags
        runtime: polyglot
        bash: |
          # Compute sequence alignment statistics
          samtools idxstats {{bam.bam.file}} > stats.txt

          # Save the statistics file
          re-save-file stats stats.txt

          # Find chromosome with the largest number of aligned reads
          CHR=`<my_script>.py stats.txt`

          # Save the chromosome name
          re-save chr "${CHR}"

Copy the above code to a file ``<process_name>.yaml``, use a text
editor. **Make sure to modify the name of the Python script**
``<my_script>.py`` **that is referenced in the above code**.
**You will create this Python script in the next step**. Analysis
steps can call programs installed in our `docker container`_ (`e.g.,`
``samtools``) and custom scripts (`e.g.,` Python and R) defined by the
user. We have designed the process ``<process_name>.yaml`` to use
a custom script ``<my_script>.py`` to parse the ``samtools idxstats``
results file and report the chromosome name.

.. _docker container: https://github.com/genialis/docker-bio-linux8-resolwe

.. code-block:: python

    #!/usr/bin/env python2
    import sys

    # Read the statistics file name from the command arguments
    fname = sys.argv[1]

    max_reads = 0
    chromosome = ''

    # Open the statistics file
    with open(fname) as file:
        # Iterate through lines
        for line in file:
            # Find lines with chromosome statistics
            if line.startswith('chr'):
                stats = line.split('\t')
                # Check if a chromosome has the largest number of aligned reads
                if int(stats[2]) > max_reads:
                    # Store the number of aligned reads
                    max_reads = int(stats[2])
                    # Store chromosome name
                    chromosome = stats[0]

    print chromosome

Save the above code to ``<my_script>.py`` file and mark it executable.

.. code-block:: bash

    # Make the file executable
    chmod +x <my_script>.py

We can now use the uploaded BAM object (``bam``) as input to the
process that we just wrote:

.. code-block:: python

   # Run the custom process on the server
   chr = res.run('max-reads',
                 input={'bam': bam.id},
                 src='/path/to/<process_name>.yaml',
                 tools=['/path/to/<my_script>.py'])

Again, we can inspect the status of the processing step by:

.. code-block:: python

    # Get the latest meta data from the server
    chr.update()

    # Print the status
    chr.status

    # Print the process' standard output
    print(chr.stdout())

We can see the analysis results by inspecting the ``chr`` object's
``output`` fields.

.. code-block:: python

    # Inspect the process output
    chr.output

The name of the chromosome with the most aligned reads is saved in
the ``chr`` output field. The file in the ``stats`` field with the
sequence alignment statistics can be downloaded by:

.. code-block:: python

    # Download chromosome statistics file
    chr.download()

We have covered the basics. Please continue with the
:ref:`introduction` where we explain how the data is organized on the
Resolwe server and how to query existing data sets.
