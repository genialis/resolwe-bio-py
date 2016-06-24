"""
Unit tests for resdk/resolwe.py file.
"""
# pylint: disable=missing-docstring, protected-access

import os
import io
import unittest
import six

from mock import patch, MagicMock, mock_open
import requests
import slumber
import yaml


from resdk.resolwe import Resolwe, ResAuth
from resdk import resolwe


class TestResolwe(unittest.TestCase):

    @patch('resdk.resolwe.logging')
    @patch('resdk.resolwe.ResolweQuerry')
    @patch('resdk.resolwe.slumber')
    @patch('resdk.resolwe.ResAuth')
    @patch('resdk.resolwe.Resolwe', spec=Resolwe)
    def test_init(self, resolwe_mock, resauth_mock, slumber_mock, resolwe_querry_mock, log_mock):
        Resolwe.__init__(resolwe_mock, 'a', 'b', 'http://some/url')
        self.assertEqual(resauth_mock.call_count, 1)
        self.assertEqual(slumber_mock.API.call_count, 1)
        # There are four instances of ResolweQuerry in init: data, process, sample and collection:
        self.assertEqual(resolwe_querry_mock.call_count, 4)
        self.assertEqual(log_mock.getLogger.call_count, 1)


class TestVersionConverters(unittest.TestCase):
    """
    Test both version convert methods.
    """

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_version_string_to_int(self, resolwe_mock):
        version = Resolwe._version_string_to_int(resolwe_mock, "1.2.3")
        self.assertEqual(version, 16809987)
        version = Resolwe._version_string_to_int(resolwe_mock, "12.6")
        self.assertEqual(version, 201424896)

        # Fail if version has 4 or more "decimal places":
        message = r"Versions with more than \d+ decimal places are not supported."
        with six.assertRaisesRegex(self, NotImplementedError, message):
            Resolwe._version_string_to_int(resolwe_mock, "1.2.3.4")

        # Fail if number used for "decimal place" is too big:
        message = r"Number \d+ cannot be stored with only \d+ bits. Max is \d+."
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._version_string_to_int(resolwe_mock, "1000.2.3")

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_version_int_to_string(self, resolwe_mock):
        version = Resolwe._version_int_to_string(resolwe_mock, 16809987)
        self.assertEqual(version, "1.2.3")
        version = Resolwe._version_int_to_string(resolwe_mock, 201424896)
        self.assertEqual(version, "12.6.0")


class TestRegister(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe', spec=True)
    def setUp(self, resolwe_mock):  # pylint: disable=arguments-differ
        self.yaml_file = os.path.normpath(os.path.dirname(__file__) + "./../files/bowtie.yaml")
        self.bad_yaml_file = os.path.normpath(os.path.dirname(__file__) + "./../files/bowtie_bad.yaml")
        self.resolwe_mock = resolwe_mock
        self.resolwe_mock._version_string_to_int = MagicMock(return_value=16777229)
        self.resolwe_mock.api = MagicMock()
        self.resolwe_mock.logger = MagicMock()
        self.resolwe_mock.process = MagicMock()

    def test_raise_if_no_yaml_file(self):
        message = r"File not found: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._register(self.resolwe_mock, "/bad/path", "alignment-bowtie")

    def test_raise_if_bad_yaml_file(self):
        with self.assertRaises(yaml.parser.ParserError):
            Resolwe._register(self.resolwe_mock, self.bad_yaml_file, "alignment-bowtie")

    def test_raise_if_slug_not_in_yaml(self):
        message = r"Process source given .* but process slug not found: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._register(self.resolwe_mock, self.yaml_file, "bad-slug")

    def test_update_existing_process(self):
        """If process with given slug already exists, process.filter will return list with exactly one element."""
        self.resolwe_mock.process.filter.return_value = [{'version': 16777228}]

        # local process version > server process version
        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)
        # Comfirm version was NOT raised (_version_int_to_string NOT called)
        self.assertEqual(self.resolwe_mock._version_int_to_string.call_count, 0)

        self.resolwe_mock.reset_mock()

        # local process version = server process version
        self.resolwe_mock.process.filter.return_value = [{'version': 16777229}]
        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)
        # Confirm version was NOT raised (_version_int_to_string NOT called)
        self.assertEqual(self.resolwe_mock._version_int_to_string.call_count, 1)

    def test_completely_new_process(self):
        """If process with given slug does not exist, process.filter will return empty list"""
        self.resolwe_mock.process.filter.return_value = []

        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)
        self.assertEqual(self.resolwe_mock._version_int_to_string.call_count, 0)

    def test_returns_two_processes(self):
        """
        If process process.filter will return a list of more than one
        process, this is a sign of some unexpected behaviour."""
        self.resolwe_mock.process.filter.return_value = [{}, {}]

        message = r"Unexpected behaviour at get process with slug .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")

    def test_raises_client_error(self):
        # Check raises error if slumber.exceptions.HttpClientError happens
        self.resolwe_mock.process.filter.return_value = []

        # Prepare response object & exception:
        response = requests.Response()
        response.status_code = 405
        exception = slumber.exceptions.HttpClientError(response=response)

        self.resolwe_mock.api.process.post.side_effect = exception
        with self.assertRaises(slumber.exceptions.HttpClientError):
            Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")


class TestUploadTools(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe', spec=True)
    def setUp(self, resolwe_mock):  # pylint: disable=arguments-differ
        self.resolwe_mock = resolwe_mock
        self.resolwe_mock.logger = MagicMock()
        self.tools = [os.path.normpath(os.path.dirname(__file__) + "./../files/tool1.py")]
        resolwe.TOOLS_REMOTE_HOST = "not_none"

    def test_remote_host_not_set(self):
        resolwe.TOOLS_REMOTE_HOST = None
        message = r"Define TOOLS_REMOTE_HOST environmental variable"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._upload_tools(self.resolwe_mock, self.tools)

    @patch('resdk.resolwe.subprocess')
    def test_logger_calls(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=0, **{'communicate.return_value': ['Standard output...', ' ']})
        subprocess_mock.Popen = MagicMock(return_value=fake_subprocess)

        Resolwe._upload_tools(self.resolwe_mock, self.tools)

        self.resolwe_mock.logger.info.assert_called_with('Standard output...')
        # confirm that logger.warning was not called - all went ok...
        self.assertEqual(self.resolwe_mock.logger.warning.call_count, 0)

    @patch('resdk.resolwe.subprocess')
    def test_raise_if_returncode_1(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=1, **{'communicate.return_value': ['Standard output...', 'b']})

        subprocess_mock.Popen = MagicMock(return_value=fake_subprocess)

        message = r"Tools file not found: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._upload_tools(self.resolwe_mock, self.tools)

    @patch('resdk.resolwe.subprocess')
    def test_log_if_returncode_gt1(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=2, **{'communicate.return_value': ['Standard output...', 'b']})
        subprocess_mock.Popen = MagicMock(return_value=fake_subprocess)

        Resolwe._upload_tools(self.resolwe_mock, self.tools)

        self.assertEqual(self.resolwe_mock.logger.warning.call_count, 1)


class TestProcessFileField(unittest.TestCase):

    @patch('resdk.resolwe.os', autospec=True)
    @patch('resdk.resolwe.Resolwe', autospec=True)
    def test_invalid_file_name(self, resolwe_mock, os_mock):
        os_mock.configure_mock(**{'path.isfile.return_value': False})

        message = r"File .* not found."
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._process_file_field(resolwe_mock, "/bad/path/to/file")
        self.assertEqual(resolwe_mock._upload_file.call_count, 0)

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_if_upload_fails(self, resolwe_mock, os_mock):
        # Good file, upload fails
        os_mock.configure_mock(**{'path.isfile.return_value': True})
        resolwe_mock._upload_file = MagicMock(return_value=None)

        message = r'Upload failed for .*'
        with six.assertRaisesRegex(self, Exception, message):
            Resolwe._process_file_field(resolwe_mock, "/good/path/to/file")
        self.assertEqual(resolwe_mock._upload_file.call_count, 1)

    @patch('resdk.resolwe.ntpath')
    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_if_upload_ok(self, resolwe_mock, os_mock, ntpath_mock):
        # Good file, upload fails
        os_mock.configure_mock(**{'path.isfile.return_value': True})
        resolwe_mock._upload_file = MagicMock(return_value="temporary_file")
        ntpath_mock.basename.return_value = "Basename returned!"

        output = Resolwe._process_file_field(resolwe_mock, "/good/path/to/file.txt")
        self.assertEqual(output, {'file': "Basename returned!", 'file_temp': "temporary_file"})

        resolwe_mock._upload_file.assert_called_once_with("/good/path/to/file.txt")


class TestRun(unittest.TestCase):

    def setUp(self):
        self.process_json = [
            {'slug':
                'some:prc:slug:',  # pylint: disable=bad-continuation
             'input_schema':
                [{"label": "NGS reads (FASTQ)",  # pylint: disable=bad-continuation
                  "type": "basic:file:",
                  "name": "src"},
                 {"label": "list of NGS reads",  # pylint: disable=bad-continuation
                  "type": "list:basic:file:",
                  "name": "src_list"}]}]

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_bad_descriptor_input(self, resolwe_mock):
        # Raise error is only one of deswcriptor/descriptor_schema is given:
        message = "Set both or neither descriptor and descriptor_schema."
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock, descriptor="a")
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock, descriptor_schema="a")

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_process_length_0(self, resolwe_mock):
        resolwe_mock.api = MagicMock(**{'process.get.return_value': []})
        message = "Could not get process for given slug."
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock)

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_process_length_gt1(self, resolwe_mock):
        process_out = ['process1', 'process2']
        resolwe_mock.api = MagicMock(**{'process.get.return_value': process_out})
        message = "Unexpected behaviour at get process with slug .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock)

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_bad_inputs(self, resolwe_mock, os_mock):
        # Good file, upload fails becouse of bad input keyword
        os_mock.path.isfile.return_value = True
        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_json})
        resolwe_mock._upload_file = MagicMock(return_value=None)
        message = r'Field .* not in process .* input schema.'
        with six.assertRaisesRegex(self, KeyError, message):
            Resolwe.run(resolwe_mock, input={"bad_key": "/good/path/to/file"})

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_file_processing(self, resolwe_mock, data_mock):

        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_json, 'data.post.return_value': {}})
        resolwe_mock._process_file_field = MagicMock(side_effect=[
            {'file': 'file_name1', 'file_temp': 'temp_file1'},
            {'file': 'file_name2', 'file_temp': 'temp_file2'},
            {'file': 'file_name3', 'file_temp': 'temp_file3'}])
        data_mock.return_value = "Data object"

        Resolwe.run(resolwe_mock,
                    input={"src": "/path/to/file1",
                           "src_list": ["/path/to/file2", "/path/to/file3"]})

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_call_with_all_args(self, resolwe_mock, os_mock, data_mock):
        resolwe_mock.api = MagicMock(**{
            'process.get.return_value': self.process_json,
            'data.post.return_value': "model_data"})
        data_mock.return_value = "Data object"

        data = Resolwe.run(resolwe_mock,
                           data_name="some_name",
                           descriptor="descriptor",
                           descriptor_schema="descriptor_schema",
                           collections=[1, 2, 3],
                           src="123",
                           tools="456")
        # Confirm that process was registred, tool uploaded but no files to upload in input:
        self.assertEqual(resolwe_mock._register.call_count, 1)
        self.assertEqual(resolwe_mock._upload_tools.call_count, 1)
        self.assertEqual(resolwe_mock._upload_file.call_count, 0)
        data_mock.assert_called_with(model_data='model_data', resolwe=resolwe_mock)
        self.assertEqual(data, "Data object")


class TestUploadFile(unittest.TestCase):

    def setUp(self):
        self.fn = os.path.normpath(os.path.dirname(__file__) + "./../files/example.fastq")
        self.config = {'url': 'http://some/url', 'auth': MagicMock(), 'logger': MagicMock()}

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_always_ok(self, resolwe_mock, requests_mock):
        resolwe_mock.configure_mock(**self.config)
        # Immitate response form server - always status 200:
        requests_response = {'files': [{'temp': 'fake_name'}]}
        requests_mock.post.return_value = MagicMock(status_code=200, **{'json.return_value': requests_response})

        response = Resolwe._upload_file(resolwe_mock, self.fn)

        self.assertEqual(response, 'fake_name')

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_always_bad(self, resolwe_mock, requests_mock):
        resolwe_mock.configure_mock(**self.config)
        # Immitate response form server - always status 400
        requests_mock.post.return_value = MagicMock(status_code=400)

        response = Resolwe._upload_file(resolwe_mock, self.fn)

        self.assertIsNone(response)
        self.assertEqual(resolwe_mock.logger.warning.call_count, 4)

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_one_bad_other_ok(self, resolwe_mock, requests_mock):
        resolwe_mock.configure_mock(**self.config)
        requests_response = {'files': [{'temp': 'fake_name'}]}
        response_ok = MagicMock(status_code=200, **{'json.return_value': requests_response})
        response_fails = MagicMock(status_code=400)
        # Immitate response form server - one status 400, but other 200:
        requests_mock.post.side_effect = [response_fails, response_ok, response_ok]

        response = Resolwe._upload_file(resolwe_mock, self.fn)

        self.assertEqual(response, 'fake_name')
        self.assertEqual(resolwe_mock.logger.warning.call_count, 1)


class TestDownload(unittest.TestCase):

    def setUp(self):
        self.file_list = ['/the/first/file.txt', '/the/second/file.py']
        self.config = {'url': 'http://some/url', 'auth': MagicMock(), 'logger': MagicMock()}

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_fail_if_bad_dir(self, resolwe_mock, os_mock):
        resolwe_mock.configure_mock(**self.config)
        os_mock.path.isdir.return_value = False

        message = "Download directory does not exist: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.download_files(resolwe_mock, self.file_list)

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_empty_file_list(self, resolwe_mock, os_mock):
        resolwe_mock.configure_mock(**self.config)
        os_mock.path.isfile.return_value = True

        Resolwe.download_files(resolwe_mock, [])

        resolwe_mock.logger.info.assert_called_once_with("No files to download.")

    @patch('resdk.resolwe.open')
    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_bad_response(self, resolwe_mock, requests_mock, os_mock, open_mock):
        resolwe_mock.configure_mock(**self.config)
        os_mock.path.isfile.return_value = True
        mock_open.return_value = MagicMock(spec=io.IOBase)

        response = {'raise_for_status.side_effect': Exception("abc")}
        requests_mock.get.return_value = MagicMock(ok=False, **response)

        with six.assertRaisesRegex(self, Exception, "abc"):
            Resolwe.download_files(resolwe_mock, self.file_list[:1])
        self.assertEqual(resolwe_mock.logger.info.call_count, 2)

    @patch('resdk.resolwe.open')
    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_good_response(self, resolwe_mock, requests_mock, os_mock, open_mock):
        resolwe_mock.configure_mock(**self.config)
        os_mock.path.isfile.return_value = True

        # When mocking open one wants it to return a "file-like" mock: (spec=io.IOBase)
        mock_open.return_value = MagicMock(spec=io.IOBase)

        requests_mock.get.return_value = MagicMock(ok=True, **{'iter_content.return_value': range(3)})

        Resolwe.download_files(resolwe_mock, self.file_list)
        self.assertEqual(resolwe_mock.logger.info.call_count, 3)

        # This asserts may seem wierd. To check what is happening behind the scenes:
        # print(open_mock.mock_calls)
        self.assertEqual(open_mock.return_value.__enter__.return_value.write.call_count, 6)
        # Why 6? 2 files in self.file_list, each takes 3 chunks to download (defined in response mock)


class TestResAuth(unittest.TestCase):

    @patch('resdk.resolwe.ResAuth', spec=True)
    def setUp(self, auth_mock):  # pylint: disable=arguments-differ
        self.auth_mock = auth_mock

    @patch('resdk.resolwe.requests')
    def test_bad_url(self, requests_mock):
        requests_mock.post = MagicMock(side_effect=[requests.exceptions.ConnectionError()])

        with six.assertRaisesRegex(self, ValueError, r"Server not accessible on .*. Wrong url?"):
            ResAuth.__init__(self.auth_mock, email='a', password='p', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_bad_credentials(self, requests_mock):
        requests_mock.post = MagicMock(return_value=MagicMock(status_code=400))

        message = r'Response HTTP status code .* Invalid credentials?'
        with six.assertRaisesRegex(self, ValueError, message):
            ResAuth.__init__(self.auth_mock, email='a', password='p', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_no_csrf_token(self, requests_mock):
        magic_mock1 = MagicMock(status_code=200, cookies={'sessionid': 42})
        requests_mock.post = MagicMock(return_value=magic_mock1)

        message = 'Missing sessionid or csrftoken. Invalid credentials?'
        with six.assertRaisesRegex(self, Exception, message):
            ResAuth.__init__(self.auth_mock, email='a', password='p', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_all_ok(self, requests_mock):
        magic_mock1 = MagicMock(status_code=200, cookies={'sessionid': 42, 'csrftoken': 42})
        requests_mock.post = MagicMock(return_value=magic_mock1)

        ResAuth.__init__(self.auth_mock, email='a', password='p', url='www.abc.com')

    def test_call(self):
        res_auth = MagicMock(spec=ResAuth, sessionid="", csrftoken="")
        ResAuth.__call__(res_auth, MagicMock(headers={}))


if __name__ == '__main__':
    unittest.main()
