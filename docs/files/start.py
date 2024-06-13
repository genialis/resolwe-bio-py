"""Code for ``start.rst`` file."""
import resdk

# Create a Resolwe object to interact with the server and login
res = resdk.Resolwe(url='https://app.genialis.com')
res.login()

# Enable verbose logging to standard output
resdk.start_logging()

res.data.count()

res.data.filter(type='data:index').count()

res.data.filter(type="data:index:star", name__contains="Homo sapiens")

# Get data object by slug
genome_index = res.data.get('resdk-example-genome-index')

# All paired-end fastq objects
res.data.filter(type='data:reads:fastq:paired')

print("All data objects")
print(res.data.all())

# Get specific object by slug
reads = res.data.get('resdk-example-reads')

reads.contributor

reads.files()

bam = res.run(
    slug='alignment-star',
    input={
        'reads': reads.id,
        'genome': genome_index.id,
    },
)

bam.status

# Get the latest info about the object from the server
bam.update()
bam.status

# Process inputs
bam.input

# Process outputs
bam.output

bam.download()
