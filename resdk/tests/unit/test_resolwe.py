"""
Unit tests for resdk/resolwe.py file.
"""
# pylint: disable=missing-docstring, protected-access

import io
import os
import unittest

import requests
import six
import slumber
import yaml
from mock import MagicMock, mock_open, patch
from slumber.exceptions import SlumberHttpBaseException

from resdk import resolwe
from resdk.exceptions import ResolweServerError, ValidationError
from resdk.resolwe import (
    ResAuth, Resolwe, ResolweResource, version_str_to_tuple, version_tuple_to_str,
)
from resdk.resources import Collection, Data, Process

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class TestResolweResource(unittest.TestCase):
    def setUp(self):
        self.resource = ResolweResource()
        self.method_mock = MagicMock(
            side_effect=[42, SlumberHttpBaseException(content='error mesage')])

    def test_get_wrapped(self):
        self.resource.get = self.method_mock
        self.assertEqual(self.resource.get(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.get()

    def test_options_wrapped(self):
        self.resource.options = self.method_mock
        self.assertEqual(self.resource.options(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.options()

    def test_head_wrapped(self):
        self.resource.head = self.method_mock
        self.assertEqual(self.resource.head(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.head()

    def test_post_wrapped(self):
        self.resource.post = self.method_mock
        self.assertEqual(self.resource.post(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.post()

    def test_patch_wrapped(self):
        self.resource.patch = self.method_mock
        self.assertEqual(self.resource.patch(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.patch()

    def test_put_wrapped(self):
        self.resource.put = self.method_mock
        self.assertEqual(self.resource.put(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.put()

    def test_delete_wrapped(self):
        self.resource.delete = self.method_mock
        self.assertEqual(self.resource.delete(), 42)

        with self.assertRaises(ResolweServerError):
            self.resource.delete()


class TestResolwe(unittest.TestCase):

    @patch('resdk.resolwe.logging')
    @patch('resdk.resolwe.ResolweQuery')
    @patch('resdk.resolwe.ResolweAPI')
    @patch('resdk.resolwe.slumber')
    @patch('resdk.resolwe.ResAuth')
    @patch('resdk.resolwe.Resolwe', spec=Resolwe)
    def test_init(self, resolwe_mock, resauth_mock, slumber_mock, resolwe_api_mock,
                  resolwe_querry_mock, log_mock):
        Resolwe.__init__(resolwe_mock, 'a', 'b', 'http://some/url')
        self.assertEqual(resauth_mock.call_count, 1)
        self.assertEqual(resolwe_api_mock.call_count, 1)
        # There are seven instances of ResolweQuery in init: data, process, sample, relations,
        # collection, feature and mapping.
        self.assertEqual(resolwe_querry_mock.call_count, 7)
        self.assertEqual(log_mock.getLogger.call_count, 1)

    def test_repr(self):
        resolwe_mock = MagicMock(spec=Resolwe, url='www.abc.com')

        resolwe_mock.auth = MagicMock(username='user')
        rep = Resolwe.__repr__(resolwe_mock)
        self.assertEqual(rep, 'Resolwe <url: www.abc.com, username: user>')

        resolwe_mock.auth = MagicMock(username=None)
        rep = Resolwe.__repr__(resolwe_mock)
        self.assertEqual(rep, 'Resolwe <url: www.abc.com>')

    @patch('resdk.resolwe.ResAuth')
    def test_env_variables(self, resauth_mock):
        # Ensure environmental variables are not set.
        os.environ.pop('RESOLWE_API_HOST', None)
        os.environ.pop('RESOLWE_API_USERNAME', None)
        os.environ.pop('RESOLWE_API_PASSWORD', None)

        # Default URL should be used by default.
        resolwe_api = Resolwe()
        self.assertEqual(resolwe_api.url, 'http://localhost:8000')
        self.assertEqual(resauth_mock.call_args[0][0], None)
        self.assertEqual(resauth_mock.call_args[0][1], None)

        # If environment variable is set, it overrides the default URL.
        os.environ['RESOLWE_API_USERNAME'] = 'foo'
        os.environ['RESOLWE_API_PASSWORD'] = 'bar'

        os.environ['RESOLWE_HOST_URL'] = 'http://resolwe-api:8000'
        resolwe_api = Resolwe()
        self.assertEqual(resolwe_api.url, 'http://resolwe-api:8000')
        self.assertEqual(resauth_mock.call_args[0][0], 'foo')
        self.assertEqual(resauth_mock.call_args[0][1], 'bar')

        # `RESOLWE_HOST_URL` takes precedence
        os.environ['RESOLWE_API_HOST'] = 'http://resolwe-api:9000'
        resolwe_api = Resolwe()
        self.assertEqual(resolwe_api.url, 'http://resolwe-api:8000')
        self.assertEqual(resauth_mock.call_args[0][0], 'foo')
        self.assertEqual(resauth_mock.call_args[0][1], 'bar')

        os.environ.pop('RESOLWE_HOST_URL')
        resolwe_api = Resolwe()
        self.assertEqual(resolwe_api.url, 'http://resolwe-api:9000')
        self.assertEqual(resauth_mock.call_args[0][0], 'foo')
        self.assertEqual(resauth_mock.call_args[0][1], 'bar')


class TestVersionConverters(unittest.TestCase):

    def test_version_string_to_tuple(self):
        self.assertEqual(version_str_to_tuple('1.0.2'), (1, 0, 2))

    def test_version_tuple_to_string(self):
        self.assertEqual(version_tuple_to_str((1, 0, 2)), '1.0.2')


class TestRegister(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe', spec=True)
    def setUp(self, resolwe_mock):  # pylint: disable=arguments-differ
        self.yaml_file = os.path.join(BASE_DIR, 'files', 'bowtie.yaml')
        self.bad_yaml_file = os.path.join(BASE_DIR, 'files', 'bowtie_bad.yaml')
        self.resolwe_mock = resolwe_mock
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
        """If process exists, process.filter returns list with exactly one element."""
        # local process version > server process version
        self.resolwe_mock.process.filter.return_value = [MagicMock(version='1.0.12')]
        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)
        self.assertEqual(self.resolwe_mock.api.process.post.call_args[0][0]['version'], '1.0.13')

        self.resolwe_mock.reset_mock()

        # local process version = server process version
        self.resolwe_mock.process.filter.return_value = [MagicMock(version='1.0.13')]
        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)
        self.assertEqual(self.resolwe_mock.api.process.post.call_args[0][0]['version'], '1.0.14')

    def test_completely_new_process(self):
        """If process with given slug does not exist, process.filter will return empty list"""
        self.resolwe_mock.process.filter.return_value = []

        Resolwe._register(self.resolwe_mock, self.yaml_file, "alignment-bowtie")
        self.assertEqual(self.resolwe_mock.api.process.post.call_count, 1)

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
        self.tools = [os.path.join(BASE_DIR, 'files', 'tool1.py')]
        resolwe.TOOLS_REMOTE_HOST = "not_none"

    def test_remote_host_not_set(self):
        resolwe.TOOLS_REMOTE_HOST = None
        message = r"Define TOOLS_REMOTE_HOST environmental variable"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._upload_tools(self.resolwe_mock, self.tools)

    @patch('resdk.resolwe.os')
    def test_tools_file_not_found(self, os_mock):
        resolwe.TOOLS_REMOTE_HOST = 'something'
        os_mock.configure_mock(**{'path.isfile.return_value': False})

        message = r"Tools file not found: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._upload_tools(self.resolwe_mock, self.tools)

    @patch('resdk.resolwe.subprocess')
    def test_logger_calls(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=0,
                                    **{'communicate.return_value': ['Standard output...', ' ']})
        subprocess_mock.Popen = MagicMock(return_value=fake_subprocess)

        Resolwe._upload_tools(self.resolwe_mock, self.tools)

        self.resolwe_mock.logger.info.assert_called_with('Standard output...')
        # confirm that logger.warning was not called - all went ok...
        self.assertEqual(self.resolwe_mock.logger.warning.call_count, 0)

    @patch('resdk.resolwe.subprocess')
    def test_raise_if_returncode_1(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=1,
                                    **{'communicate.return_value': ['Standard output...', 'b']})

        subprocess_mock.Popen = MagicMock(return_value=fake_subprocess)

        message = r"Something wrong while SCP for tool: .*"
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe._upload_tools(self.resolwe_mock, self.tools)

    @patch('resdk.resolwe.subprocess')
    def test_log_if_returncode_gt1(self, subprocess_mock):
        fake_subprocess = MagicMock(returncode=2,
                                    **{'communicate.return_value': ['Standard output...', 'b']})
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

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_url(self, resolwe_mock):
        output = Resolwe._process_file_field(resolwe_mock, "http://www.example.com/reads.fq.gz")
        self.assertEqual(
            output, {'file': "reads.fq.gz", 'file_temp': "http://www.example.com/reads.fq.gz"})


class TestRun(unittest.TestCase):

    def setUp(self):
        self.process_mock = MagicMock(spec=Process)
        self.process_mock.slug = 'some:prc:slug:'
        self.process_mock.input_schema = [
            {
                "label": "NGS reads (FASTQ)",
                "type": "basic:file:",
                "required": "false",
                "name": "src"
            },
            {
                "label": "list of NGS reads",
                "type": "list:basic:file:",
                "required": "false",
                "name": "src_list"
            },
            {
                "label": "Genome object",
                "type": "data:genome:fasta:",
                "required": "false",
                "name": "genome"
            },
            {
                "label": "List of reads objects",
                "type": "list:data:reads:fastg:",
                "required": "false",
                "name": "reads"
            },
        ]

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_run_process(self, resolwe_mock, data_mock):
        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_mock})

        Resolwe.run(resolwe_mock)
        self.assertEqual(resolwe_mock.api.data.post.call_count, 1)

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_get_or_run(self, resolwe_mock, data_mock):
        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_mock})

        Resolwe.get_or_run(resolwe_mock)
        self.assertEqual(resolwe_mock.api.data.get_or_create.post.call_count, 1)

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_wrap_list(self, resolwe_mock):
        process = self.process_mock

        Resolwe._process_inputs(resolwe_mock, {"src_list": ["/path/to/file"]}, process)
        resolwe_mock._process_file_field.assert_called_once_with('/path/to/file')

        resolwe_mock.reset_mock()
        Resolwe._process_inputs(resolwe_mock, {"src_list": "/path/to/file"}, process)
        resolwe_mock._process_file_field.assert_called_once_with('/path/to/file')

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_keep_input(self, resolwe_mock):
        process = self.process_mock

        input_dict = {"src_list": ["/path/to/file"]}
        Resolwe._process_inputs(resolwe_mock, input_dict, process)
        self.assertEqual(input_dict, {"src_list": ["/path/to/file"]})

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_bad_descriptor_input(self, resolwe_mock):
        # Raise error is only one of deswcriptor/descriptor_schema is given:
        message = "Set both or neither descriptor and descriptor_schema."
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock, descriptor="a")
        with six.assertRaisesRegex(self, ValueError, message):
            Resolwe.run(resolwe_mock, descriptor_schema="a")

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_bad_inputs(self, resolwe_mock, os_mock):
        # Good file, upload fails becouse of bad input keyword
        os_mock.path.isfile.return_value = True
        process = self.process_mock

        resolwe_mock._upload_file = MagicMock(return_value=None)
        message = r'Field .* not in process .* input schema.'
        with six.assertRaisesRegex(self, ValidationError, message):
            Resolwe._process_inputs(resolwe_mock, {"bad_key": "/good/path/to/file"}, process)

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_file_processing(self, resolwe_mock, data_mock):

        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_mock,
                                        'data.post.return_value': {}})
        resolwe_mock._process_file_field = MagicMock(side_effect=[
            {'file': 'file_name1', 'file_temp': 'temp_file1'},
            {'file': 'file_name2', 'file_temp': 'temp_file2'},
            {'file': 'file_name3', 'file_temp': 'temp_file3'}])
        data_mock.return_value = "Data object"

        Resolwe.run(resolwe_mock,
                    input={"src": "/path/to/file1",
                           "src_list": ["/path/to/file2", "/path/to/file3"]})

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_dehydrate_data(self, resolwe_mock):
        data_obj = Data(id=1, resolwe=MagicMock())
        data_obj.id = 1  # this is overriden when initialized
        process = self.process_mock

        result = Resolwe._process_inputs(resolwe_mock, {"genome": data_obj}, process)
        self.assertEqual(result, {'genome': 1})

        result = Resolwe._process_inputs(resolwe_mock, {"reads": [data_obj]}, process)
        self.assertEqual(result, {'reads': [1]})

    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_dehydrate_collections(self, resolwe_mock):
        resolwe_mock.configure_mock(
            **{'_get_process.return_value': MagicMock(spec=Process, slug='some:prc:slug:'),
               '_process_inputs.return_value': {}}
        )
        resolwe_mock.collection = MagicMock()
        resolwe_mock.api = MagicMock(**{'process.get.return_value': self.process_mock,
                                        'data.post.return_value': {}})

        collection = Collection(id=1, resolwe=MagicMock())
        collection.id = 1  # this is overriden when initialized

        Resolwe.run(resolwe_mock, collections=[collection])
        resolwe_mock.api.data.post.assert_called_once_with(
            {'process': 'some:prc:slug:', 'input': {}, 'collections': [1]})

    @patch('resdk.resolwe.Data')
    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_call_with_all_args(self, resolwe_mock, os_mock, data_mock):
        resolwe_mock.api = MagicMock(**{
            'process.get.return_value': self.process_mock,
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
        self.file_path = os.path.join(BASE_DIR, 'files', 'example.fastq')
        self.config = {'url': 'http://some/url', 'auth': MagicMock(), 'logger': MagicMock()}

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_always_ok(self, resolwe_mock, requests_mock):
        resolwe_mock.configure_mock(**self.config)
        # Immitate response form server - always status 200:
        requests_response = {'files': [{'temp': 'fake_name'}]}
        requests_mock.post.return_value = MagicMock(status_code=200,
                                                    **{'json.return_value': requests_response})

        response = Resolwe._upload_file(resolwe_mock, self.file_path)

        self.assertEqual(response, 'fake_name')

    @patch('resdk.resolwe.requests')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_always_bad(self, resolwe_mock, requests_mock):
        resolwe_mock.configure_mock(**self.config)
        # Immitate response form server - always status 400
        requests_mock.post.return_value = MagicMock(status_code=400)

        response = Resolwe._upload_file(resolwe_mock, self.file_path)

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

        response = Resolwe._upload_file(resolwe_mock, self.file_path)

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
            Resolwe._download_files(resolwe_mock, self.file_list)

    @patch('resdk.resolwe.os')
    @patch('resdk.resolwe.Resolwe', spec=True)
    def test_empty_file_list(self, resolwe_mock, os_mock):
        resolwe_mock.configure_mock(**self.config)

        Resolwe._download_files(resolwe_mock, [])

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
            Resolwe._download_files(resolwe_mock, self.file_list[:1])
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

        requests_mock.get.return_value = MagicMock(ok=True,
                                                   **{'iter_content.return_value': range(3)})

        Resolwe._download_files(resolwe_mock, self.file_list)
        self.assertEqual(resolwe_mock.logger.info.call_count, 3)

        # This asserts may seem wierd. To check what is happening behind the scenes:
        # print(open_mock.mock_calls)
        self.assertEqual(open_mock.return_value.__enter__.return_value.write.call_count, 6)
        # Why 6? 2 files in self.file_list, each downloads 3 chunks (defined in response mock)


class TestResAuth(unittest.TestCase):

    @patch('resdk.resolwe.ResAuth', spec=True)
    def setUp(self, auth_mock):  # pylint: disable=arguments-differ
        auth_mock.configure_mock(sessionid=None, csrftoken=None)
        self.auth_mock = auth_mock

    @patch('resdk.resolwe.requests')
    def test_bad_url(self, requests_mock):
        requests_mock.post = MagicMock(side_effect=[requests.exceptions.ConnectionError()])

        with six.assertRaisesRegex(self, ValueError,
                                   'Server not accessible on www.abc.com. Wrong url?'):
            ResAuth.__init__(self.auth_mock, username='usr', password='pwd', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_bad_credentials(self, requests_mock):
        requests_mock.post = MagicMock(return_value=MagicMock(status_code=400))

        message = r'Response HTTP status code .* Invalid credentials?'
        with six.assertRaisesRegex(self, ValueError, message):
            ResAuth.__init__(self.auth_mock, username='usr', password='pwd', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_no_csrf_token(self, requests_mock):
        post_mock = MagicMock(status_code=200, cookies={'sessionid': 42})
        requests_mock.post = MagicMock(return_value=post_mock)

        message = 'Missing sessionid or csrftoken. Invalid credentials?'
        with six.assertRaisesRegex(self, Exception, message):
            ResAuth.__init__(self.auth_mock, username='usr', password='pwd', url='www.abc.com')

    @patch('resdk.resolwe.requests')
    def test_all_ok(self, requests_mock):
        post_mock = MagicMock(status_code=200, cookies={'sessionid': 42, 'csrftoken': 43})
        requests_mock.post = MagicMock(return_value=post_mock)

        ResAuth.__init__(self.auth_mock, username='usr', password='pwd', url='www.abc.com')
        self.assertEqual(self.auth_mock.sessionid, 42)
        self.assertEqual(self.auth_mock.csrftoken, 43)

    @patch('resdk.resolwe.requests')
    def test_public_user(self, requests_mock):
        post_mock = MagicMock(status_code=200)
        requests_mock.post = MagicMock(return_value=post_mock)

        ResAuth.__init__(self.auth_mock, url='www.abc.com')
        self.assertEqual(self.auth_mock.sessionid, None)
        self.assertEqual(self.auth_mock.csrftoken, None)

    def test_call(self):
        res_auth = MagicMock(spec=ResAuth, sessionid=None, csrftoken=None, url="www.abc.com")
        resp = ResAuth.__call__(res_auth, MagicMock(headers={}))
        self.assertDictEqual(resp.headers, {'referer': 'www.abc.com'})

        res_auth = MagicMock(spec=ResAuth, sessionid='my-id', csrftoken='my-token', url="abc.com")
        resp = ResAuth.__call__(res_auth, MagicMock(headers={}))
        self.assertDictEqual(resp.headers, {
            'X-CSRFToken': 'my-token',
            'referer': 'abc.com',
            'Cookie': 'csrftoken=my-token; sessionid=my-id'
        })


if __name__ == '__main__':
    unittest.main()
