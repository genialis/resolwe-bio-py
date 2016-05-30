
=============
Creating data
=============

So far we were only inspecting data: accessing information and downloading stuff. Finally time has come to start creating data objects.

The obvious way to start the analysis is to upload some data to Resolwe. We will do that by using process of type upload. It may sound strange at first, but uploading the data to Resaolwe is exactly the same as running any other process. We have inputs - path to some file on our local computer, an algorithm (some file transfer protocol) and output - reference to same file freshly uploaded on Resolwe server.

There are many upload processes, since there are many different types of files that can be uploaded. How to find out what are all the possible upload processes? Well, using  the knowledge from previous chapter::

    upload_processes = res.process.filter(category='upload')

Uploading file to Resolwe is as easy as::

    reads = res.run(slug='import-upload-reads-fastq', input={src:'/path/to/file/reads.fastq'})

As you can see, we only provided process slug and input data. What we th method returns is a data object ``reads``. After uploading reads, we may want to assemble them with *Abyss*::


    assembled_reads = res.run(slug='assembler-abyss', input={'se':reads.id})
    TODO: How do i do i reference the data on platform?

You probably noticed that we get the result almost instantly, while typical assembling process can last multiple hours. This is because processing runs asynchronously, so the returned Data object (``assembled_reads``) does not have an OK status or outputs when returned. Use ``assembled_reads.update()`` to refresh the information. Also, to estimate ``assembled_reads.process_progress`` can be useful.

From the documentation of method :any:`run <Resolwe.run>` we see how to run process in general::

    result = res.run(slug=None, input={}, descriptor=None, descriptor_schema=None,
            collections=[], data_name='', src=None, tools=None)


The first agrument is the slug of process to use. It was already showed how to get the slug of desired process some lines before.

Secondly, inputs should be provided. As seen in the upper example, they are given with dictionary of ``"input_name":input_value`` pairs. But how to know what are all the possible inputs for a given process? Well, this is excactly what input schema is for::

    abyss_process = res.process.get('assembler-abyss')
    abyss_inputs = abyss_process.input_schema

The output may not be the visually intuitive so we made a nice image to emphsize the content:

IMAGE:
In put schema is a list of dictionaries. Each dictionary contains:

* name - unique name of the field
* label - human readable name
* type - type of field
* other optional fields (description, required, default, validate_regex ...)

Except for dictionaries where the group is:
there jou juts have :

*name
* label
For


Except for options: it is a subdictionary...

For now, this should suffice, but for more info regarding process syntax, visit `Resolwe documentation.`_
.. _`Resolwe documentation.`: http://resolwe.readthedocs.io/en/latest/proc.html#input-and-output


What is descriptor schema for?

Additoionally
How to know descriptor_schema or descriptor?

Collections

data name - none but d+set by process if not provided

src and tools - only for development - link further on Just reference to :doc:`writing pipelines. </pipelines>`


For process development, use src and tools arguments. If src
argument given, a process from the specified source YAML file
is first uploaded and registered on the server. List the
process auxiliary scripts (tools to call in the processes)
in the tools argument. This scripts will be copied to the
server automatically with SCP.


veriženje - delayed execution!!!

