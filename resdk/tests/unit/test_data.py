"""
Unit tests for resdk/resources/data.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest

import six

from mock import patch, MagicMock

from resdk.resources.data import Data
from resdk.tests.mocks.data import DATA_SAMPLE


class TestData(unittest.TestCase):

    @patch('resdk.resources.data.logging')
    @patch('resdk.resources.data.Data', spec=True)
    def test_init(self, data_mock, log_mock):
        data_mock.configure_mock(endpoint="a string")
        Data.__init__(data_mock, id=1, resolwe=MagicMock())
        log_mock.getLogger.assert_called_once_with('resdk.resources.data')

    @patch('resdk.resources.data.Data', spec=True)
    def test_update_fields(self, data_mock):
        Data._update_fields(data_mock, DATA_SAMPLE[0])
        self.assertEqual(data_mock._flatten_field.call_count, 2)

    @patch('resdk.resources.data.Data', spec=True)
    def test_flatten_field(self, data_mock):

        input_ = [{'src': "abc"}]
        process_input_schema = [{'name': "src", 'type': "x", 'label': "y"}]
        flat = Data._flatten_field(data_mock,
                                   input_,
                                   process_input_schema,
                                   "p")
        expected = {u'p.src': {u'type': 'x', u'name': 'src', u'value': None, u'label': 'y'}}
        self.assertEqual(flat, expected)

    @patch('resdk.resources.data.Data', spec=True)
    def test_files(self, data_mock):
        data_annotation = {
            'output.list': {'value': [{'file': "element.gz"}], 'type': 'list:basic:file:'},
            'output.fastq': {'value': {'file': "file.fastq.gz"}, 'type': 'basic:file:fastq'},
            'output.fastq_archive': {'value': {'file': "archive.gz"}, 'type': 'basic:file:'},
            'input.fastq_url': {'value': {'file': "blah"}, 'type': 'basic:url:'},
            'input.blah': {'value': "blah.gz", 'type': 'basic:file:'}
            }
        bad_data_annotation = {
            'output.list': {'value': [{'no_file_field_here': "element.gz"}], 'type': 'list:basic:file:'},
            }
        data_mock.configure_mock(annotation=data_annotation)

        file_list = Data.files(data_mock)
        self.assertEqual(set(file_list), set(['element.gz', 'archive.gz', 'file.fastq.gz']))
        file_list = Data.files(data_mock, file_name='element.gz')
        self.assertEqual(file_list, ['element.gz'])
        file_list = Data.files(data_mock, field_name='output.fastq')
        self.assertEqual(file_list, ['file.fastq.gz'])

        data_mock.configure_mock(annotation=bad_data_annotation)
        message = r"Item .* does not contain 'file' key."
        with six.assertRaisesRegex(self, KeyError, message):
            Data.files(data_mock)

    @patch('resdk.resources.data.Data', spec=True)
    def test_download_fail(self, data_mock):
        message = "Only one of file_name or field_name may be given."
        with six.assertRaisesRegex(self, ValueError, message):
            Data.download(data_mock, file_name="a", field_name="b")

    @patch('resdk.resources.data.Data', spec=True)
    def test_download_ok(self, data_mock):
        data_mock.configure_mock(id=123, **{'resolwe': MagicMock()})
        data_mock.configure_mock(**{'files.return_value': ['file1.txt', 'file2.fq.gz']})

        Data.download(data_mock)
        data_mock.resolwe.download_files.assert_called_once_with([u'123/file1.txt', u'123/file2.fq.gz'], None)

        data_mock.reset_mock()
        Data.download(data_mock, download_dir="/some/path/")
        data_mock.resolwe.download_files.assert_called_once_with([u'123/file1.txt', u'123/file2.fq.gz'], '/some/path/')

    @patch('resdk.resources.data.Data', spec=True)
    def test_print_annotation(self, data_mock):
        with six.assertRaisesRegex(self, NotImplementedError, ""):
            Data.print_annotation(data_mock)

    @patch('resdk.resources.data.requests')
    @patch('resdk.resources.data.urljoin')
    @patch('resdk.resources.data.Data', spec=True)
    def test_stdout_ok(self, data_mock, urljoin_mock, requests_mock):
        # Configure mocks:
        data_mock.configure_mock(id=123, resolwe=MagicMock(url="a", auth="b"))
        urljoin_mock.return_value = "some_url"

        # If response.ok = True:
        response = MagicMock(ok=True, **{'iter_content.return_value': ["abc", "def"]})
        requests_mock.configure_mock(**{'get.return_value': response})

        out = Data.stdout(data_mock)

        self.assertEqual(out, "abcdef")
        urljoin_mock.assert_called_once_with("a", 'data/123/stdout.txt')
        requests_mock.get.assert_called_once_with("some_url", stream=True, auth="b")

        # If response.ok = False:
        response = MagicMock(ok=False)
        requests_mock.configure_mock(**{'get.return_value': response})

        out = Data.stdout(data_mock)

        self.assertEqual(response.raise_for_status.call_count, 1)


if __name__ == '__main__':
    unittest.main()
