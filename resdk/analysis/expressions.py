"""Expressions analysis."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.resources.utils import (
    get_data_id, get_resolwe, get_resource_collection, get_samples, is_collection, is_relation,
)

__all__ = ('cuffquant', 'cuffnorm')


def cuffquant(resource, gff, genome=None, mask_file=None, library_type=None,
              multi_read_correct=None, threads=None):
    """Run Cuffquant_ for selected cuffquats.

    This method runs `Cuffquant`_ process with ``annotation`` specified
    in arguments. Library type is by defalt fr-unsstranded. Other
    parameters: genome, mask_file, multi_reads_correct and threads are
    optional.

    .. _Cuffquant:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-cuffquant

    :param gff: id of annotation file is given
    :type gff: int or `~resdk.resources.data.Data`
    :param genome: id of genome file is given to run bias detection and
        correction algorithm
    :type genome: int or `~resdk.resources.data.Data`
    :param mask_file: id of mask file is given
    :type mask_file: int or `~resdk.resources.data.Data`
    :param str library_type: options are fr-unstranded, fr-firststrand,
        fr-secondstrand
    :param bool multi_read_correct: do initial estimation procedure to
        more accurately weight reads with multiple genome mappings
    :param int threads: use this many processor threads

    """
    results = []
    for sample in get_samples(resource):
        inputs = {
            'alignment': sample.get_bam().id,
            'gff': get_data_id(gff),
        }

        if genome is not None:
            inputs['genome'] = genome

        if mask_file is not None:
            inputs['mask_file'] = mask_file

        if library_type is not None:
            inputs['library_type'] = library_type

        if multi_read_correct is not None:
            inputs['multi_read_correct'] = multi_read_correct

        if threads is not None:
            inputs['threads'] = threads

        cuffquant_obj = sample.resolwe.get_or_run(slug='cuffquant', input=inputs)
        sample.add_data(cuffquant_obj)
        results.append(cuffquant_obj)

    return results


def cuffnorm(resource, annotation, use_ercc=None, threads=None):
    """Run Cuffnorm_ for selected cuffquats.

    This method runs `Cuffnorm`_ process on ``resource`` with
     ``annotation``, ``useERCC`` and ``threads`` parameters specified
     in arguments.

    .. _Cuffnorm:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-upload-expression-cuffnorm

    :param resource: resource on which cuffnorm will be run
    :param annotation: annotation object used in cuffnorm
    :type annotation: int or `~resdk.resources.data.Data`
    :param bool useERCC: use ERRCC spike-in controls for normalization
    :param int threads: use this many threads to align reads
        (default: ``1``)

    """
    relation_filter = {}
    collection_id = get_resource_collection(resource)
    if collection_id:
        relation_filter['collection'] = collection_id

    samples = get_samples(resource)

    input_objects = [annotation]
    input_objects.extend(samples)
    resolwe = get_resolwe(*input_objects)

    cuffquants = [get_data_id(sample.get_cuffquant()) for sample in samples]

    labels = []
    replicates = []
    replicates_ids = {}
    for sample in samples:
        relations = resolwe.relation.filter(
            type='group',
            label='replicates',
            entity=[sample.id],
            **relation_filter
        )

        if len(relations) == 1:
            relation = relations[0]
        else:
            raise LookupError(
                "Cannot determine unique group relation with label `replicates` for the "
                "following sample: {}".format(sample.name)
            )

        if relation.id not in replicates_ids:
            replicates_ids[relation.id] = str(len(replicates_ids))
        replicates.append(replicates_ids[relation.id])

        if str(relation.id) not in labels:
            labels.append(str(relation.id))

    inputs = {
        'cuffquant': cuffquants,
        'replicates': replicates,
        'annotation': get_data_id(annotation),
        'labels': labels,
    }

    if use_ercc is not None:
        inputs['useERCC'] = use_ercc

    if threads is not None:
        inputs['threads'] = threads

    cuffnorm_obj = resolwe.get_or_run(slug='cuffnorm', input=inputs)

    if is_collection(resource):
        resource.add_data(cuffnorm_obj)
    elif is_relation(resource):
        resource.collection.add_data(cuffnorm_obj)

    return cuffnorm_obj
