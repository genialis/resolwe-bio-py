"""Chip Seq analysis."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.resources.utils import get_data_id, get_resource_collection, get_samples, is_sample

__all__ = ('macs', 'rose2')


def is_background(sample):
    """Return ``True`` if given sample is background and ``False`` otherwise."""
    background_relations = sample.resolwe.relation.filter(
        type='compare',
        label='background',
        entity=sample.id,
        position='background'
    )
    return len(background_relations) > 0


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
            inputs['treatment'] = sample.get_bam().id

            if use_background:
                if is_background(sample) and not is_sample(single_resource):
                    # Don't run process on the background sample,
                    # but let it fail if it is run directly on sample
                    continue

                background = sample.get_background(**background_filter)
                inputs['control'] = background.get_bam().id

            macs_obj = sample.resolwe.get_or_run(slug='macs14', input=inputs)
            sample.add_data(macs_obj)
            results.append(macs_obj)

    return results


def rose2(resource, use_background=True, genome='HG19', tss=None, stitch=None, beds=None):
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
    :param str genome: Genome used in the process (options are HG18,
        HG19, MM8, MM9, MM10, RN4 and RN6), default is ``HG19``
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
            valid_genomes = ['HG18', 'HG19', 'MM8', 'MM9', 'MM10', 'RN4', 'RN6']
            if genome not in valid_genomes:
                raise KeyError('Invalid `genome`, please use one of the following: '
                               '{}'. format(', '.join(valid_genomes)))

            inputs = {
                'genome': genome,
                'rankby': sample.get_bam().id,
            }

            if tss is not None:
                inputs['tss'] = tss

            if stitch is not None:
                inputs['stitch'] = stitch

            if use_background:
                if is_background(sample) and not is_sample(single_resource):
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
