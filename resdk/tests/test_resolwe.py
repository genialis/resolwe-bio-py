"""
Unit tests for resdk/resolwe.py file.
"""
# pylint: disable=missing-docstring, protected-access

import os
import unittest
import six

from mock import patch, MagicMock
import requests

from resdk.resolwe import Resolwe, ResAuth
from resdk.resources import Data  # pylint: disable=unused-import
from resdk.tests.mocks.data import PROCESS_SAMPLE

if six.PY2:
    # pylint: disable=deprecated-method
    unittest.TestCase.assertRegex = unittest.TestCase.assertRegexpMatches


class TestResolweProcesses(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_process_without_name(self, resolwe_mock):
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.process.get = MagicMock(return_value=PROCESS_SAMPLE)

        resolwe = Resolwe.processes(resolwe_mock)

        self.assertIsInstance(resolwe, list)
        self.assertEqual(len(resolwe), 4)
        self.assertIsInstance(resolwe[0], dict)
        self.assertEqual(resolwe[0]['name'], 'Upload NGS reads')
        self.assertEqual(len(resolwe_mock.api.mock_calls), 1)

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_process_with_process_name(self, resolwe_mock):
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.process.get = MagicMock(return_value=PROCESS_SAMPLE)

        resolwe = Resolwe.processes(resolwe_mock, 'Variant filtering (Chemical Mutagenesis)')

        self.assertIsInstance(resolwe, list)
        self.assertEqual(len(resolwe), 1)
        self.assertIsInstance(resolwe[0], dict)
        self.assertEqual(resolwe[0]['name'], 'Variant filtering (Chemical Mutagenesis)')
        self.assertEqual(len(resolwe_mock.api.mock_calls), 1)


class TestResolwePrintUploadProcesses(unittest.TestCase):

    @patch('resdk.resolwe.sys', spec=True)
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_print_upload_processes(self, resolwe_mock, sys_mock):

        # Check output is correct
        resolwe_mock.processes.return_value = PROCESS_SAMPLE
        sys_mock.stdout.write = MagicMock()
        Resolwe.print_upload_processes(resolwe_mock)
        sys_mock.stdout.write.assert_called_with('Upload NGS reads\n')


class TestResolwePrintProcessInputs(unittest.TestCase):

    @patch('resdk.resolwe.sys', spec=True)
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_print_process_inpts(self, resolwe_mock, sys_mock):

        # Bad processor name:
        resolwe_mock.processes.return_value = []
        with self.assertRaises(Exception) as exc:
            Resolwe.print_process_inputs(resolwe_mock, 'Bad processor name')
        self.assertRegex(exc.exception.args[0], r"Invalid process name: .*.")  # pylint: disable=deprecated-method

        # Check output is correct
        resolwe_mock.processes.return_value = PROCESS_SAMPLE
        sys_mock.stdout.write = MagicMock()
        Resolwe.print_process_inputs(resolwe_mock, 'Upload NGS reads')
        sys_mock.stdout.write.assert_called_with('src -> basic:file:\n')


class TestResolweRegister(unittest.TestCase):

    pass


class TestResolweUploadTools(unittest.TestCase):

    pass


class TestResolweRun(unittest.TestCase):

    @patch('resdk.resolwe.os', spec=True)
    @patch('resdk.resolwe.Data', spec=True)
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_upload_file(self, resolwe_mock, data_mock, os_mock):

        # Raise error is only one of deswcriptor/descriptor_schema is given:
        msg = "Set both or neither descriptor and descriptor_schema"
        with self.assertRaises(ValueError) as exc:
            Resolwe.run(resolwe_mock, descriptor="a")
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method
        with self.assertRaises(ValueError) as exc:
            Resolwe.run(resolwe_mock, descriptor_schema="a")
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # Value error if process len is 0
        process_json = []
        resolwe_mock.api = MagicMock(**{'process.get.return_value': process_json})
        msg = "Could not get process for given slug"
        with self.assertRaises(ValueError) as exc:
            Resolwe.run(resolwe_mock)
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # Value error if process len >1
        process_json = ['process1', 'process2']
        resolwe_mock.api = MagicMock(**{'process.get.return_value': process_json})
        msg = r"Unexpected behaviour at get process with slug .*"
        with self.assertRaises(ValueError) as exc:
            Resolwe.run(resolwe_mock)
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # Bad file name
        process_json = [
            {'slug':
                'some:prc:slug:',  # pylint: disable=bad-continuation
             'input_schema':
                [{"label": "NGS reads (FASTQ)",  # pylint: disable=bad-continuation
                  "type": "basic:file:",
                  "name": "src"}]}]
        resolwe_mock.api = MagicMock(**{'process.get.return_value': process_json})
        os_mock.path = MagicMock()
        os_mock.path.isfile.return_value = False
        msg = r"File .* not found."
        with self.assertRaises(ValueError) as exc:
            Resolwe.run(resolwe_mock, input={"src": "/bad/path/to/file"})
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # Kao good file, upload fails
        os_mock.path.isfile.return_value = True
        msg = r'Upload failed for .*'
        resolwe_mock._upload_file = MagicMock(return_value=None)
        with self.assertRaises(Exception) as exc:
            Resolwe.run(resolwe_mock, input={"src": "/good/path/to/file"})
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # TODO: This doesn't do a thing: ???
        # fields[field_name] = {
        #     'file': file_name,
        #     'file_temp': file_temp
        # }

        # All good:
        resolwe_mock.api = MagicMock(**{
            'process.get.return_value': process_json,
            'data.post.return_value': "mdata"})
        data_mock.return_value = "Data object"
        data = Resolwe.run(resolwe_mock,
                           src="123",
                           tools="456")
        self.assertEqual(len(resolwe_mock._register.mock_calls), 1)
        self.assertEqual(len(resolwe_mock._upload_tools.mock_calls), 1)
        self.assertEqual(len(resolwe_mock._upload_file.mock_calls), 1)
        data_mock.assert_called_with(model_data='mdata', resolwe=resolwe_mock)
        self.assertEqual(data, "Data object")


class TestResolweUploadFile(unittest.TestCase):

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.sys')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_run(self, resolwe_mock, sys_mock, requests_mock):
        # Example file:
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'example.fastq')

        resolwe_mock.url = 'http://some/url'

        resolwe_mock.auth = MagicMock()
        # Supress upload progress messages:
        sys_mock.sys.stdout.write = MagicMock()
        sys_mock.sys.stdout.flush = MagicMock()

        # Immitate response form server - always status 200
        requests_response = {'files': [{'temp': 'fake_name'}]}
        requests_mock.post.return_value = MagicMock(status_code=200, **{'json.return_value': requests_response})
        resolwe = Resolwe._upload_file(resolwe_mock, fn)
        self.assertEqual(resolwe, 'fake_name')

        # Immitate response form server - always status 400
        requests_mock.post.return_value = MagicMock(status_code=400)
        resolwe = Resolwe._upload_file(resolwe_mock, fn)
        self.assertIsNone(resolwe)

        # Immitate response form server - one status 400, but other 200
        requests_response = {'files': [{'temp': 'fake_name'}]}
        response_ok = MagicMock(status_code=200, **{'json.return_value': requests_response})
        response_fails = MagicMock(status_code=400)
        requests_mock.post.side_effect = [response_ok, response_fails, response_ok, response_ok]
        resolwe = Resolwe._upload_file(resolwe_mock, fn)
        self.assertEqual(resolwe, 'fake_name')


class TestResolweResAuth(unittest.TestCase):

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.ResAuth', spec=True)
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_res_auth(self, resolwe_mock, auth_mock, requests_mock):

        # Wrong URL:
        requests_mock.post = MagicMock(side_effect=[requests.exceptions.ConnectionError()])
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        self.assertRegex(exc.exception.args[0], r"Server not accessible on .*.")  # pylint: disable=deprecated-method

        # Wrong credentials:
        magic_mock1 = MagicMock(status_code=400)
        requests_mock.post = MagicMock(return_value=magic_mock1)
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        msg = r'Response HTTP status code .* Invalid credentials?'
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # NO CSRF token:
        magic_mock1 = MagicMock(status_code=200, cookies={'sessionid': 42})
        requests_mock.post = MagicMock(return_value=magic_mock1)
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        msg = 'Missing sessionid or csrftoken. Invalid credentials?'
        self.assertRegex(exc.exception.args[0], msg)  # pylint: disable=deprecated-method

        # "All good" scenario should be tested in end-to-end tests.

if __name__ == '__main__':
    unittest.main()
