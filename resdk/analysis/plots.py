"""Plot analysis."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.resources.utils import get_data_id, get_resolwe, get_samples, is_collection, is_relation

__all__ = ('bamplot', )


def bamplot(resource, genome, input_gff=None, input_region=None, stretch_input=None, color=None,
            sense=None, extension=None, rpm=None, yscale=None, names=None, plot=None, title=None,
            scale=None, bed=None, multi_page=None):
    """Run ``bamplot`` on the resource.

    This method runs `bamplot`_ with bams, genome and gff or region
    specified in arguments.

    .. _bamplot:
        http://resolwe-bio.readthedocs.io/en/latest/catalog-definitions.html#process-bamplot

    :param list resource: resource from which bam objects will be get
    :param str genome: Genome used in the process (options are HG18,
        HG19, MM9 and MM10)
    :param input_gff: id of annotation file is given
    :type input_gff: int or `~resdk.resources.data.Data`
    :param str input_region: enter a genomic region
    :param int stretch_input: stretch the input regions to a minimum
        length
    :param str color: enter a colon separated list of colors
    :param str sense: map to forward, reverse or'both strand,
        default maps to ``both``
    :param int extension: extends reads by n bp, dfault value is 200bp
    :param bool rpm: normalizes density to reads per million (rpm),
        default is ``False``
    :param str yscale: choose either relative or uniform y axis scaling,
        default is ``relative scaling``
    :param str names: a comma separated list of names for your bams
    :param str plot: choose all lines on a single plot or multiple plots
    :param str title: title for the output plot(s), default will be the
        coordinate region
    :param str scale: a comma separated list of multiplicative scaling
        factors for your bams, default is ``None``
    :param list beds: subset of bed files to run process on, if empty
        processes for all bed files will be run
    :param bool multi_page: if flagged will create a new pdf for each
        region

    """
    input_objects = []

    if not input_gff and not input_region:
        raise KeyError('Please specify `input_gff` or `input_region.')
    if input_gff and input_region:
        raise KeyError('Please specify `input_gff` or `input_region.')

    valid_genomes = ['HG18', 'HG19', 'MM8', 'MM9', 'MM10']
    if genome not in valid_genomes:
        raise KeyError('Invalid `genome`, please use one of the following: '
                       '{}'. format(', '.join(valid_genomes)))

    bams = [sample.get_bam() for sample in get_samples(resource)]
    input_objects.extend(bams)
    bams = [get_data_id(bam) for bam in bams]

    inputs = {
        'genome': genome,
        'bam': bams,
    }

    if color is not None:
        inputs['color'] = color

    if sense is not None:
        inputs['scale'] = scale

    if extension is not None:
        inputs['extension'] = extension

    if rpm is not None:
        inputs['rpm'] = rpm

    if yscale is not None:
        inputs['yscale'] = yscale

    if names is not None:
        inputs['names'] = names

    if plot is not None:
        inputs['plot'] = plot

    if title is not None:
        inputs['title'] = title

    if scale is not None:
        inputs['scale'] = scale

    if multi_page is not None:
        inputs['multi_page'] = multi_page

    if input_gff is not None:
        input_objects.append(input_gff)
        inputs['input_gff'] = get_data_id(input_gff)

    if input_region is not None:
        inputs['input_region'] = input_region

    if bed is not None:
        if isinstance(bed, list):
            input_objects.extend(bed)
            inputs['bed'] = [get_data_id(bed_obj) for bed_obj in bed]
        else:
            input_objects.append(bed)
            inputs['bed'] = [get_data_id(bed)]

    resolwe = get_resolwe(*input_objects)

    bamplot_obj = resolwe.get_or_run(slug='bamplot', input=inputs)

    if is_collection(resource):
        resource.add_data(bamplot_obj)
    elif is_relation(resource):
        resource.collection.add_data(bamplot_obj)

    return bamplot_obj
