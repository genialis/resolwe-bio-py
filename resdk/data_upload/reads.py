"""Upload reads."""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from resdk.data_upload.base import upload_and_annotate
from resdk.exceptions import ResolweServerError

__all__ = ('upload_reads',)

logger = logging.getLogger(__name__)


def upload_reads(collection, samplesheet_path, basedir=''):
    """Upload NGS reads to the Resolwe server, and annotate.

    The sample sheet (.tsv or .xls*) location is specifed by `samplesheet_path`.
    The reads files (.fastq) should be located at `basedir`/'filepath', where
    'filepath' is specified for each file in the sample sheet.

    :param collection: collection to contain the uploaded reads
    :param samplesheet_path: filepath of the sample annotation spreadsheet
    :param basedir: base directory of the reads files
    """
    upload_and_annotate(collection, samplesheet_path, basedir, _upload_reads_samples)


def _upload_reads_samples(sample_dict, basedir, collection, pre_invalid):
    """Upload groups of samples."""
    failed_uploads = {
        _upload_sample(sample, basedir, collection, pre_invalid)
        for sample in sample_dict.values()
    }

    pre_invalid.update(failed_uploads)
    pre_invalid.discard(None)

    return pre_invalid


def _upload_sample(sample, basedir, collection, pre_invalid):
    """Validate a sample, upload the reads, and create the collection sample.

    Returns None if successful, or the sample name if errored.
    """
    try:
        _validate_upload(sample, collection, pre_invalid)
        reads = _start_upload(sample, basedir, collection)
        _create_sample(reads, sample.name)
    except (FileNotFoundError, FileExistsError, ValueError, ResolweServerError) as ex:
        logger.error(ex)
        return sample.name


def _validate_upload(sample, collection, pre_invalid):
    """Check if the sample is valid to upload to this collection."""
    readsfile = os.path.basename(sample.path)
    skip_msg = "Skipping upload of '{}': ".format(sample.name)

    # Don't upload if the annotation info is invalid
    if sample.name in pre_invalid:
        raise ValueError(skip_msg + "Invalid annotation.")

    # Check if filepaths were given
    if not readsfile:
        raise ValueError(skip_msg + "No forward reads given.")

    # Check if the data is already in the collection
    if readsfile in {data.name for data in collection.data}:
        raise FileExistsError(skip_msg + "File already uploaded.")

    # Check if at least one file has the proper filetype
    # TODO: Remove this when validation is fixed in the resolwe-bio process
    validtypes = ['.fq', '.fastq']
    if not any(ext in sample.path for ext in validtypes):
        raise ValueError(
            skip_msg + "Invalid file extension(s). "
            "(Options: {})".format(', '.join(validtypes))
        )

    # Passed all checks!


def _start_upload(sample, basedir, collection):
    """Upload single-end or paired-end reads."""
    path = _parse_paths(basedir, sample.path)
    path2 = _parse_paths(basedir, sample.path2)
    if path and path2:
        logger.debug('Uploading data for the sample: %s', sample.name)
        reads = collection.resolwe.run('upload-fastq-paired',
                                       input={'src1': path, 'src2': path2},
                                       collections=[collection])
    elif path and not path2:
        logger.debug('Uploading data for the sample: %s', sample.name)
        reads = collection.resolwe.run('upload-fastq-single',
                                       input={'src': path},
                                       collections=[collection])
    return reads


def _create_sample(reads, name):
    """Create a sample from uploaded reads."""
    reads.sample.delete(force=True)
    main_sample = reads.resolwe.sample.create(name=name)
    main_sample.add_data(reads)
    main_sample.save()
    reads.collections[0].add_samples(main_sample)


def _parse_paths(base, filepath):
    """Convert filepaths into list."""
    if filepath:
        return [os.path.join(base, s) for s in filepath.split(',')]
    else:
        return []
