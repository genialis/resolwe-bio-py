"""Command line scripts."""
# pylint: disable=logging-format-interpolation
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import glob
import logging
import os
import resdk
import xlrd

__all__ = ('upload_and_annotate',)

COLUMNS = {
    'SAMPLE_NAME',
    'FASTQ_R1',
    'FASTQ_R2',
    'SEQ_TYPE',
    'COLLECTION',
    'ANNOTATOR',
    'SOURCE',
    'ORGANISM',
    'CELL_TYPE',
    'STRAIN',
    'TISSUE',
    'AGE',
    'GENOTYPE',
    'MOLECULE',
    'LIBRARY_STRATEGY',
    'EXTRACTION_PROTOCOL',
    'GROWTH_PROTOCOL',
    'TREATMENT_PROTOCOL',
    'LIBRARY_CONSTRUCTION_PROTOCOL',
    'BARCODE',
    'ANTIBODY',
    'FACILITY',
    'OTHER_CHAR_1',
    'OTHER_CHAR_2',
}

ORGANISM = {
    'Homo sapiens',
    'Mus musculus',
    'Dictyostelium discoideum',
    'Rattus norvegicus',
}

MOLECULE = {
    'total RNA',
    'polyA RNA',
    'cytoplasmic RNA',
    'nuclear RNA',
    'genomic DNA',
    'protein',
    'other',
}

OPTIONAL = {
    'LIBRARY_STRATEGY',
    'TISSUE',
    'AGE',
    'OTHER_CHAR_1',
    'OTHER_CHAR_2',
}

# Scripts logger
logger = logging.getLogger(__name__)


class FileImporter(object):
    """Import annotation spreadsheet."""

    def __init__(self, annotation_path):
        self.sample_list = []
        self.path = annotation_path
        self._is_file()
        self.populate_samples()
        self.validate()

    def _is_file(self):
        """Check is the provided path exists."""
        if not os.path.isfile(self.path):
            raise LookupError(
                "The provided annotation file '{}' does not exist. Please provide the script "
                "with the correct annotation file.".format(self.path)
            )

    def extension(self):
        """Find spreadsheet file extension."""
        return os.path.splitext(self.path)[1]

    def _read_xlrd(self):
        """Read Excel spreadsheet annotation file."""
        workbook = xlrd.open_workbook(self.path)
        worksheet = workbook.sheets()[0]
        header = worksheet.row_values(0)
        for rownum in range(1, worksheet.nrows):
            row = worksheet.row_values(rownum)
            entries = {}
            for i, value in enumerate(row):
                if isinstance(value, float):
                    entries[header[i]] = str(value)
                else:
                    entries[header[i]] = value
            self.sample_list.append(entries)

    def _read_text_file(self):
        """Read simple spreadsheet annotation file."""
        with open(self.path, 'rb') as sample_sheet:
            self.sample_list = list(csv.DictReader(sample_sheet, delimiter='\t'))

    def populate_samples(self):
        """Check the format of annotation file and asign read function."""
        if self.extension() in ['.xls', '.xlsx', '.xlsm']:
            self._read_xlrd()
        elif self.extension() in ['.txt', '.tab', '.tsv']:
            self._read_text_file()
        else:
            raise TypeError(
                "Annotation spreadsheet extension `{}` not recognised."
                " Options are: `.xls`, `.xlsx`, `.xlsm`, `.txt`, "
                "`.tab`, `.tsv`.".format(self.extension())
            )

    def validate(self):
        """Validate the annotation spreadsheet file."""
        for sample in self.sample_list:
            diff1 = COLUMNS - set(sample.keys())
            diff2 = set(sample.keys()) - COLUMNS
            err_msg = (
                "Headers `{0}` {1}. You should use the"
                " headers from Annotation_spreadsheet.xlsm found on "
                "https://github.com/genialis/resdk-scripts/tree/master/"
                "BCM_project/upload_scripts."
            )
            if diff1:
                raise NameError(
                    err_msg.format(', '.join(diff1), "are missing")
                    )
            if diff2:
                raise NameError(
                    err_msg.format(', '.join(diff2), "not recognised")
                    )

            for var_name, VAR in [('organism', ORGANISM), ('molecule', MOLECULE)]:
                var = sample[var_name.upper()]
                if var and var not in VAR:
                    raise ValueError(
                        "`{0}` is not a valid {1}. Valid"
                        " {2}s are found in Annotation_spreadsheet"
                        ".xlsm sheet Options. Spreadsheet can be found on "
                        "https://github.com/genialis/resdk-scripts/tree/master"
                        "/BCM_project/upload_scripts.".format(var, var_name.upper(), var_name)
                    )


class Sample(object):
    """Create a Sample like object."""

    def __init__(self, sample):
        self.name = sample['SAMPLE_NAME']
        self.slug = sample['SAMPLE_NAME']
        self.collection = sample['COLLECTION']
        self.path = sample['FASTQ_R1']
        self.path2 = sample['FASTQ_R2']
        self.seq_type = sample['SEQ_TYPE']
        self.reads_annotation = {
            'experiment_type': self.seq_type,
            'protocols': {
                'extract_protocol': sample['EXTRACTION_PROTOCOL'],
                'library_prep': sample['LIBRARY_CONSTRUCTION_PROTOCOL'],
                'treatment_protocol': sample['TREATMENT_PROTOCOL'],
                'growth_protocol': sample['GROWTH_PROTOCOL'],
                'antibody_information': {
                    'manufacturer' : sample['ANTIBODY']
                }
            },
            'reads_info': {
                'barcode': sample['BARCODE'],
                'facility': sample['FACILITY']
            }
        }
        self.molecule = sample['MOLECULE']
        self.organism = sample['ORGANISM']
        self.sample_annotation = {
            'sample': {
                'annotator': sample['ANNOTATOR'],
                'cell_type': sample['CELL_TYPE'],
                'source': sample['SOURCE'],
                'strain': sample['STRAIN'],
                'genotype': sample['GENOTYPE'],
                'optional_char': []
            }
        }
        if self.organism:
            self.sample_annotation['sample']['organism'] = self.organism
        if self.molecule:
            self.sample_annotation['sample']['molecule'] = self.molecule
        for option in OPTIONAL:
            if sample[option]:
                self.sample_annotation['sample']['optional_char'].append(
                    '{0}:{1}'.format(option, sample[option]))

    def tag_community(self):
        """Prepare community tags."""
        seq = self.seq_type.lower()
        if 'rna' in seq:
            community = 'community:rna-seq'
        elif 'chip' in seq:
            community = 'community:chip-seq'
        else:
            community = None
        return community


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Upload raw data.')
    parser.add_argument('--sample_sheet', type=str, help='Sample sheet', required=True)
    parser.add_argument('--username', type=str, help='Username', required=True)
    parser.add_argument('--password', type=str, help='Password', required=True)
    parser.add_argument('--URL', type=str, help='URL', required=True)
    return parser.parse_args()


def get_or_create_collection(resolwe, coll_name):
    """Check if Collection with given name already exists. Create new Collection if not."""

    collections = resolwe.collection.filter(name=coll_name)
    if len(collections) > 1:
        raise LookupError(
            "More than one collection with name '{}' already exists on the platform!"
            "".format(coll_name)
        )

    if not collections:
        collection = resdk.resources.Collection(resolwe=resolwe)
        collection.name = coll_name
        collection.save()
    else:
        collection = resolwe.collection.get(name=coll_name)

    return collection


def upload_and_annotate():
    """Upload and annotate NGS reads.

    Usage:

    upload_and_annotate \
      --sample_sheet <path_to_annotation_spreadsheet> \
      --username <Genialis_username> \
      --password <Genialis_password> \
      --URL <server_url>

    Accepted annotation spreadsheet extensions:
    `.xls`, `.xlsx`, `.xlsm`, `.txt`, `.tab`, `.tsv`
    """

    args = parse_arguments()

    res = resdk.Resolwe(args.username, args.password, args.URL)
    resdk.start_logging()

    # Read  and validate the annotation template
    annotation = FileImporter(args.sample_sheet)

    for sample in annotation.sample_list:
        read_file = Sample(sample)

        # Create or get a collection if existing
        coll = read_file.collection
        if coll:
            collection = get_or_create_collection(res, coll)

        path = read_file.path
        path2 = read_file.path2
        err_path = []
        if path and path2:
            src1 = path.split(',')
            src2 = path2.split(',')
            err_path = [s for s in src1 + src2 if not glob.glob(s)]
            if err_path:
                print("Incorrect file paths: {}".format(err_path))
                continue
            print('Uploading data for sample: {}'.format(read_file.name))
            reads = res.run('upload-fastq-paired',
                            input={
                                'src1': src1,
                                'src2': src2})

        elif path and not path2:
            src = path.split(',')
            err_path = [s for s in src if not glob.glob(s)]
            if err_path:
                print("Incorrect file paths: {}".format(err_path))
                continue
            print('Uploading data for sample: {}'.format(read_file.name))
            reads = res.run('upload-fastq-single',
                            input={'src': src})

        else:
            print("Warning: There are no file paths or there is only "
                  "the reverse reads path provided for sample {} so "
                  "it was not uploaded. You should fix or provide the "
                  "correct file paths".format(read_file.name))
            continue

        if coll:
            collection.add_data(reads)

        # Rename reads object
        reads.name = read_file.name

        # Provide reads annotation
        reads.descriptor_schema = 'reads'
        reads.descriptor = read_file.reads_annotation
        reads.save()

        # Get sample object
        reads.sample.delete(force=True)
        main_sample = res.sample.create(name=read_file.name)
        main_sample.add_data(reads)

        # Rename main_sample
        main_sample.name = read_file.name

        # Provide sample annotation and tag community
        main_sample.descriptor_schema = 'sample'
        main_sample.descriptor = read_file.sample_annotation
        if read_file.tag_community():
            main_sample.tags.append(read_file.tag_community())
        main_sample.save()

        # Confirm that the sample is annotated and attach it to the collection
        main_sample.confirm_is_annotated()
        if coll:
            collection.add_samples(main_sample)
