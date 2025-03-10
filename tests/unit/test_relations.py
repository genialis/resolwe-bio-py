"""
Unit tests for resdk/resources/relation.py file.
"""

import unittest

from mock import MagicMock, patch

from resdk.resources.base import DataSource
from resdk.resources.collection import Collection
from resdk.resources.descriptor import DescriptorSchema
from resdk.resources.relation import Relation
from resdk.resources.sample import Sample

from .utils import server_resource


class TestRelation(unittest.TestCase):
    def test_samples(self):
        relation = server_resource(Relation, id=1, collection=None, resolwe=MagicMock())

        sample_1 = MagicMock(id=1)
        sample_2 = MagicMock(id=2)
        # order in return_value is intentionally mixed to test ordering
        relation.resolwe.sample.filter = MagicMock(return_value=[sample_2, sample_1])
        relation.partitions = [
            {"entity": 1, "position": None},
            {"entity": 2, "position": None},
        ]
        self.assertEqual(relation.samples, [sample_1, sample_2])
        relation.resolwe.sample.filter.assert_called_with(id__in=[1, 2])

        # test caching
        self.assertEqual(relation.samples, [sample_1, sample_2])
        self.assertEqual(relation.resolwe.sample.filter.call_count, 1)

        # cache is cleared at update
        relation._samples = ["sample"]
        relation._update_fields(
            {"id": 1, "collection": None}, data_source=DataSource.SERVER
        )
        self.assertEqual(relation._samples, None)

    # I appears it is not possible to deepcopy MagicMocks so we just patch
    # the deepcopy functionality:
    @patch("resdk.resources.base.copy")
    def test_collection(self, copy_mock):
        relation = server_resource(Relation, id=1, collection=None, resolwe=MagicMock())
        collection = server_resource(Collection, id=3, resolwe=MagicMock())

        # get collection
        relation.resolwe.collection.get = MagicMock(return_value=collection)
        relation._collection = collection
        self.assertEqual(relation.collection, collection)

    # I appears it is not possible to deepcopy MagicMocks so we just patch
    # the deepcopy functionality:
    @patch("resdk.resources.base.copy")
    def test_descriptor_schema(self, copy_mock):
        relation = server_resource(Relation, id=1, collection=None, resolwe=MagicMock())
        ds = server_resource(DescriptorSchema, id=3, resolwe=MagicMock())

        # get collection
        relation.resolwe.descriptor_schema.get = MagicMock(return_value=ds)
        relation._descriptor_schema = ds
        self.assertEqual(relation.descriptor_schema, ds)

    def test_repr(self):
        # `name` cannot be mocked in another way
        sample_1 = MagicMock(spec=Sample)
        sample_1.configure_mock(name="sample_1")
        sample_2 = MagicMock(spec=Sample)
        sample_2.configure_mock(name="sample_2")

        relation = server_resource(
            Relation,
            id=1,
            collection=None,
            type="compare",
            unit="min",
            category="background",
            samples=[sample_1, sample_2],
            resolwe=MagicMock(),
        )

        # Positions and labels are given
        relation.partitions = [
            {"id": 3, "entity": 1, "position": 10, "label": "first"},
            {"id": 4, "entity": 2, "position": 20, "label": "second"},
        ]
        self.assertEqual(
            str(relation),
            "Relation id: 1, type: 'compare', category: 'background', "
            "samples: {first (10 min): sample_1, second (20 min): sample_2}",
        )

        # Only labels are given
        relation.partitions = [
            {"id": 3, "entity": 1, "position": None, "label": "first"},
            {"id": 4, "entity": 2, "position": None, "label": "second"},
        ]
        self.assertEqual(
            str(relation),
            "Relation id: 1, type: 'compare', category: 'background', "
            "samples: {first: sample_1, second: sample_2}",
        )

        # Only positions are given
        relation.partitions = [
            {"id": 3, "entity": 1, "position": 10, "label": None},
            {"id": 4, "entity": 2, "position": 20, "label": None},
        ]
        self.assertEqual(
            str(relation),
            "Relation id: 1, type: 'compare', category: 'background', "
            "samples: {10 min: sample_1, 20 min: sample_2}",
        )

        # Only sample names are given
        relation.partitions = [
            {"id": 3, "entity": 1, "position": None, "label": None},
            {"id": 4, "entity": 2, "position": None, "label": None},
        ]
        self.assertEqual(
            str(relation),
            "Relation id: 1, type: 'compare', category: 'background', "
            "samples: {sample_1, sample_2}",
        )


if __name__ == "__main__":
    unittest.main()
