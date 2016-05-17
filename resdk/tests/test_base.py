"""
Unit tests for resdk/resources/base.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest
import six

from mock import patch, MagicMock, call

from resdk.resources.base import BaseResource

if six.PY2:
    # pylint: disable=deprecated-method
    unittest.TestCase.assertRegex = unittest.TestCase.assertRegexpMatches

FILES = [
    (101, 'file1.fq', 'output.fastq', 'data:reads:fastq:'),
    (102, 'file2.bam', 'output.bam', 'data:alignment:bam:')]


class TestDownload(unittest.TestCase):

    @patch('resdk.resources.base.print')
    @patch('resdk.resources.base.requests')
    @patch('resdk.resources.base.urljoin')
    @patch('resdk.resources.base.open')
    @patch('resdk.resources.base.os', spec=True)
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_download1(self, base_mock, os_mock, open_mock, urljoin_mock, requests_mock, print_mock):

        # Confirm that download_dir is determined if not specified:
        BaseResource.download(base_mock)
        self.assertEqual(len(os_mock.getcwd.mock_calls), 1)

        # Name given, file exists
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(return_value='file1.fq')
        urljoin_mock.return_value = "http://bla/blah"
        requests_mock.ok = True
        print_mock.reset_mock()
        BaseResource.download(base_mock, name='file1.fq')
        open_mock.assert_called_once_with('file1.fq', 'wb')
        print_mock.assert_has_calls([
            call('Following files will be downloaded to direcotry {}:'.format(os_mock.getcwd())),
            call('* file1.fq')])

        # Name given, file does not exist.
        base_mock.files.return_value = FILES
        print_mock.reset_mock()
        BaseResource.download(base_mock, name='bad_file.txt')
        print_mock.assert_called_once_with("No files matching.")

        # Type given with abbreviation, file exists:
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(return_value='file2.bam')
        urljoin_mock.return_value = "http://bla/blah"
        requests_mock.ok = True
        print_mock.reset_mock()
        open_mock.reset_mock()
        BaseResource.download(base_mock, type='bam')
        open_mock.assert_called_once_with('file2.bam', 'wb')
        print_mock.assert_has_calls([
            call('Following files will be downloaded to direcotry {}:'.format(os_mock.getcwd())),
            call('* file2.bam')])

        # Type given with abbreviation, file does not exist:
        base_mock.files.return_value = FILES
        with self.assertRaises(ValueError) as exc:
            BaseResource.download(base_mock, type='bad_ebbreviation')
        self.assertRegex(exc.exception.args[0], r"Invalid argument typ.")  # pylint: disable=deprecated-method

        # Type given with tuple, file exists:
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(return_value='file2.bam')
        urljoin_mock.return_value = "http://bla/blah"
        requests_mock.ok = True
        print_mock.reset_mock()
        open_mock.reset_mock()
        BaseResource.download(base_mock, type=('data:alignment:bam:', 'output.bam'))
        open_mock.assert_called_once_with('file2.bam', 'wb')
        print_mock.assert_has_calls([
            call('Following files will be downloaded to direcotry {}:'.format(os_mock.getcwd())),
            call('* file2.bam')])

        # Type given with bad tuple
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(return_value='file2.bam')
        urljoin_mock.return_value = "http://bla/blah"
        requests_mock.ok = True
        print_mock.reset_mock()
        open_mock.reset_mock()
        BaseResource.download(base_mock, type=('bad:type', 'bad.field'))
        print_mock.assert_called_once_with('No files matching.')

        # Force:
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(side_effect=['file1.fq', 'file2.bam'])
        urljoin_mock.return_value = "http://bla/blah"
        requests_mock.ok = True
        print_mock.reset_mock()
        open_mock.reset_mock()
        BaseResource.download(base_mock, force=True)
        # open_mock.assert_has_calls([call('file1.fq', 'wb'), call('file2.bam', 'wb')])
        print_mock.assert_has_calls([
            call('Following files will be downloaded to direcotry {}:'.format(os_mock.getcwd())),
            call('* file1.fq'),
            call('* file2.bam')])

        # Response not ok:
        base_mock.files.return_value = FILES
        base_mock.resolwe = MagicMock()
        os_mock.path = MagicMock()
        os_mock.path.join = MagicMock(side_effect=['file1.fq', 'file2.bam'])
        urljoin_mock.return_value = "http://bla/blah"
        raise_mock = MagicMock(side_effect=KeyError("Fail!"))
        requests_mock.get.return_value = MagicMock(ok=False, **{'raise_for_status': raise_mock})
        with self.assertRaises(KeyError) as exc:
            BaseResource.download(base_mock, force=True)
        self.assertRegex(exc.exception.args[0], r"Fail!")  # pylint: disable=deprecated-method

if __name__ == '__main__':
    unittest.main()
