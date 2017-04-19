"""Chip Seq analysis."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.resources.utils import get_data_id, get_samples

__all__ = ('bowtie2', 'hisat2')


def bowtie2(resource, genome):
    """Run bowtie2 aligner on given resource.

    Aligne reads files of given resource to the given genome using the
    ``bowtie2`` aligner. If reads were already aligned, existing objects
    will be returned.

    :param resource: resource of which reads will be aligned
    :param genome: data object with genome that will be used
    :type genome: int or `~resdk.resources.data.Data`

    """
    results = []

    if not isinstance(resource, list):
        resource = [resource]

    for single_resource in resource:

        for sample in get_samples(single_resource):
            inputs = {
                'reads': sample.get_reads().id,
                'genome': get_data_id(genome),
            }

            aligned = sample.resolwe.get_or_run(slug='alignment-bowtie2', input=inputs)
            sample.add_data(aligned)
            results.append(aligned)

    return results


def hisat2(resource, genome):
    """Run hisat2 aligner on given resource.

    Aligne reads files of given resource to the given genome using the
    ``hisat2`` aligner. If reads were already aligned, existing objects
    will be returned.

    :param resource: resource of which reads will be aligned
    :param genome: data object with genome that will be used
    :type genome: int or `~resdk.resources.data.Data`

    """
    results = []

    if not isinstance(resource, list):
        resource = [resource]

    for single_resource in resource:

        for sample in get_samples(single_resource):
            inputs = {
                'reads': sample.get_reads().id,
                'genome': get_data_id(genome),
            }

            aligned = sample.resolwe.get_or_run(slug='alignment-hisat2', input=inputs)
            sample.add_data(aligned)
            results.append(aligned)

    return results
