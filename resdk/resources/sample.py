"""Sample resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from .collection import BaseCollection


class SampleUtilsMixin(object):
    """Mixin with utility functions for `~resdk.resources.sample.Sample` resource.

    This mixin includes handy methods for common tasks like getting
    data object of specific type from sample (or list of them, based on
    common usecase) and running analysis on the objects in the sample.

    """

    def get_reads(self, **filters):
        """Return the latest ``fastq`` object in sample.

        If there are multiple ``fastq`` objects in sample (trimmed,
        filtered, subsampled...), return the latest one. If any other of
        the ``fastq`` objects is required, one can provide additional
        ``filter`` arguments and limits search to one result.
        """
        kwargs = {
            'process_type': 'data:reads:fastq',
            'ordering': '-id',
        }
        kwargs.update(filters)

        reads = self.data.filter(**kwargs)
        # TODO: In future, implement method ``last()`` on ResolweQuery
        # and return the ResolweQuery object.

        if not reads:
            raise LookupError('Reads not found on sample {}.'.format(self))
        else:
            return reads[0]

    def get_bam(self):
        """Return ``bam`` object on the sample."""
        return self.data.get(type='data:alignment:bam')

    def get_primary_bam(self, fallback_to_bam=False):
        """Return ``primary bam`` object on the sample.

        If the ``primary bam`` object is not present and
        ``fallback_to_bam`` is set to ``True``, a ``bam`` object will
        be returned.

        """
        try:
            return self.data.get(type='data:alignment:bam:primary')
        except LookupError:
            if fallback_to_bam:
                return self.get_bam()
            else:
                raise

    def get_macs(self):
        """Return list of ``bed`` objects on the sample."""
        return self.data.filter(type='data:chipseq:callpeak:macs14')

    def get_cuffquant(self):
        """Return ``cuffquant`` object on the sample."""
        return self.data.get(type='data:cufflinks:cuffquant')

    def get_expression(self):
        """Return ``expression`` object on the sample."""
        return self.data.get(type='data:expression:')


class Sample(SampleUtilsMixin, BaseCollection):
    """Resolwe Sample resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = 'sample'

    WRITABLE_FIELDS = BaseCollection.WRITABLE_FIELDS + (
        'descriptor_completed',
    )

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: list of ``Collection``s that contain ``Sample`` (lazy loaded)
        self._collections = None
        #: list of ``Relation`` objects in ``Collection`` (lazy loaded)
        self._relations = None
        #: background ``Sample`` of the current ``Sample``
        self._background = None
        #: is this sample background to any other sample?
        self._is_background = None
        #: indicate whether `descriptor` is completed
        self.descriptor_completed = None

        super(Sample, self).__init__(resolwe, **model_data)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._collections = None
        self._relations = None
        self._background = None
        self._is_background = None

        super(Sample, self).update()

    @property
    def data(self):
        """Return list of data objects on collection."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `data` attribute.')
        if self._data is None:
            self._data = self.resolwe.data.filter(entity=self.id)

        return self._data

    @property
    def collections(self):
        """Return list of collections to which sample belongs."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `collections` attribute.')

        if self._collections is None:
            collection_ids = self._original_values.get('collections', [])
            self._collections = self.resolwe.collection.filter(id__in=collection_ids)
            if not collection_ids:
                # Make querry empty.
                self._collections._cache = []  # pylint: disable=protected-access

        return self._collections

    @property
    def relations(self):
        """Get ``Relation`` objects for this sample."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `relations` attribute.')
        if self._relations is None:
            self._relations = self.resolwe.relation.filter(entity=self.id)

        return self._relations

    def update_descriptor(self, descriptor):
        """Update descriptor and descriptor_schema."""
        self.api(self.id).patch({'descriptor': descriptor})
        self.descriptor = descriptor

    def confirm_is_annotated(self):
        """Mark sample as annotated (descriptor is completed)."""
        self.api(self.id).patch({'descriptor_completed': True})
        self.logger.info('Marked Sample %s as annotated', self.id)

    def get_background(self, fail_silently=False, **extra_filters):
        """Get background sample of the current one."""
        # XXX: This method is still needed as some samples may be
        # backgrounds in multiple collections (collection can be given
        # as extra_filters). When sample will be restricted to only be
        # in one collection, the logic from this function can be placed
        # in background property and collection query parameter removed.
        self.logger.warning('This method is deprecated and will be removed when restriction is '
                            'made that sample can only belong to single collection.')

        background_relation = list(self.resolwe.relation.filter(
            type='background',
            entity=self.id,
            label='case',
            **extra_filters
        ))

        if len(background_relation) != 1:
            if len(background_relation) > 1 and not fail_silently:
                raise LookupError("Multiple backgrounds defined for sample '{}'".format(self.name))
            elif not background_relation and not fail_silently:
                raise LookupError("No background is defined for sample '{}'".format(self.name))
            else:
                return

        for partition in background_relation[0].partitions:
            if partition['label'] == 'background' and partition['entity'] != self.id:
                return self.resolwe.sample.get(id=partition['entity'])

    @property
    def background(self):
        """Get background sample of the current one."""
        if self._background is None:
            self._background = self.get_background(fail_silently=True)
            if self._background is None:
                # Cache the result = no background is found.
                self._background = False

        if self._background:
            return self._background

    @background.setter
    def background(self, bground):
        """Set sample background."""
        def count_cases(entity, label):
            """Get a tuple (relation, number_of_cases) in a specified relation.

            Relation is specified by collection, type-background'entity and label.
            """
            relation = list(self.resolwe.relation.filter(
                collection=collection.id,
                type='background',
                entity=entity.id,
                label=label,
            ))
            if len(relation) > 1:
                raise ValueError(
                    'Multiple relations of type "background" for sample {} in ' 'collection {} '
                    'with label {}.'.format(entity, collection, label)
                )
            elif len(relation) == 1:
                cases = len([prt for prt in relation[0].partitions if prt.get('label') == 'case'])
            else:
                cases = 0

            return (relation[0] if relation else None, cases)

        if self.background == bground:
            return

        assert isinstance(bground, Sample)

        # Relations are always defined on collections: it is necessary
        # to check that both, background and case are defined in only
        # one common collection. Actions are done on this collection.
        common_ids = {col.id for col in self.collections} & {col.id for col in bground.collections}
        if not common_ids:
            raise ValueError('Background and case sample are not in the same collection.')
        elif len(common_ids) > 1:
            raise ValueError('Background and case sample are in multiple common collections.')
        collection = self.resolwe.collection.get(list(common_ids)[0])

        # One cannot simply assign a background to sample but needs to
        # account also for already existing background relations they
        # are part of. By this, 3 x 3 scenarios are possible. One
        # dimension of scenarios is determined by the relation in which
        # *sample* is. It can be in no background relation (0), it can
        # be in background relation where only one sample is the case
        # sample (1) or it can be in background relation where many
        # case samples are involved (2). Similarly, (future, to-be)
        # background relation can be without any existing background
        # relation (0), in background relation with one (1) or more (2)
        # case samples.

        # Get background relation for this sample and count cases in it.
        # If no relation is found set to 0.
        self_relation, self_cases = count_cases(self, 'case')

        # Get background relation of to-be background sample and count
        # cases in it. If no relation is found set to 0.
        bground_relation, bground_cases = count_cases(bground, 'background')

        # 3 x 3 options reduce to 5, since some of them can be treated equally:
        if self_cases == bground_cases == 0:
            # Neither case nor background is in background relation.
            # Make a new background relation.
            collection.create_background_relation('Background', bground, [self])
        elif self_cases == 0 and bground_cases > 0:
            # Sample is not part of any existing background relation,
            # but background sample is. In this cae, just add sample to
            # alread existing background relation
            bground_relation.add_sample(self, label='case')
        elif self_cases == 1 and bground_cases == 0:
            # Sample si part od already existing background relation
            # where there is one sample and one background. New,
            # to-be-background sample is not part of any background
            # relation yet. Modify sample relation and replace background.
            for partition in self_relation.partitions:
                if partition['label'] == 'background':
                    partition['entity'] = bground.id
                    break
        elif self_cases == 1 and bground_cases > 0:
            # Sample si part od already existing background relation
            # where there is one sample and one background. New,
            # to-be-background sample is is similar two-member relation.
            # Remove relaton of case sample and add it to existing
            # relation of the background smaple.
            self_relation.delete(force=True)
            bground_relation.add_sample(self, label='case')
        elif self_cases > 1:
            raise ValueError(
                'This sample is a case in a background relation with also other samples as cases. '
                'If you would like to change background sample for all of them please delete '
                'current relation and create new one with desired background.'
            )

        self.save()
        self._relations = None
        self._background = None
        bground._is_background = True  # pylint: disable=protected-access

    @property
    def is_background(self):
        """Return ``True`` if given sample is background to any other and ``False`` otherwise."""
        if self._is_background is None:
            background_relations = self.resolwe.relation.filter(
                type='background',
                entity=self.id,
                label='background',
            )
            # we need to iterate ``background_relations`` (using len) to
            # evaluate ResolweQuery:
            self._is_background = len(background_relations) > 0  # pylint: disable=len-as-condition

        return self._is_background
