"""
Unit tests for resdk/resources/utils.py file.
"""

import unittest

import pytz
from mock import MagicMock, call, patch

from resdk.resources import Collection, Data, Process, Relation, Sample
from resdk.resources.utils import (
    _print_input_line,
    fill_spaces,
    flatten_field,
    get_collection_id,
    get_data_id,
    get_process_id,
    get_relation_id,
    get_sample_id,
    iterate_fields,
    iterate_schema,
    parse_resolwe_datetime,
)

from .utils import server_resource

PROCESS_OUTPUT_SCHEMA = [
    {"name": "fastq", "type": "basic:file:", "label": "Reads file"},
    {"name": "bases", "type": "basic:string:", "label": "Number of bases"},
    {
        "name": "options",
        "label": "Options",
        "group": [
            {"name": "id", "type": "basic:string:", "label": "ID"},
            {"name": "k", "type": "basic:integer:", "label": "k-mer size"},
        ],
    },
]

OUTPUT = {
    "fastq": {"file": "example.fastq.gz"},
    "bases": "75",
    "options": {
        "id": "abc",
        "k": 123,
    },
}


class TestUtils(unittest.TestCase):
    def test_iterate_fields(self):
        result = list(iterate_fields(OUTPUT, PROCESS_OUTPUT_SCHEMA))
        # result object is iterator - we use lists to pull all elements

        expected = [
            (
                {"type": "basic:string:", "name": "id", "label": "ID"},
                {"k": 123, "id": "abc"},
            ),
            (
                {"type": "basic:string:", "name": "bases", "label": "Number of bases"},
                {
                    "options": {"k": 123, "id": "abc"},
                    "bases": "75",
                    "fastq": {"file": "example.fastq.gz"},
                },
            ),
            (
                {"type": "basic:file:", "name": "fastq", "label": "Reads file"},
                {
                    "options": {"k": 123, "id": "abc"},
                    "bases": "75",
                    "fastq": {"file": "example.fastq.gz"},
                },
            ),
            (
                {"type": "basic:integer:", "name": "k", "label": "k-mer size"},
                {"k": 123, "id": "abc"},
            ),
        ]

        self.assertCountEqual(result, expected)

    def test_iterate_fields_modif(self):
        """
        Ensure that changing ``values`` inside iteration loop also changes ``OUTPUT`` values.
        """
        for schema, values in iterate_fields(OUTPUT, PROCESS_OUTPUT_SCHEMA):
            field_name = schema["name"]
            if field_name == "bases":
                values[field_name] = str(int(values[field_name]) + 1)

        self.assertEqual(OUTPUT["bases"], "76")
        # Fix the OUTPUT to previous state:
        OUTPUT["bases"] = "75"

    def test_iterate_schema(self):
        result1 = list(iterate_schema(OUTPUT, PROCESS_OUTPUT_SCHEMA, "my_path"))
        result2 = list(iterate_schema(OUTPUT, PROCESS_OUTPUT_SCHEMA))

        expected1 = [
            (
                {"name": "fastq", "label": "Reads file", "type": "basic:file:"},
                {
                    "fastq": {"file": "example.fastq.gz"},
                    "options": {"k": 123, "id": "abc"},
                    "bases": "75",
                },
                "my_path.fastq",
            ),
            (
                {"name": "bases", "label": "Number of bases", "type": "basic:string:"},
                {
                    "fastq": {"file": "example.fastq.gz"},
                    "options": {"k": 123, "id": "abc"},
                    "bases": "75",
                },
                "my_path.bases",
            ),
            (
                {"name": "id", "label": "ID", "type": "basic:string:"},
                {"k": 123, "id": "abc"},
                "my_path.options.id",
            ),
            (
                {"name": "k", "label": "k-mer size", "type": "basic:integer:"},
                {"k": 123, "id": "abc"},
                "my_path.options.k",
            ),
        ]

        expected2 = [
            (
                {"type": "basic:file:", "name": "fastq", "label": "Reads file"},
                {
                    "fastq": {"file": "example.fastq.gz"},
                    "bases": "75",
                    "options": {"k": 123, "id": "abc"},
                },
            ),
            (
                {"type": "basic:string:", "name": "bases", "label": "Number of bases"},
                {
                    "fastq": {"file": "example.fastq.gz"},
                    "bases": "75",
                    "options": {"k": 123, "id": "abc"},
                },
            ),
            (
                {"type": "basic:string:", "name": "id", "label": "ID"},
                {"k": 123, "id": "abc"},
            ),
            (
                {"type": "basic:integer:", "name": "k", "label": "k-mer size"},
                {"k": 123, "id": "abc"},
            ),
        ]

        self.assertEqual(result1, expected1)
        self.assertEqual(result2, expected2)

    def test_flatten_field(self):
        process_input_schema = [
            {
                "name": "x",
                "type": "basic:integer:",
                "label": "Input X",
            },
            {
                "name": "group_input",
                "group": [
                    {
                        "name": "y1",
                        "type": "basic:string:",
                        "label": "Input Y1",
                    },
                ],
            },
        ]
        input_ = {
            "x": 123,
            "group_input": {
                "y1": "bar",
            },
        }
        flat = flatten_field(input_, process_input_schema, "input")
        self.assertEqual(
            flat,
            {
                "input.x": {
                    "name": "x",
                    "type": "basic:integer:",
                    "label": "Input X",
                    "value": 123,
                },
                "input.group_input.y1": {
                    "name": "y1",
                    "type": "basic:string:",
                    "label": "Input Y1",
                    "value": "bar",
                },
            },
        )

    def test_fill_spaces(self):
        result = fill_spaces("one_word", 12)
        self.assertEqual(result, "one_word    ")

    @patch("resdk.resources.utils.print")
    def test_print_input_line(self, print_mock):
        _print_input_line(PROCESS_OUTPUT_SCHEMA, 0)
        calls = [
            call("- fastq     [basic:file:]   - Reads file"),
            call("- bases     [basic:string:] - Number of bases"),
            call("- options - Options"),
            call("    - id   [basic:string:]  - ID"),
            call("    - k    [basic:integer:] - k-mer size"),
        ]

        self.assertEqual(print_mock.mock_calls, calls)

    def test_get_collection_id(self):
        collection = server_resource(Collection, id=1, resolwe=MagicMock())
        self.assertEqual(get_collection_id(collection), 1)

        self.assertEqual(get_collection_id(2), 2)

    def test_get_sample_id(self):
        sample = server_resource(Sample, id=1, resolwe=MagicMock())
        self.assertEqual(get_sample_id(sample), 1)

        self.assertEqual(get_sample_id(2), 2)

    def test_get_data_id(self):
        data = server_resource(Data, id=1, resolwe=MagicMock())
        self.assertEqual(get_data_id(data), 1)

        self.assertEqual(get_data_id(2), 2)

    def test_get_process_id(self):
        process = server_resource(Process, id=1, resolwe=MagicMock())
        self.assertEqual(get_process_id(process), 1)

        self.assertEqual(get_process_id(2), 2)

    def test_get_relation_id(self):
        relation = server_resource(Relation, id=1, collection=None, resolwe=MagicMock())
        self.assertEqual(get_relation_id(relation), 1)

        self.assertEqual(get_relation_id(2), 2)

    @patch("resdk.resources.utils.tzlocal")
    def test_parse_resolwe_datetime(self, tzlocal_mock):
        tzlocal_mock.get_localzone.return_value = pytz.timezone("US/Hawaii")
        dtime = parse_resolwe_datetime("2018-06-01T16:12:34.123456+02:00")
        self.assertEqual(dtime.year, 2018)
        self.assertEqual(dtime.month, 6)
        self.assertEqual(dtime.day, 1)
        self.assertEqual(dtime.hour, 6)
        self.assertEqual(dtime.minute, 12)
        self.assertEqual(dtime.second, 34)
        self.assertEqual(dtime.microsecond, 123456)
        self.assertEqual(dtime.tzinfo.zone, "US/Hawaii")


if __name__ == "__main__":
    unittest.main()
