"""Chip Seq analysis."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.resources.utils import get_data_id, get_resource_collection, get_samples, is_sample

__all__ = ('bamsplit', 'macs', 'rose2')


def bamsplit(resource, header=None, header2=None):
    """Run ``Bam split`` process on the resource.

    This method runs `Bam split`_ process on the resource. The process
    will be run on all samples in the resource. Samples' alignment data
    object must be valid. Valid alignment data objects are those that
    were aligned to a hybrid genome with a valid build. Valid builds
    are: 'hg19_dm6' and 'mm10_dm6'.

    .. _Bam split:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-bam-split

    :param resource: resource on which bam-split will be run
    :param header: SAM header data object for the primary BAM
    :type header: `~resdk.resources.data.Data`
    :param header2: SAM header data object for the secodary BAM
    :type header: `~resdk.resources.data.Data`

    """
    inputs = {}

    if header:
        inputs['header'] = header

    if header2:
        inputs['header2'] = header2

    results = []

    if not isinstance(resource, list):
        resource = [resource]

    for single_resource in resource:
        for sample in get_samples(single_resource):
            inputs['bam'] = sample.get_bam().id
            primary_bam = sample.resolwe.run(
                slug='bam-split', input=inputs, collections=sample.collections
            )
            results.append(primary_bam)

    return results


def macs(resource, use_background=True, p_value=None):
    """Run ``MACS 1.4`` process on the resource.

    This method runs `MACS 1.4`_ process with ``p-value`` specified in
    arguments and ``bam`` file from the sample.

    If ``use_background`` argument is set to ``True``, ``bam`` file from
    background sample is passed to the process as the control.

    .. _MACS 1.4:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-macs14

    :param bool use_background: if set to ``True``, background sample
        will be used in the process
    :param float p_value: p-value used in the process

    """
    inputs = {}
    if p_value is not None:
        inputs['pvalue'] = p_value

    results = []

    if not isinstance(resource, list):
        resource = [resource]

    for single_resource in resource:

        background_filter = {}
        if use_background:
            collection_id = get_resource_collection(single_resource)
            if collection_id:
                background_filter['collection'] = collection_id

        for sample in get_samples(single_resource):
            inputs['treatment'] = sample.get_primary_bam(fallback_to_bam=True).id

            if use_background:
                if sample.is_background and not is_sample(single_resource):
                    # Don't run process on the background sample,
                    # but let it fail if it is run directly on sample
                    continue

                background = sample.get_background(**background_filter)
                inputs['control'] = background.get_primary_bam(fallback_to_bam=True).id

            macs_obj = sample.resolwe.get_or_run(slug='macs14', input=inputs)
            sample.add_data(macs_obj)
            results.append(macs_obj)

    return results


def rose2(resource, use_background=True, tss=None, stitch=None, beds=None):
    """Run ``ROSE 2`` process on the resource.

    This method runs `ROSE2`_ process with ``tss_exclusion`` and
    ``stitch`` parameters specified in arguments.

    Separate process is run for each bed file on the sample. To run
    process only on subset of those files, list them in ``beds``
    argument (if only one object is given, it will be auto-wrapped in
    list, if it is not already).

    If ``use_background`` argument is set to ``True``, bam file from
    background sample is passed to the process as the control.

    .. _ROSE2:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-rose2

    :param bool use_background: if set to ``True``, background sample
        will be used in the process
    :param int tss: TSS exclusion used in process
    :param int stitch: Stitch used in process
    :param list beds: subset of bed files to run process on, if empty
        processes for all bed files will be run

    """
    results = []

    if not isinstance(resource, list):
        resource = [resource]

    for single_resource in resource:

        background_filter = {}
        if use_background:
            collection_id = get_resource_collection(single_resource)
            if collection_id:
                background_filter['collection'] = collection_id

        for sample in get_samples(single_resource):
            inputs = {
                'rankby': sample.get_bam().id,
            }

            if tss is not None:
                inputs['tss'] = tss

            if stitch is not None:
                inputs['stitch'] = stitch

            if use_background:
                if sample.is_background and not is_sample(single_resource):
                    # Don't run process on the background sample,
                    # but let it fail if it is run directly on sample
                    continue

                background = sample.get_background(**background_filter)
                inputs['control'] = background.get_bam().id

            bed_list = sample.get_macs()
            if beds is not None:
                # Convert objects to the list of their ids
                if isinstance(beds, list):
                    bed_filter = [get_data_id(bed) for bed in beds]
                else:
                    bed_filter = [get_data_id(beds)]

                bed_list = bed_list.filter(id__in=bed_filter)

            for bed in bed_list:
                inputs['input'] = bed.id

                rose = sample.resolwe.get_or_run(slug='rose2', input=inputs)
                sample.add_data(rose)
                results.append(rose)

    return results
