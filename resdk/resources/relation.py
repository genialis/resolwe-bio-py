"""Relation resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import six

from resdk.exceptions import ValidationError

from .base import BaseResolweResource
from .utils import get_collection_id, get_sample_id, is_collection


class Relation(BaseResolweResource):
    """Resolwe Relation resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = 'relation'

    UPDATE_PROTECTED_FIELDS = BaseResolweResource.UPDATE_PROTECTED_FIELDS + (
        'type',
    )
    WRITABLE_FIELDS = BaseResolweResource.WRITABLE_FIELDS + (
        'collection', 'category', 'partitions', 'unit',
    )

    ALL_PERMISSIONS = ['view', 'edit', 'share', 'owner']

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: collection id in which relation is
        self._collection = None
        #: (lazy loaded) collection object in which relation is
        self._hydrated_collection = None
        #: (lazy loaded) list of samples in the relation
        self._samples = None

        #: list of ``RelationPartition`` objects in the ``Relation``
        self.partitions = None
        #: type of the relation
        self.type = None
        #: category of the relation
        self.category = None
        #: unit (where applicable, e.g. for serieses)
        self.unit = None

        super(Relation, self).__init__(resolwe, **model_data)

    @property
    def samples(self):
        """Return list of sample objects in the relation."""
        if not self._samples:
            if not self.partitions:
                self._samples = []
            else:
                sample_ids = [partition['entity'] for partition in self.partitions]
                self._samples = self.resolwe.sample.filter(id__in=sample_ids)
                # Samples should be sorted, so they have same order as positions
                # XXX: This may be slow for many samples in single collection
                self._samples = sorted(
                    self._samples, key=lambda sample: sample_ids.index(sample.id)
                )
        return self._samples

    @property
    def collection(self):
        """Return collection object to which relation belongs."""
        if not self._hydrated_collection:
            self._hydrated_collection = self.resolwe.collection.get(self._collection)
        return self._hydrated_collection

    @collection.setter
    def collection(self, collection):
        """Set collection to which relation belongs."""
        self._collection = get_collection_id(collection)
        # Save collection if already hydrated, othervise it will be rerived in getter
        self._hydrated_collection = collection if is_collection(collection) else None

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._samples = None
        self._hydrated_collection = None

        super(Relation, self).update()

    def add_sample(self, sample, label=None, position=None):
        """Add ``sample`` object to relation."""
        self.partitions.append({
            'entity': sample.id,
            'position': position,
            'label': label,
        })
        self.save()
        self._samples = None

    def remove_samples(self, *samples):
        """Remove ``sample`` objects from relation."""
        sample_ids = [get_sample_id(sample) for sample in samples]
        self.partitions = [partition for partition in self.partitions if
                           partition['entity'] not in sample_ids]
        self.save()
        self._samples = None

    def save(self):
        """Check that collection is saved and save instance."""
        if self._collection is None:
            # `save` fails in an ugly way if collection is not set
            raise ValidationError('`collection` attribute is required.')

        super(Relation, self).save()

    def __repr__(self):
        """Format relation name."""
        sample_info = []
        for sample, partition in zip(self.samples, self.partitions):
            name = sample.name
            label = partition.get('label', None)
            position = partition.get('position', None)

            if label and position:
                sample_info.append('{} ({} {}): {}'.format(label, position, self.unit, name))
            elif partition['label']:
                sample_info.append('{}: {}'.format(label, name))
            elif partition['position']:
                sample_info.append('{} {}: {}'.format(position, self.unit, name))
            else:
                sample_info.append(name)

        rep = "{} id: {}, type: '{}', category: '{}', samples: {{{}}}".format(
            self.__class__.__name__,
            self.id,
            self.type,
            self.category,
            ', '.join(sample_info),
        )

        return rep.encode('utf-8') if six.PY2 else rep
