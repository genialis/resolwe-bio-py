from example_index import *

# Get processes in the upload category
upload_processes = res.process.filter(category='upload')

# Upload NGS read sequences
reads = res.run(slug='upload-fastq-paired',
                input={
                    'src1': ['/path/to/file/reads_paired_abyss_1.fastq.gz'],
                    'src2': ['/path/to/file/reads_paired_abyss_2.fastq.gz']
                })

# Run the genome assembler
assembled_reads = res.run(slug='assembler-abyss',
                          input={
                              'paired_end': reads.id,
                              'options': {'name': 'test', 'k': 25}
                          })

# Access assembler-abyss process' input schema
res.process.get('assembler-abyss').input_schema

# Print assembler-abyss process' inputs
res.process.get('assembler-abyss').print_inputs()

# Set the descriptor schema slug
descriptor_schema = 'reads'

# Set annotations
descriptor = {
    'barcode': 'TGACCA',
    'barcode_removed': True,
    'instrument_type': 'NextSeq 500',
    'seq_date': '2015-12-31'
}

# Set process' inputs
inputs = {
    'paired_end': reads.id,
    'options': {
        'name': 'blah_blah',
        'k': 20,
        'n': 30
    }
}

# Run the assembler-abyss process
assembled_reads = res.run(slug='assembler-abyss',
                          input=inputs,
                          descriptor=descriptor,
                          descriptor_schema=descriptor_schema,
                          collections=[76],
                          data_name='my_favourite_name')

# Run a process with invalid inputs
result = res.run('some_bad_inputs')

# Update the data object to get the most recent info
result.update()

# Print process' standard output
print(result.stdout())

# Access process' execution information
result.process_info

# Access process' execution warnings
result.process_warning

# Access process' execution errors
result.process_error
