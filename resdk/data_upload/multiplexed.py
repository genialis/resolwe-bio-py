"""Upload multiplexed reads."""
from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import logging
import os
from collections import OrderedDict

from resdk.data_upload.base import upload_and_annotate
from resdk.data_upload.utils import process_complete
from resdk.exceptions import ResolweServerError

__all__ = ('upload_demulti',)

logger = logging.getLogger(__name__)


def upload_demulti(collection, samplesheet_path, basedir=''):
    """Upload multiplexed reads to the Resolwe server, demultiplex, and annotate.

    The reads files (.qseq) should be located at `basedir`/'filepath', where
    'filepath' is specified for each file in the sample sheet.

    Sample-creation and annotation cannot occur until the demultiplexing process
    has finished. Complete sample annotation by rerunning `upload_demulti` on
    the same collection containing the demultiplexed data objects, using the
    same sample annotation spreadsheet.

    :param collection: collection to contain the uploaded reads
    :param samplesheet_path: filepath of the sample annotation spreadsheet
    :param basedir: base directory of the reads and barcodes files
    """
    upload_and_annotate(collection, samplesheet_path, basedir, _upload_multi_samples)


def _upload_multi_samples(sample_dict, basedir, collection, pre_invalid):
    """Upload and demultiplex groups of samples."""
    sample_groups = _group_multiplexed(sample_dict.values())
    attempted = OrderedDict(
        (qseq, _demultiplex_samples(sample_groups[qseq], basedir, collection, pre_invalid))
        for qseq in sample_groups
    )
    uploaded = OrderedDict((qseq, data) for qseq, data in attempted.items() if data)
    failed_uploads = [
        {sample.name for sample in sample_groups[qseq]}
        for qseq, data in attempted.items() if not data
    ]
    pre_invalid.update(*failed_uploads)

    # Create the child samples
    for qseq in uploaded:
        ex = _demultiplex_error(uploaded[qseq])
        if not ex:
            _create_multi_sample(uploaded[qseq], sample_groups[qseq])
        elif ex.startswith("Demultiplex process"):
            logger.error(ex, qseq)
        else:
            logger.error(ex)
            pre_invalid.update({sample.name for sample in sample_groups[qseq]})
    return pre_invalid


def _group_multiplexed(sample_list):
    """Group samples sharing the same reads file."""
    grouped = itertools.groupby(sample_list, key=lambda x: x.path)
    return {key: list(group) for key, group in grouped}


def _demultiplex_samples(sample_list, basedir, collection, pre_invalid):
    """Validate, upload, and demultiplex a sample group.

    Returns the data object if successful, or None if errored.
    """
    try:
        _validate_multiplexed(collection, sample_list, pre_invalid)
        mapfile = _generate_mapfile(sample_list, sample_list[0].path)
        demulti_result = _start_demultiplex(sample_list, mapfile, basedir, collection)
    except ValueError as ex:
        logger.error(ex)
        demulti_result = None
    except (FileNotFoundError, AttributeError, ResolweServerError):
        logger.error(
            "Unable to demultiplex samples '%s'. Invalid filepath.",
            "', '".join({sample.name for sample in sample_list})
        )
        demulti_result = None
    except FileExistsError as ex:
        logger.error(ex)
        demulti_result = _recover_demultiplexed(sample_list[0].path, collection)
        pre_invalid.update({sample.name for sample in sample_list})

    # Clean up barcode mapping file
    try:
        os.remove(mapfile)
    except (FileNotFoundError, UnboundLocalError, TypeError):
        logger.debug("Unable to remove barcode mapping file for: %s", sample_list[0].path)

    return demulti_result


def _validate_multiplexed(collection, samples, pre_invalid):
    """Check if the sample is valid to upload to this collection."""
    names = {sample.name for sample in samples}
    sample0 = samples[0]
    readsfile = os.path.basename(sample0.path)
    barfile = os.path.basename(sample0.path3)

    skip_msg = "Skipping upload of '{}': ".format(readsfile)

    # Don't upload if the annotation info is invalid
    if any(name in pre_invalid for name in names):
        raise ValueError(skip_msg + "Invalid annotation.")

    # Check if the primary filepath was given
    if not readsfile:
        raise ValueError(skip_msg + "No forward reads given.")

    # Check if the data is already in the collection
    if readsfile in {data.name for data in collection.data}:
        raise FileExistsError(skip_msg + "File already uploaded.")

    # Check if the barcodes filepath was given
    if not barfile:
        raise ValueError(skip_msg + "No barcodes file given.")

    # Check if at least one file has the proper filetype
    # TODO: Remove this when validation is fixed in the resolwe-bio process
    if not all(['.qseq' in readsfile, '.qseq' in barfile]):
        raise ValueError(
            skip_msg + "Invalid file extension(s). "
            "(Options: {})".format('.qseq'))

    # Check if all included samples have barcodes
    if not all(sample.barcode for sample in samples):
        raise ValueError(skip_msg + "Missing barcode.")

    # Passed all checks!


def _start_demultiplex(sample_list, mapfile, basedir, collection):
    """Upload and demultiplex single-end or paired-end reads."""
    res = collection.resolwe
    sample0 = sample_list[0]
    path = sample0.path
    path2 = sample0.path2
    path3 = sample0.path3

    # Upload and demultiplex the reads
    if path and path2:
        logger.debug('Uploading multiplexed data: %s', path)
        qseq_reads = res.run('upload-multiplexed-paired',
                             input={
                                 'reads': os.path.join(basedir, path),
                                 'reads2': os.path.join(basedir, path2),
                                 'barcodes': os.path.join(basedir, path3),
                                 'annotation': mapfile,
                             },
                             collections=[collection])

    elif path and not path2:
        logger.debug('Uploading multiplexed data: %s', path)
        qseq_reads = res.run('upload-multiplexed-single',
                             input={
                                 'reads': os.path.join(basedir, path),
                                 'barcodes': os.path.join(basedir, path3),
                                 'annotation': mapfile,
                             },
                             collections=[collection])

    return qseq_reads


def _generate_mapfile(sample_list, filepath):
    """Create a barcodes mapping file for demultiplexing."""
    path = filepath.split('.')[0]
    mapfile = '{}.map.tsv'.format(path)
    try:
        with open(mapfile, 'w') as tsv:
            tsv.write('\n'.join(
                '{}\t{}'.format(sample.barcode, sample.name) for sample in sample_list
            ))
    except OSError:
        os.remove(mapfile)
        mapfile = None
        logger.error("Barcode mapping file not generated for: %s", filepath)
    return mapfile


def _create_multi_sample(multi_reads, sample_list):
    """Create samples from uploaded and demultiplexed reads."""
    qseq_id = multi_reads.id
    demulti_list = multi_reads.resolwe.data.filter(parents=qseq_id)
    for sample in sample_list:
        label = '{}_{}'.format(sample.name, sample.barcode)
        demulti_reads = [s for s in demulti_list if label in s.name][0]

        demulti_reads.sample.delete(force=True)
        main_sample = demulti_reads.resolwe.sample.create(name=sample.name)
        main_sample.add_data(demulti_reads)
        main_sample.save()
        demulti_reads.collections[0].add_samples(main_sample)


def _recover_demultiplexed(qseq, collection):
    """Query a multiplexed data object and check if it is done.

    Returns the data object if complete, or None otherwise.
    """
    all_multiplexed = collection.data.filter(type='data:multiplexed')
    data = all_multiplexed.filter(name=qseq)
    if not data:
        message = "Multiplexed data '%s' not found."
    elif len(data) > 1:
        message = "Multiplexed data '%s' is ambiguously duplicated."
    else:
        message = _demultiplex_error(data[0])
    if message:
        logger.error(message, qseq)
        return None
    else:
        return data[0]


def _demultiplex_error(data):
    """Check the processing status of a demultiplexing object.

    Returns the error message, or None.
    """
    try:
        if process_complete(data):
            return None
        else:
            return "Demultiplex process not yet complete for '%s'."
    except ValueError as ex:
        return ex
