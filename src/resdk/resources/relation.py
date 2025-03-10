"""Relation resource."""

import logging

from .base import BaseResolweResource
from .fields import (
    BooleanField,
    DictResourceField,
    FieldAccessType,
    JSONField,
    LazyResourceField,
    StringField,
)
from .utils import get_sample_id


class Relation(BaseResolweResource):
    """Resolwe Relation resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "relation"

    descriptor_dirty = BooleanField()
    type = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    collection = DictResourceField(
        resource_class_name="Collection",
        access_type=FieldAccessType.WRITABLE,
        required=True,
    )
    category = StringField(access_type=FieldAccessType.WRITABLE)
    descriptor = JSONField(access_type=FieldAccessType.WRITABLE)
    descriptor_schema = DictResourceField(
        resource_class_name="DescriptorSchema", access_type=FieldAccessType.WRITABLE
    )
    partitions = JSONField(access_type=FieldAccessType.WRITABLE, many=True)
    unit = StringField(access_type=FieldAccessType.WRITABLE)
    samples = LazyResourceField(
        "Sample", lambda relation: relation._lazy_load_samples()
    )

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def _lazy_load_samples(self):
        """Return list of sample objects in the relation."""
        if not self.partitions:
            return []
        else:
            sample_ids = [partition["entity"] for partition in self.partitions]
            samples = self.resolwe.sample.filter(id__in=sample_ids)
            # Samples should be sorted, so they have same order as positions
            # XXX: This may be slow for many samples in single collection
            samples = sorted(samples, key=lambda sample: sample_ids.index(sample.id))
        return samples

    def add_sample(self, sample, label=None, position=None):
        """Add ``sample`` object to relation."""
        self.partitions.append(
            {
                "entity": sample.id,
                "position": position,
                "label": label,
            }
        )
        self.save()
        self._resource_fields["samples"].reset()

    def remove_samples(self, *samples):
        """Remove ``sample`` objects from relation."""
        sample_ids = [get_sample_id(sample) for sample in samples]
        self.partitions = [
            partition
            for partition in self.partitions
            if partition["entity"] not in sample_ids
        ]
        self.save()
        self._resource_fields["samples"].reset()

    def __repr__(self):
        """Format relation name."""
        sample_info = []
        for sample, partition in zip(self.samples, self.partitions):
            name = sample.name
            label = partition.get("label", None)
            position = partition.get("position", None)

            if label and position:
                sample_info.append(
                    "{} ({} {}): {}".format(label, position, self.unit, name)
                )
            elif partition["label"]:
                sample_info.append("{}: {}".format(label, name))
            elif partition["position"]:
                sample_info.append("{} {}: {}".format(position, self.unit, name))
            else:
                sample_info.append(name)

        return "{} id: {}, type: '{}', category: '{}', samples: {{{}}}".format(
            self.__class__.__name__,
            self.id,
            self.type,
            self.category,
            ", ".join(sample_info),
        )
