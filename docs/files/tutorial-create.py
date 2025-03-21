"""Code used in ``tutorial-create.rst`` file."""
import resdk

res = resdk.Resolwe(url='https://app.genialis.com')
res.login()

# Get example reads
example = res.data.get('resdk-example-reads')
# Download them to current working directory
example.download(
    field_name='fastq',
    download_dir='./',
)

# create a new collection object in your running instance of Resolwe (res)
test_collection = res.collection.create(name='Test collection')

# Upload FASTQ reads
reads = res.run(
    slug='upload-fastq-single',
    input={
        'src': './reads.fastq.gz',
    },
    collection=test_collection,
)

reads.sample

# Change name
reads.name = 'My first data'
reads.save()

reads.sample.set_annotation("general.species", "Homo sapiens")

# Get the field by it's group and name:
field = res.annotation_field.get(group__name="general", name="species")
# Same thing, but in shorter syntax
field = res.annotation_field.from_path("general.species")
# Examine some of the field attributes
field.name
field.group
field.description

res.annotation_field.all()
# You can also filter the results
res.annotation_field.filter(group__name="general")

# Get an AnnotationValue
ann_value = reads.sample.get_annotation("general.species")
# The actual value
ann_value.value
# The corresponding field
ann_value.field
# The corresponding sample
ann_value.sample

reads.sample.annotations
reads.sample.get_annotations()
annotations = {
    "general.species": "Homo sapiens", "general.description": "Description"
}
reads.sample.set_annotations(annotations)
reads.sample.set_annotation("general.description", None)



# Get genome
genome_index = res.data.get('resdk-example-genome-index')

alignment = res.run(
    slug='alignment-star',
    input={
        'genome': genome_index,
        'reads': reads,
    },
)

# Get the latest meta data from the server
alignment.update()

# See the process progress
alignment.process_progress

# Print the status of data
alignment.status

# See process output
alignment.output

# Run a workflow
res.run(
    slug='workflow-bbduk-star-featurecounts-qc',
    input={
        'reads': reads,
        'genome': res.data.get('resdk-example-genome-index'),
        'annotation': res.data.get('resdk-example-annotation'),
        'rrna_reference': res.data.get('resdk-example-rrna-index'),
        'globin_reference': res.data.get('resdk-example-globin-index'),
    }
)



# Update the data object to get the most recent info
alignment.update()

# Print process' standard output
print(alignment.stdout())

# Access process' execution information
alignment.process_info

# Access process' execution warnings
alignment.process_warning

# Access process' execution errors
alignment.process_error

