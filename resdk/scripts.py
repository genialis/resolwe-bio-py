"""Command line scripts."""
# pylint: disable=logging-format-interpolation
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import fnmatch
import logging
import os
import time
import zipfile

import appdirs
import slumber

from . import __about__ as about
from . import Resolwe, resdk_logger

ORGANISMS = {
    'HUMAN': 'Homo sapiens',
    'HOMO SAPIENS': 'Homo sapiens',
    'MOUSE': 'Mus musculus',
    'MUS MUSCULUS': 'Mus musculus',
    'DICTY': 'Dictyostelium discoideum',
    'DICTYOSTELIUM DISCOIDEUM': 'Dictyostelium discoideum',
}

EXPERIMENT_TYPE = {
    'RNA-SEQ': 'RNA-Seq',
    'MIRNA-SEQ': 'miRNA-Seq',
    'NCRNA-SEQ': 'ncRNA-Seq',
    'RNA-SEQ (CAGE)': 'RNA-Seq (CAGE)',
    'RNA-SEQ (RAGE)': 'RNA-Seq (RACE)',
    'CHIP-SEQ': 'ChIP-Seq',
    'MNASE-SEQ': 'MNase-Seq',
    'MBD-SEQ': 'MBD-Seq',
    'MRE-SEQ': 'MRE-Seq',
    'BISULFITE-SEQ': 'Bisulfite-Seq',
    'BISULFITE-SEQ (REDUCED REPRESENTATION)': 'Bisulfite-Seq (reduced representation)',
    'MEDIP-SEQ': 'MeDIP-Seq',
    'DNASE-HYPERSENSITIVITY': 'DNase-Hypersensitivity',
    'TN-SEQ': 'Tn-Seq',
    'FAIRE-SEQ': 'FAIRE-seq',
    'SELEX': 'SELEX',
    'RIP-SEQ': 'RIP-Seq',
    'CHIA-PET': 'ChIA-PET',
    'OTHER': 'OTHER',
}

SUBTYPE_MAP = {
    'processed_pseudogene': 'pseudo',
    'unprocessed_pseudogene': 'pseudo',
    'polymorphic_pseudogene': 'pseudo',
    'transcribed_unprocessed_pseudogene': 'pseudo',
    'unitary_pseudogene': 'pseudo',
    'transcribed_processed_pseudogene': 'pseudo',
    'transcribed_unitary_pseudogene': 'pseudo',
    'TR_J_pseudogene': 'pseudo',
    'IG_pseudogene': 'pseudo',
    'IG_D_pseudogene': 'pseudo',
    'IG_C_pseudogene': 'pseudo',
    'TR_V_pseudogene': 'pseudo',
    'IG_V_pseudogene': 'pseudo',
    'pseudogene': 'pseudo',
    'pseudo': 'pseudo',
    'asRNA': 'asRNA',
    'antisense': 'asRNA',
    'protein_coding': 'protein-coding',
    'protein-coding': 'protein-coding',
    'IG_V_gene': 'protein-coding',
    'IG_LV_gene': 'protein-coding',
    'TR_C_gene': 'protein-coding',
    'TR_V_gene': 'protein-coding',
    'TR_J_gene': 'protein-coding',
    'IG_J_gene': 'protein-coding',
    'TR_D_gene': 'protein-coding',
    'IG_C_gene': 'protein-coding',
    'IG_D_gene': 'protein-coding',
    'miRNA': 'ncRNA',
    'lincRNA': 'ncRNA',
    'processed_transcript': 'ncRNA',
    'sense_intronic': 'ncRNA',
    'sense_overlapping': 'ncRNA',
    'bidirectional_promoter_lncRNA': 'ncRNA',
    'ribozyme': 'ncRNA',
    'Mt_tRNA': 'ncRNA',
    'Mt_rRNA': 'ncRNA',
    'misc_RNA': 'ncRNA',
    'macro_lncRNA': 'ncRNA',
    '3prime_overlapping_ncRNA': 'ncRNA',
    'sRNA': 'ncRNA',
    'snRNA': 'snRNA',
    'scaRNA': 'snoRNA',
    'snoRNA': 'snoRNA',
    'rRNA': 'rRNA',
    'ncRNA': 'ncRNA',
    'tRNA': 'tRNA',
    'other': 'other',
    'unknown': 'unknown'
}

# Scripts logger.
logger = logging.getLogger(__name__)


def sequp():
    """Auto-upload NGS reads from directory to the Resolwe server.

    Script checks if there are new reads or annotation files in the
    target directory tree. If both: reads and corresponding annotation
    files are present, upload the reads and set the initial annotation
    based on the annotation file.

    We want to upload files which have not been uploaded yet. We need
    to know the most recent modification date of all uploaded files.
    Files modified later are upload candidates. The timestamp of last
    modification time is stored in config_file.

    """
    # XXX: Saving the config_file in user_data_dir is probably not the
    # right decision. We want multiple users to be able to upload data
    # to the same directory - therefore the config_file should be set
    # for the system and not user dependant.

    # Application data
    config_file = os.path.join(appdirs.user_data_dir(about.__title__, about.__author__), 'config')
    # XXX: Increase to 1h
    change_time_window = 5

    parser = argparse.ArgumentParser(description='Auto-upload NGS reads from '
                                     'directory to the Resolwe server.')

    parser.add_argument('-a', '--address', help='Resolwe server address')
    parser.add_argument('-e', '--email', help='User e-mail')
    parser.add_argument('-p', '--password', help='User password')
    parser.add_argument('-d', '--directory', help='Observed directory with reads')
    parser.add_argument('-f', '--force', action='store_true', help='Force upload of all files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose reporting')

    args = parser.parse_args()

    if args.verbose:
        resdk_logger.start_logging()

    genialis_url = args.address or os.getenv('GENIALIS_URL') or 'http://localhost:8000'
    genialis_email = args.email or os.getenv('GENIALIS_EMAIL') or 'admin'
    genialis_pass = args.password or os.getenv('GENIALIS_PASS') or 'admin'
    genialis_seq_dir = args.directory or os.getenv('GENIALIS_SEQ_DIR') or os.path.expanduser('~')
    genialis_seq_dir = os.path.normpath(genialis_seq_dir)

    logger.info('Address: {}'.format(genialis_url))
    logger.info('User: {}'.format(genialis_email))
    logger.info('Pass: ******')
    logger.info('Directory: {}'.format(genialis_seq_dir))

    if args.force and os.path.isfile(config_file):
        os.remove(config_file)

    def read_timestamps():
        """Read timestamps from config_file.

        :rtype: Dict of pairs (dir, timestamp)

        """
        if not os.path.isfile(config_file):
            return {}

        data = {}
        with open(config_file, 'r') as file_:
            for line in file_:
                parts = line.strip().split('\t')
                data[parts[0]] = float(parts[1])
        return data

    def write_timestamps(pairs):
        """Write timestamps to config_file."""
        with open(config_file, 'w') as file_:
            for first, second in pairs.items():
                file_.write(str(first) + '\t' + str(second) + '\n')

    def get_timestamp():
        """Get timestamp for GENIALIS_SEQ_DIR."""
        timestamps = read_timestamps()
        return timestamps.get(genialis_seq_dir, 0)

    def set_timestamp(timestamp):
        """Set timestamp for GENIALIS_SEQ_DIR."""
        if os.path.isfile(config_file):  # Update timestamp
            pairs = read_timestamps()
            pairs[genialis_seq_dir] = timestamp
            write_timestamps(pairs)

        else:  # Create config file and add timestamp
            try:
                os.makedirs(os.path.dirname(config_file))
                write_timestamps({genialis_seq_dir: timestamp})
            except OSError:
                # Folder already exists, make the file
                write_timestamps({genialis_seq_dir: timestamp})

    # Get timestamp
    timestamp = get_timestamp()

    # Find new reads
    all_new_read_files = []
    read_file_extensions = ['*.fastq', '*.fastq.gz', '*.fq', '*.fq.gz']

    for root, _, filenames in os.walk(genialis_seq_dir):
        for extension in read_file_extensions:
            for filename in fnmatch.filter(filenames, extension):
                path = os.path.join(root, filename)
                if os.path.getmtime(path) > timestamp:
                    all_new_read_files.append(path)

    # Determnine if the candidate files are fully uploaded by the
    # sequencer. The idea is that the file size does not change in a
    # defined time window (change_time_window).
    sizes1 = {f: os.path.getsize(f) for f in all_new_read_files}
    time.sleep(change_time_window)
    sizes2 = {f: os.path.getsize(f) for f in all_new_read_files}

    all_new_read_files_uploaded = [os.path.normpath(f) for f in all_new_read_files if
                                   sizes1[f] == sizes2[f]]

    # Find all annotation files
    all_annotation_files = []
    annotation_file_extensions = ['*.csv', '*.txt', '*.tsv']
    for root, _, filenames in os.walk(genialis_seq_dir):
        for extension in annotation_file_extensions:
            for filename in fnmatch.filter(filenames, extension):
                all_annotation_files.append(os.path.join(root, filename))

    def parse_annotation_file(annotation_file):
        """Parse annotation file to list of annotation objects."""
        anns = {}
        seq_paths = []
        # We use 'rU' mode to be able to read also files with '\r' chars
        with open(annotation_file, 'rU') as file_:
            try:
                reader = csv.DictReader([row for row in file_ if row[0] != '#'],
                                        delimiter=str('\t'))

                # One line is one annotation (one reads file)
                for row in reader:
                    # Capitalize dict keys
                    row.update({k.upper(): v for k, v in row.items()})

                    if 'FASTQ_PATH' in row:
                        for seqfile in row['FASTQ_PATH'].split(','):
                            seq_path = os.path.normpath(os.path.join(genialis_seq_dir, seqfile))
                            seq_paths.append(seq_path)

                        if all(os.path.isfile(sf) for sf in seq_paths):
                            row['FASTQ_PATH'] = ','.join(seq_paths)
                            anns[row['SAMPLE_NAME']] = row
                            seq_paths = []

            except csv.Error:
                logger.error("File type not supported")
                exit(1)
        return anns

    # Write all annotations to single dict with reads filenames as keys
    annotations = {}
    for ann_file in all_annotation_files:
        annotations.update(parse_annotation_file(ann_file))

    # Connect to Resolwe server
    resolwe = Resolwe(genialis_email, genialis_pass, genialis_url)

    read_schemas = resolwe.api.descriptorschema.get(slug='reads')
    read_schema = read_schemas[0] if read_schemas else None

    # Upload all files in all_new_read_files_uploaded with annotations
    uploaded_files = []

    for sample_n in annotations:
        input_ = {}
        fw_reads = annotations[sample_n]['FASTQ_PATH'].split(',')

        if set(fw_reads).issubset(set(all_new_read_files_uploaded)):
            descriptor, descriptor_schema = None, None

            if read_schema:
                descriptor_schema = read_schema['slug']
                barcode_removed = annotations[sample_n].get('BARCODE_REMOVED', 'N').strip().upper()
                exp_type = EXPERIMENT_TYPE.get(annotations[sample_n]['SEQ_TYPE'].upper(), '')
                descriptor = {
                    'reads_info': {
                        'barcode': annotations[sample_n].get('BARCODE', None),
                        'barcode_removed': True if barcode_removed == 'Y' else False,
                        'instrument_type': annotations[sample_n].get('INSTRUMENT', None),
                        'seq_date': annotations[sample_n].get('SEQ_DATE', None)
                    }
                }
                if exp_type:
                    descriptor['experiment_type'] = exp_type
            # Paired-end reads
            if (annotations[sample_n]['PAIRED_END'] == 'Y' and
                    annotations[sample_n]['FASTQ_PATH_PAIR']):
                rw_reads = annotations[sample_n]['FASTQ_PATH_PAIR'].split(',')
                slug = 'upload-fastq-paired'
                input_['src1'] = fw_reads
                input_['src2'] = [os.path.join(genialis_seq_dir, f) for f in rw_reads]
                file_path = input_['src1'] + input_['src2']

            # Single-end reads
            else:
                slug = 'upload-fastq-single'
                input_['src'] = fw_reads
                file_path = input_['src']

            data = resolwe.run(slug,
                               input=input_,
                               descriptor=descriptor,
                               descriptor_schema=descriptor_schema,
                               data_name=sample_n)

            if data:
                for up_file in file_path:
                    uploaded_files.append(up_file)

                sample = data.sample

                if 'sample' not in sample.descriptor:
                    sample.descriptor['sample'] = {}

                organism = ORGANISMS.get(annotations[sample_n]['ORGANISM'].upper(), '')
                if organism:
                    sample.descriptor['sample']['organism'] = organism

                sample.update_descriptor(sample.descriptor)

            else:
                logger.error("Error uploading {}".format(sample_n))

    # Set the modification timestamp
    modif_times = [os.path.getmtime(f) for f in uploaded_files]
    if modif_times:
        set_timestamp(sorted(modif_times)[-1])


def upload_reads():
    """Upload NGS reads to the Resolwe server."""
    description = """Upload single-end or paired-end NGS reads to the Resolwe server.

UPLOAD A SINGLE-END FASTQ FILE:
resolwe-upload-reads -r sample1.fastq.gz

UPLOAD A SET OF MULTI-LANE FASTQ FILES:
resolwe-upload-reads -r sample1_lane1.fastq.gz sample1_lane2.fastq.gz

UPLOAD A PAIR OF PAIRED-END READS FILES:
resolwe-upload-reads -r1 sample1_mate1.fastq.gz -r2 sample1_mate2.fastq.gz

UPLOAD ALL SINGLE-END READS IN A WORKING DIRECTORY:
for reads_file in *.fastq.gz
do
   resolwe-upload-reads -r ${reads_file}
done
"""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=description)

    parser.add_argument('-a', '--address', default='https://torta.bcm.genialis.com',
                        help='Resolwe server address')
    parser.add_argument('-e', '--email', default='admin', help='User name')
    parser.add_argument('-p', '--password', default='admin', help='User password')
    parser.add_argument('-c', '--collection', nargs='*', type=int, help='Collection ID(s)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose reporting')
    parser.add_argument('-r', metavar='READS-LANE-X', nargs='*',
                        help='Single-end reads (<read1_lane1 read1_lane2, ..>)')
    parser.add_argument('-r1', metavar='MATE-1-LANE-X', nargs='*',
                        help='Paired-end reads mate1 (<mate1_lane1 mate1_lane2, ..>)')
    parser.add_argument('-r2', metavar='MATE-2-LANE-X', nargs='*',
                        help='Paired-end reads mate2 (<mate1_lane1 mate1_lane2, ..>)')

    args = parser.parse_args()

    if args.verbose:
        resdk_logger.start_logging()

    if not (args.r or (args.r1 and args.r2)) or (args.r and (args.r1 or args.r2)):
        parser.print_help()
        print("\nERROR: define either -r or -r1 and -r2.\n")
        exit(1)

    if not args.r and len(args.r1) != len(args.r2):
        parser.print_help()
        print("\nERROR: -r1 and -r2 file list length must match\n")
        exit(1)

    resolwe = Resolwe(args.email, args.password, args.address)

    if args.r:
        if all(os.path.isfile(file) for file in args.r):
            resolwe.run('upload-fastq-single', {'src': args.r}, collections=args.collection)
        else:
            print("\nERROR: Incorrect file path(s).\n")
            exit(1)
    else:
        if (all(os.path.isfile(file) for file in args.r1) and
                all(os.path.isfile(file) for file in args.r2)):
            resolwe.run('upload-fastq-paired', {'src1': args.r1, 'src2': args.r2},
                        collections=args.collection)
        else:
            print("\nERROR: Incorrect file path(s).\n")
            exit(1)


def update_knowledge_base():
    """Update the knowledge base from an external file."""
    description = """Updates the remote knowledge base from an external file."""

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=description)

    parser.add_argument('-a', '--address', default='https://torta.bcm.genialis.com',
                        help='Resolwe server address')
    parser.add_argument('-e', '--email', default='admin', help='User name')
    parser.add_argument('-p', '--password', default='admin', help='User password')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose reporting')
    parser.add_argument('features', help='ZIP file containing feature descriptions')

    args = parser.parse_args()

    if args.verbose:
        resdk_logger.start_logging()

    resolwe = Resolwe(args.email, args.password, args.address)

    errors = 0
    updated = 0
    with zipfile.ZipFile(args.features) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith('.tab'):
                continue

            logger.info('Importing features from "{}"...'.format(entry.filename))

            reader = csv.DictReader(archive.open(entry), delimiter=str('\t'))
            for row in reader:
                aliases = row['Aliases'].strip()
                if not aliases or aliases == '-':
                    aliases = []
                else:
                    aliases = aliases.split(',')

                try:
                    for retry in range(3):  # pylint: disable=unused-variable
                        try:
                            resolwe.feature.post({
                                'source': row['Source'],
                                'feature_id': row['ID'],
                                'species': row['Species'],
                                'type': row['Type'],
                                'sub_type': SUBTYPE_MAP.get(row['Gene type'], 'other'),
                                'name': row['Name'],
                                'full_name': row['Full name'],
                                'description': row['Description'],
                                'aliases': aliases
                            })
                            break
                        except slumber.exceptions.HttpServerError as error:
                            # Retry on server errors.
                            continue

                    updated += 1
                except slumber.exceptions.HttpClientError as error:
                    logger.warning("Failed to update feature '{}:{}':\n{}\n{}".format(
                        row['Source'],
                        row['ID'],
                        row,
                        error.response.content  # pylint: disable=no-member
                    ))
                    errors += 1

    if errors:
        logger.warning("Encountered {} errors during import.".format(errors))

    logger.info("Updated {} features.".format(updated))
