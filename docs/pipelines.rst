.. _pipelines:

=================
Writing pipelines
=================

In :doc:`previous chapter<run>` we have shown how to run processes with
the ``run`` command. We define the process to execute on the server
with the slug parameter (*e.g.,* ``alignment-bowtie2``).
The process has to be registered (installed) on the server, or the
command will fail.

.. code-block:: python

   import resdk

   # Sign-in the Resolwe server
   res = resdk.Resolwe('admin', 'admin', 'https://torta.bcm.genialis.com')

   # Get the genome
   genome = res.data.get('human-example-chr22-reads')

   # Get a sample
   sample = res.sample.get('')

   # Access genome ID
   genome_id = genome.id

   # Access the ID of the first data object on the sample
   reads_id = sample.data[0]

   # Run the Bowtie 2 read sequence alignment
   aligned = res.run('alignment-bowtie2',
                     input={
                         'genome': genome_id,
                         'reads': reads_id,
                         'reporting': {'rep_mode': 'k', 'k_reports': 1}
                     })

This is great for running processes, but not so much for development.
Developers want to modify the analysis process. Two arguments of
the ``run`` method help developers with this challenge: ``src`` and
``tools``. With the ``src`` argument, you can reference a local script
that contains process definition. The process definition will first
automatically register (install) on the server and then the data object
would be created and the process would run. The code shows an example.
You can play with the Bowtie2 process locally (in `bowtie.yml`_
file), but the process runs on the server.

.. code-block:: python
   :emphasize-lines: 5

   aligned = res.run('alignment-bowtie2',
                     input={
                         'genome': genome_id,
                         'reads': reads_id,
                         'reporting': {'rep_mode': 'k', 'k_reports': 1}
                     },
                     src='bowtie.yml')

.. _bowtie.yml: https://github.com/genialis/resolwe-bio/blob/master/resolwe_bio/processes/alignment/bowtie.yml

The process's algorithm is written in bash. We can directly call programms that
are included in the runtime (*e.g.,* cat, head and grep). Resolwe
Bioinformatics runs processes in a `Docker container`_ with many
bioinformatics tools pre-installed. In the *Bowtie 2.2.3*
process we call the ``bowtie2`` aligner, ``samtools`` and other
commands.

.. _Docker container: https://github.com/genialis/docker-bio-linux8-resolwe

.. code-block:: bash
   :linenos:
   :lineno-start: 460

   samtools sort "${FW_NAME}_align_unsorted.bam" "${FW_NAME}_align"

Sometimes you may want to write *ad-hoc* scripts and call them from
processes. For instance, to post-process the results of Bowtie, we call
``mergebowtiestats.py``.

.. code-block:: bash
   :linenos:
   :lineno-start: 214

   mergebowtiestats.py $STATS

Resolwe allows to place the *ad-hoc* scripts in a ``tools`` folder that
is added to runtime PATH. The ``tools`` folder is on Resolwe server,
so SDK helps you upload your *ad-hoc* scripts to the server automatically.
Files are transfered via SCP, so you should have an SSH access to the
Resolwe server. Also, you have to configure the `password-less
authentication`_.

.. _password-less authentication: https://docs.fedoraproject.org/en-US/Fedora/14/html/Deployment_Guide/s2-ssh-configuration-keypairs.html

You have to tell the Resolwe SDK where to copy the files. Set the
``TOOLS_REMOTE_HOST`` environment variable in your terminal:

.. code-block:: bash

   export TOOLS_REMOTE_HOST=<username>@torta.bcmt.bcm.edu://genialis/tools

Now you can reference your *ad-hoc* scripts in the ``run`` command with
the tools argument:

.. code-block:: python
   :emphasize-lines: 5

   aligned = res.run('alignment-bowtie2',
                     input={
                         'genome': genome_id,
                         'reads': reads_id,
                         'reporting': {'rep_mode': 'k', 'k_reports': 1}
                     },
                     src='bowtie.yml',
                     tools=['mergebowtiestats.py'])

The tools folder is in the runtime PATH. If you wish to run your
scripts in a Resolwe process, remember to make them executable (*e.g.,*
``chmod +x mergebowtiestats.py``) and set an appropriate shebang_
(*e.g.,* ``#!/usr/bin/env python2`` for Python and
``#!/usr/bin/Rscript`` for R).

.. _shebang: https://en.wikipedia.org/wiki/Shebang_(Unix)

Note that processes are executed asynchronously. This allows you
to write the whole pipeline from start to finish interactivelly in
Python shell, witout waiting for each step to finish. But you have to
manually check if results are ready from time to time:

.. code-block:: python

   # Check the status of your data object
   aligned.update(); aligned.status

You can view the process' ``stdout`` to inspect if it runs as intended
and debug errors:

.. code-block:: python

   # Print the process' standard output
   print(aligned.stdout())

You can read how to write processes in YAML syntax in the
`Writing processes`_ chapter of Resolwe Documentation. You should
review which processes are already available in the `Process catalog`_
and what inputs they accept.

.. _Writing processes: http://resolwe.readthedocs.io/en/latest/proc.html
.. _Process catalog: http://resolwe-bio.readthedocs.io/en/latest/catalog.html
