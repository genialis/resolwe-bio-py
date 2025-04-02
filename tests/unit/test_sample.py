"""
Unit tests for resdk/resources/sample.py file.
"""

import unittest

from mock import MagicMock, patch

from resdk.exceptions import ResolweServerError
from resdk.resources.annotations import AnnotationValue
from resdk.resources.descriptor import DescriptorSchema
from resdk.resources.sample import Sample

from .utils import server_resource


class TestSampleUtilsMixin(unittest.TestCase):
    def test_get_reads(self):
        sample = server_resource(Sample, resolwe=MagicMock(), id=42)
        data1 = MagicMock(process_type="data:reads:fastq:single", id=1)
        data2 = MagicMock(process_type="data:reads:fastq:single:cutadapt", id=2)
        sample.data.filter = MagicMock(return_value=[data2, data1])

        self.assertEqual(sample.get_reads(), data2)


class TestSample(unittest.TestCase):
    def test_descriptor_schema(self):
        # hidrated descriptor schema
        descriptor_schema = {
            "slug": "test-schema",
            "name": "Test schema",
            "version": "1.0.0",
            "schema": [
                {
                    "default": "56G",
                    "type": "basic:string:",
                    "name": "description",
                    "label": "Object description",
                }
            ],
            "id": 1,
        }
        sample = server_resource(
            Sample, id=1, descriptor_schema=descriptor_schema, resolwe=MagicMock()
        )
        self.assertTrue(isinstance(sample.descriptor_schema, DescriptorSchema))

        self.assertEqual(sample.descriptor_schema.slug, "test-schema")

    def test_data(self):
        resolwe_mock = MagicMock()
        sample = server_resource(Sample, id=1, resolwe=resolwe_mock)

        # test getting data attribute
        filter_mock = MagicMock(return_value=["data_1", "data_2", "data_3"])
        resolwe_mock.get_query_by_resource.return_value = MagicMock(filter=filter_mock)
        self.assertEqual(sample.data, ["data_1", "data_2", "data_3"])

        # test caching data attribute
        self.assertEqual(sample.data, ["data_1", "data_2", "data_3"])
        self.assertEqual(filter_mock.call_count, 1)

        # cache is cleared at update
        sample._data = ["data"]
        sample.update()
        self.assertEqual(sample._data, None)

        # raising error if sample is not saved
        sample._id = None
        with self.assertRaises(ValueError):
            sample.data

    def test_set_annotation(self):
        resolwe = MagicMock()
        sample = server_resource(Sample, id=1, resolwe=resolwe)
        full_path = "general.species"
        value_mock = MagicMock(spec=AnnotationValue)
        resolwe.annotation_value.create.side_effect = value_mock
        sample.set_annotation(full_path, "Mus musculus")
        value_mock.assert_called_once()
        self.assertEqual(value_mock.call_args[1]["value"], "Mus musculus")

        # Nonexisting field.
        resolwe.annotation_field.from_path.side_effect = LookupError
        with patch("resdk.resources.sample.Sample.annotations") as mock_annotations:
            sample = server_resource(Sample, id=1, resolwe=resolwe)
            full_path = "general.species"
            post_mock = MagicMock()
            sample.api = MagicMock(return_value=post_mock)
            mock_annotations.get.side_effect = LookupError
            self.assertRaisesRegex(
                ResolweServerError,
                "Field 'general.species' does not exist.",
                sample.set_annotation,
                full_path,
                "Mus musculus",
            )

    def test_set_annotations(self):
        sample = server_resource(Sample, id=1, resolwe=MagicMock())
        annotations = {"general.species": "Mus musculus", "qc.message": None}
        post_mock = MagicMock()
        sample.api = MagicMock(return_value=post_mock)

        sample.set_annotations(annotations)

        post_mock.set_annotations.post.assert_called_with(
            [
                {"field_path": "general.species", "value": "Mus musculus"},
                {"field_path": "qc.message", "value": None},
            ]
        )


if __name__ == "__main__":
    unittest.main()
