"""
Unit tests for resdk/resources/collection.py file.
"""

import unittest

from mock import MagicMock

from resdk.resources.collection import Collection

from .utils import server_resource


class TestCollection(unittest.TestCase):
    def test_create_group(self):
        collection = server_resource(Collection, id=1, resolwe=MagicMock())

        # only samples
        collection.create_group_relation(category="replicates", samples=[1, 2, 3])
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="group",
            category="replicates",
            partitions=[
                {"entity": 1},
                {"entity": 2},
                {"entity": 3},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels
        collection.create_group_relation(
            category="replicates",
            samples=[1, 2, 3],
            labels=["first", "second", "third"],
        )
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="group",
            category="replicates",
            partitions=[
                {"label": "first", "entity": 1},
                {"label": "second", "entity": 2},
                {"label": "third", "entity": 3},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels - length mismatch
        with self.assertRaises(ValueError):
            collection.create_group_relation(
                category="replicates", samples=[1, 2, 3], labels=["first"]
            )
        self.assertEqual(collection.resolwe.relation.create.call_count, 0)

        collection.resolwe.relation.create.reset_mock()

    def test_create_compare(self):
        collection = server_resource(Collection, id=1, resolwe=MagicMock())

        # only samples
        collection.create_compare_relation(category="case-control", samples=[1, 2])
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="compare",
            category="case-control",
            partitions=[
                {"entity": 1},
                {"entity": 2},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels
        collection.create_compare_relation(
            category="case-control", samples=[1, 2], labels=["case", "control"]
        )
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="compare",
            category="case-control",
            partitions=[
                {"label": "case", "entity": 1},
                {"label": "control", "entity": 2},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels - length mismatch
        with self.assertRaises(ValueError):
            collection.create_compare_relation(
                category="case-control", samples=[1, 2], labels=["case"]
            )
        self.assertEqual(collection.resolwe.relation.create.call_count, 0)

        collection.resolwe.relation.create.reset_mock()

    def test_create_series(self):
        collection = server_resource(Collection, id=1, resolwe=MagicMock())

        # only samples
        collection.create_series_relation(category="time-series", samples=[1, 2, 3])
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="series",
            category="time-series",
            partitions=[
                {"entity": 1},
                {"entity": 2},
                {"entity": 3},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels
        collection.create_series_relation(
            category="time-series", samples=[1, 2, 3], labels=["0Hr", "2Hr", "4Hr"]
        )
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="series",
            category="time-series",
            partitions=[
                {"label": "0Hr", "entity": 1},
                {"label": "2Hr", "entity": 2},
                {"label": "4Hr", "entity": 3},
            ],
        )

        # samples with positions
        collection.create_series_relation(
            category="time-series", samples=[1, 2, 3], positions=[10, 20, 30]
        )
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="series",
            category="time-series",
            partitions=[
                {"position": 10, "entity": 1},
                {"position": 20, "entity": 2},
                {"position": 30, "entity": 3},
            ],
        )

        collection.resolwe.relation.create.reset_mock()

        # samples with labels - length mismatch
        with self.assertRaises(ValueError):
            collection.create_series_relation(
                category="time-series", samples=[1, 2], labels=["0Hr"]
            )
        self.assertEqual(collection.resolwe.relation.create.call_count, 0)

        collection.resolwe.relation.create.reset_mock()

    def test_create_background(self):
        collection = server_resource(Collection, id=1, resolwe=MagicMock())

        # only samples
        collection.create_background_relation("background 1", "sample_1", ["sample_2"])
        collection.resolwe.relation.create.assert_called_with(
            collection=1,
            type="background",
            category="background 1",
            partitions=[
                {"label": "background", "entity": "sample_1"},
                {"label": "case", "entity": "sample_2"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
