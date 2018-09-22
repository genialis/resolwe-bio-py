"""Upload base."""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from resdk.data_upload.samplesheet import FileImporter

__all__ = ('upload_and_annotate',)

logger = logging.getLogger(__name__)


def upload_and_annotate(collection, samplesheet_path, basedir, process):
    """Upload data files to the Resolwe server, and annotate.

    The sample sheet (.tsv or .xls*) location is specifed by `samplesheet_path`.
    The reads files should be located at `basedir`/'filepath', where 'filepath'
    is specified for each file in the sample sheet.

    :param collection: collection to contain the uploaded reads
    :param samplesheet_path: filepath of the sample annotation spreadsheet
    :param basedir: base directory of the source files
    :param process: data upload function to use (returns failed sample names)
    """
    # Read and validate the annotation template
    logger.debug(
        "\nChecking the sample annotation spreadsheet at:\n%s",
        samplesheet_path
    )
    samplesheet = FileImporter(samplesheet_path)
    err_names = samplesheet.invalid_names

    # Run the upload process
    failed_uploads = process(
        sample_dict=samplesheet.valid_samples,
        basedir=basedir,
        collection=collection,
        pre_invalid=err_names
    )

    # Report failures
    logger.error(
        "The following samples could not be uploaded: %s.", ', '.join(failed_uploads)
    )

    # Annotate the samples
    collection.annotate(samplesheet)
    collection.update()
