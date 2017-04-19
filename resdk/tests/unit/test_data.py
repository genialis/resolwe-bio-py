"""
Unit tests for resdk/resources/data.py file.
"""
# pylint: disable=missing-docstring, protected-access
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

import six
from mock import MagicMock, patch

from resdk.resources.data import Data
from resdk.tests.mocks.data import DATA_SAMPLE


class TestData(unittest.TestCase):

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

    def test_sample(self):
        data = Data(id=1, resolwe=MagicMock())

        data.resolwe.sample.filter = MagicMock(return_value=[])
        self.assertEqual(data.sample, None)

        data.resolwe.sample.filter = MagicMock(return_value=['sample'])
        self.assertEqual(data.sample, 'sample')
        # test caching
        self.assertEqual(data.sample, 'sample')
        self.assertEqual(data.resolwe.sample.filter.call_count, 1)

        # cache is cleared at update
        data._sample = 'sample'
        data.update()
        self.assertEqual(data._sample, None)

        # raising error if data object is not saved
        data.id = None
        with self.assertRaises(ValueError):
            _ = data.sample

    def test_collections(self):
        data = Data(id=1, resolwe=MagicMock())

        # test getting collections attribute
        data.resolwe.collection.filter = MagicMock(return_value=['collection'])
        self.assertEqual(data.collections, ['collection'])

        # test caching collections attribute
        self.assertEqual(data.collections, ['collection'])
        self.assertEqual(data.resolwe.collection.filter.call_count, 1)

        # cache is cleared at update
        data._collections = ['collection']
        data.update()
        self.assertEqual(data._collections, None)

        # raising error if data object is not saved
        data.id = None
        with self.assertRaises(ValueError):
            _ = data.collections

    def test_files(self):
        data = Data(id=123, resolwe=MagicMock())
        data._get_dir_files = MagicMock(
            side_effect=[['first_dir/file1.txt'], ['fastq_dir/file2.txt']])

        data.annotation = {
            'output.list': {'value': [{'file': "element.gz"}], 'type': 'list:basic:file:'},
            'output.dir_list': {'value': [{'dir': "first_dir"}], 'type': 'list:basic:dir:'},
            'output.fastq': {'value': {'file': "file.fastq.gz"}, 'type': 'basic:file:fastq'},
            'output.fastq_archive': {'value': {'file': "archive.gz"}, 'type': 'basic:file:'},
            'output.fastq_dir': {'value': {'dir': "fastq_dir"}, 'type': 'basic:dir:'},
            'input.fastq_url': {'value': {'file': "blah"}, 'type': 'basic:url:'},
            'input.blah': {'value': "blah.gz", 'type': 'basic:file:'}
        }

        file_list = data.files()
        six.assertCountEqual(self, file_list, [
            'element.gz',
            'archive.gz',
            'file.fastq.gz',
            'first_dir/file1.txt',
            'fastq_dir/file2.txt'
        ])
        file_list = data.files(file_name='element.gz')
        self.assertEqual(file_list, ['element.gz'])
        file_list = data.files(field_name='output.fastq')
        self.assertEqual(file_list, ['file.fastq.gz'])

        data.annotation = {
            'output.list': {'value': [{'no_file_field_here': "element.gz"}],
                            'type': 'list:basic:file:'},
        }
        with six.assertRaisesRegex(self, KeyError, "does not contain 'file' key."):
            data.files()

        data = Data(resolwe=MagicMock())
        with six.assertRaisesRegex(self, ValueError, "must be saved before"):
            data.files()

    @patch('resdk.resources.data.requests')
    def test_dir_files(self, requests_mock):
        data = Data(id=123, resolwe=MagicMock(url='http://resolwe.url'))
        requests_mock.get = MagicMock(side_effect=[
            MagicMock(content=b'[{"type": "file", "name": "file1.txt"}, '
                              b'{"type": "directory", "name": "subdir"}]'),
            MagicMock(content=b'[{"type": "file", "name": "file2.txt"}]'),
        ])

        files = data._get_dir_files('test_dir')

        self.assertEqual(files, ['test_dir/file1.txt', 'test_dir/subdir/file2.txt'])

    @patch('resdk.resources.data.Data', spec=True)
    def test_download_fail(self, data_mock):
        message = "Only one of file_name or field_name may be given."
        with six.assertRaisesRegex(self, ValueError, message):
            Data.download(data_mock, file_name="a", field_name="b")

    @patch('resdk.resources.data.Data', spec=True)
    def test_download_ok(self, data_mock):
        data_mock.configure_mock(id=123, **{'resolwe': MagicMock()})
        data_mock.configure_mock(**{
            'files.return_value': ['file1.txt', 'file2.fq.gz'],
        })

        Data.download(data_mock)
        data_mock.resolwe._download_files.assert_called_once_with(
            ['123/file1.txt', '123/file2.fq.gz'], None)

        data_mock.reset_mock()
        Data.download(data_mock, download_dir="/some/path/")
        data_mock.resolwe._download_files.assert_called_once_with(
            ['123/file1.txt', '123/file2.fq.gz'], '/some/path/')

    @patch('resdk.resources.data.Data', spec=True)
    def test_add_output(self, data_mock):
        data_mock.configure_mock(
            annotation={'output.fastq': {'type': 'basic:file:', 'value': {'file': 'reads.fq'}},
                        'output.fasta': {'type': 'basic:file:', 'value': {'file': 'genome.fa'}}}
        )

        files_list = Data._files_dirs(data_mock, 'file', field_name="output.fastq")
        self.assertEqual(files_list, ['reads.fq'])

        files_list = Data._files_dirs(data_mock, 'file', field_name="fastq")
        self.assertEqual(files_list, ['reads.fq'])

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
        response = MagicMock(ok=True, **{'iter_content.return_value': [b"abc", b"def"]})
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
