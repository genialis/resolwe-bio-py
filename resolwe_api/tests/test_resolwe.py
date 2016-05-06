import os
import unittest

from mock import patch, MagicMock
import requests
from slumber.exceptions import HttpNotFoundError

from resolwe_api.resolwe import Resolwe, ResAuth
from resolwe_api import Data, Collection
from DATA import COLLECTIONS_SAMPLE, COLLECTIONS_SAMPLE_2, PROCESS_SAMPLE, DATA_SAMPLE


class TestResolweCollections(unittest.TestCase):

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_collections_if_cache_not_empty(self, resolwe_mock):

        # Add 'cache' attribute to mock object and set its value:
        resolwe_mock.configure_mock(cache={'collections': {'id1': 'some collection object'}})
        # resolwe_mock does not have api attribute by default -> create it:
        resolwe_mock.api = MagicMock()
        self.assertEqual(Resolwe.collections(resolwe_mock), {'id1': 'some collection object'})
        # Ensure that output was not generated from calling api.collections.get():
        self.assertEqual(len(resolwe_mock.api.mock_calls), 0)
        collection_mock = MagicMock('resolwe_api.resolwe.Collection')
        self.assertEqual(len(collection_mock.mock_calls), 0)

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_collections_if_cache_empty(self, resolwe_mock):

        # This is the default cache when Resolwe __init__ is executed.
        resolwe_mock.cache = {
                                'data': {},
                                'collections': None,
                                'collections_data': {}
                            }
        # Specify what should be returned when api.collection.get() is called.
        resolwe_mock.api = MagicMock(**{'collection.get.return_value': COLLECTIONS_SAMPLE})
        collection_mock = MagicMock('resolwe_api.resolwe.Collection')

        r = Resolwe.collections(resolwe_mock)
        self.assertIsInstance(list(r.values())[0], Collection)
        self.assertEqual(str(r), '{21: Collection: 21 - TestCollection}')
        self.assertEqual(len(resolwe_mock.api.mock_calls), 1)
        self.assertEqual(len(collection_mock.mock_calls), 0)


class TestResolweCollectionData(unittest.TestCase):

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_collection_data(self, resolwe_mock):

        # Case#1: cache has data for desired collection; collection is valid id number:
        resolwe_mock.cache = {'data': {}, 'collections': None, 'collections_data': {42: 'bla'}}
        r = Resolwe.collection_data(resolwe_mock, 42)
        self.assertEqual(r, 'bla')

        # Case#2: cache has data for desired collection; collection is valid slug:
        resolwe_mock.cache = {'data': {}, 'collections': None, 'collections_data': {42: 'bla'}}
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.collection.get = MagicMock(return_value=[{'slug': 'valid_slug', 'id': 42}])
        r = Resolwe.collection_data(resolwe_mock, 'valid_slug')
        self.assertEqual(r, 'bla')

        # Case#3: cache has data for desired collection; collection is NOT a valid slug:
        resolwe_mock.cache = {'data': {}, 'collections': None, 'collections_data': {42: 'bla'}}
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.collection.get = MagicMock(return_value=[])
        with self.assertRaises(ValueError) as exc:
            Resolwe.collection_data(resolwe_mock, 'invalid_slug')
        m = r"Parameter .* is not a valid collection slug"
        self.assertRegexpMatches(exc.exception.args[0], m)

        # Case#4: non-existent collection ID:
        resolwe_mock.cache = {'data': {}, 'collections': None, 'collections_data': {42: 'bla'}}
        m1 = MagicMock(**{'get.side_effect': [HttpNotFoundError()]})
        resolwe_mock.api = MagicMock(**{'collection.return_value': m1})
        with self.assertRaises(ValueError) as exc:
            Resolwe.collection_data(resolwe_mock, 43)
        self.assertRegexpMatches(exc.exception.args[0], r"Collections id .* does not exist")

        # Case#5: cache is empty; collection is a valid id number:
        resolwe_mock.cache = {'data': {}, 'collections': None, 'collections_data': {}}
        m1 = MagicMock(**{'get.return_value': COLLECTIONS_SAMPLE_2})
        m2 = MagicMock(**{'get.side_effect': [DATA_SAMPLE[0], DATA_SAMPLE[1]]})
        resolwe_mock.api = MagicMock(**{'collection.return_value': m1, 'data.return_value': m2})
        r = Resolwe.collection_data(resolwe_mock, 1)
        self.assertEqual(str(r), '[Data: 13 - Name1, Data: 14 - Name2]')


class TestResolweData(unittest.TestCase):

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_data(self, resolwe_mock):

        resolwe_mock.cache = {'data': {}}
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.data.get = MagicMock(return_value=DATA_SAMPLE[1:2])

        r = Resolwe.data(resolwe_mock, status='ER')

        self.assertEqual(len(r), 1)


class TestResolweProcesses(unittest.TestCase):

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_process_without_process_name(self, resolwe_mock):
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.process.get = MagicMock(return_value=PROCESS_SAMPLE)

        r = Resolwe.processes(resolwe_mock)

        self.assertIsInstance(r, list)
        self.assertEqual(len(r), 4)
        self.assertIsInstance(r[0], dict)
        self.assertEqual(r[0]['name'], 'Upload NGS reads')
        self.assertEqual(len(resolwe_mock.api.mock_calls), 1)

    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_process_with_process_name(self, resolwe_mock):
        resolwe_mock.api = MagicMock()
        resolwe_mock.api.process.get = MagicMock(return_value=PROCESS_SAMPLE)

        r = Resolwe.processes(resolwe_mock, 'Variant filtering (Chemical Mutagenesis)')

        self.assertIsInstance(r, list)
        self.assertEqual(len(r), 1)
        self.assertIsInstance(r[0], dict)
        self.assertEqual(r[0]['name'], 'Variant filtering (Chemical Mutagenesis)')
        self.assertEqual(len(resolwe_mock.api.mock_calls), 1)


class TestResolwePrintUploadProcesses(unittest.TestCase):

    @patch('resolwe_api.resolwe.sys', spec=True)
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_print_upload_processes(self, resolwe_mock, sys_mock):

        # Check output is correct
        resolwe_mock.processes.return_value = PROCESS_SAMPLE
        sys_mock.stdout.write = MagicMock()
        Resolwe.print_upload_processes(resolwe_mock)
        sys_mock.stdout.write.assert_called_with('Upload NGS reads\n')


class TestResolwePrintProcessInputs(unittest.TestCase):

    @patch('resolwe_api.resolwe.sys', spec=True)
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_print_process_inpts(self, resolwe_mock, sys_mock):

        # Bad processor name:
        resolwe_mock.processes.return_value = []
        with self.assertRaises(Exception) as exc:
            Resolwe.print_process_inputs(resolwe_mock, 'Bad processor name')
        self.assertRegexpMatches(exc.exception.args[0], r"Invalid process name: .*.")

        # Check output is correct
        resolwe_mock.processes.return_value = PROCESS_SAMPLE
        sys_mock.stdout.write = MagicMock()
        Resolwe.print_process_inputs(resolwe_mock, 'Upload NGS reads')
        sys_mock.stdout.write.assert_called_with('src -> basic:file:')


class TestResolweCreate(unittest.TestCase):

    @patch('resolwe_api.resolwe.requests')
    @patch('resolwe_api.resolwe.urlparse')
    @patch('resolwe_api.resolwe.json')
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_create(self, resolwe_mock, json_mock, urlparse_mock, requests_mock):
        resolwe_mock.url = 'http://some/url'
        resolwe_mock.auth = MagicMock()
        json_mock.dumps = MagicMock(return_value="whatever")
        urlparse_mock.urljoin = MagicMock()
        requests_mock.post = MagicMock(return_value="Something!")

        r = Resolwe.create(resolwe_mock, {"a": "b"})
        self.assertEqual(json_mock.dumps.call_count, 1)
        json_mock.dumps.assert_called_with({"a": "b"})

        # Raise error if data is not dict/str:
        self.assertRaises(ValueError, Resolwe.create, *(resolwe_mock, 666))

        json_mock.dumps.reset_mock()
        r = Resolwe.create(resolwe_mock, "some input")
        self.assertEqual(json_mock.dumps.call_count, 0)
        self.assertEqual(r, "Something!")

        # Raise error on bad name for resource
        self.assertRaises(ValueError, Resolwe.create,
                          *(resolwe_mock, "some input"),
                          **{'resource': "bad_name"})


class TestResolweUpload(unittest.TestCase):

    @patch('resolwe_api.resolwe.os')
    @patch('resolwe_api.resolwe.uuid')
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_upload(self, resolwe_mock, uuid_mock, os_mock):

        # Bad processor name:
        resolwe_mock.processes.return_value = []
        with self.assertRaises(Exception) as exc:
            Resolwe.upload(resolwe_mock, 'Bad processor name')
        self.assertRegexpMatches(exc.exception.args[0], r"Invalid process name: .*.")

        # Bad processor inputs - bad keyword name
        resolwe_mock.processes.side_effect = [PROCESS_SAMPLE, PROCESS_SAMPLE[:1]]
        with self.assertRaises(Exception) as exc:
            Resolwe.upload(resolwe_mock, 'Upload NGS reads', bad_key="Blah.")
        self.assertRegexpMatches(exc.exception.args[0], r"Field .* not in process .* inputs.")

        # Bad processor inputs - bad keyword value:
        resolwe_mock.processes.side_effect = [PROCESS_SAMPLE, PROCESS_SAMPLE[:1]]
        os_mock.path.isfile.return_value = False
        with self.assertRaises(Exception) as exc:
            Resolwe.upload(resolwe_mock, 'Upload NGS reads', src="/bad/file/name")
        self.assertRegexpMatches(exc.exception.args[0], r"File .* not found")

        # Function _upload_file returns None (upload failed):
        resolwe_mock.processes.side_effect = [PROCESS_SAMPLE, PROCESS_SAMPLE[:1]]
        os_mock.path.isfile.return_value = True  # meke look like file is ok
        resolwe_mock._upload_file.return_value = None
        with self.assertRaises(Exception) as exc:
            Resolwe.upload(resolwe_mock, 'Upload NGS reads', src="/file/path")
        self.assertRegexpMatches(exc.exception.args[0], r"Upload failed for .*.")

        # All good:
        resolwe_mock.processes.side_effect = [PROCESS_SAMPLE, PROCESS_SAMPLE[:1]]
        os_mock.path.isfile.return_value = True  # pretend it is a valid file name
        UUID = '0'*10
        resolwe_mock._upload_file.return_value = UUID
        uuid_mock.uuid4.return_value = UUID

        r = Resolwe.upload(resolwe_mock, 'Upload NGS reads', src="/a/b/c/test.txt")

        resolwe_mock._upload_file.assert_called_with("/a/b/c/test.txt")
        d = {u'status': u'uploading',
             u'process': u'import-upload-reads-fastq',
             u'slug': '0000000000',
             u'name': '',
             u'input': {'src': {u'file_temp': '0000000000', u'file': 'test.txt'}}}
        resolwe_mock.create.assert_called_with(d)


class TestResolweUploadFile(unittest.TestCase):

    @patch('resolwe_api.resolwe.requests')
    @patch('resolwe_api.resolwe.sys')
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_upload_file(self, resolwe_mock, sys_mock, requests_mock):
        # Example file:
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'example.fastq')

        resolwe_mock.url = 'http://some/url'

        resolwe_mock.auth = MagicMock()
        # Supress upload progress messages:
        sys_mock.sys.stdout.write = MagicMock()
        sys_mock.sys.stdout.flush = MagicMock()

        # Immitate response form server - always status 200
        m1 = {'files': [{'temp': 'fake_name'}]}
        requests_mock.post.return_value = MagicMock(status_code=200, **{'json.return_value': m1})
        r = Resolwe._upload_file(resolwe_mock, fn)
        self.assertEqual(r, 'fake_name')

        # Immitate response form server - always status 400
        requests_mock.post.return_value = MagicMock(status_code=400)
        r = Resolwe._upload_file(resolwe_mock, fn)
        self.assertIsNone(r)

        # Immitate response form server - one status 400, but other 200
        m0 = {'files': [{'temp': 'fake_name'}]}
        m1 = MagicMock(status_code=200, **{'json.return_value': m0})
        m2 = MagicMock(status_code=400)
        requests_mock.post.side_effect = [m1, m2, m1, m1]
        r = Resolwe._upload_file(resolwe_mock, fn)
        self.assertEqual(r, 'fake_name')


class TestResolweDownload(unittest.TestCase):

    @patch('resolwe_api.resolwe.urlparse', spec=True)
    @patch('resolwe_api.resolwe.requests', spec=True)
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_download(self, resolwe_mock, requests_mock, url_mock):

        # Case#1: Field != "output.*"
        with self.assertRaises(ValueError) as exc:
            Resolwe.download(resolwe_mock, [1], 'somthing.wierd')
        m = "Only process results (output.* fields) can be downloaded."
        self.assertEqual(exc.exception.args[0], m)

        # Case#2: Invalid object ID:
        with self.assertRaises(ValueError) as exc:
            Resolwe.download(resolwe_mock, ['not_a_number'], 'output.abc')
        self.assertRegexpMatches(exc.exception.args[0], "Invalid object id .*")

        # Case#3: not in cache, bad ID
        resolwe_mock.cache = {'data': {}}
        m1 = MagicMock(**{'get.side_effect': [HttpNotFoundError()]})
        resolwe_mock.api = MagicMock(**{'data.return_value': m1})
        with self.assertRaises(ValueError) as exc:
            Resolwe.download(resolwe_mock, [123], 'output.abc')
        self.assertRegexpMatches(exc.exception.args[0], "Data id .* does not exist.")

        # Case#4: data ID not in cache, field not in annotation
        m1 = MagicMock(**{'get.return_value': DATA_SAMPLE[0]})
        resolwe_mock.api = MagicMock(**{'data.return_value': m1})
        with self.assertRaises(ValueError) as exc:
            Resolwe.download(resolwe_mock, [13], 'output.abc')
        m = "Field .* does not exist for data object .*."
        self.assertRegexpMatches(exc.exception.args[0], m)

        # Case#5: filend type not basic:file:
        with self.assertRaises(ValueError) as exc:
            Resolwe.download(resolwe_mock, [13], 'output.bases')
        self.assertEqual(exc.exception.args[0], "Only basic:file: fields can be downloaded.")

        # Case#6: Requests response with status code 404:
        resolwe_mock.url = 'http://some/url'
        resolwe_mock.auth = 'any_object'
        url_mock.urljoin.return_value = 'http://another/url'
        m1 = MagicMock(**{'raise_for_status.side_effect': [requests.exceptions.HTTPError()]})
        m1.configure_mock(ok=False)
        requests_mock.get.return_value = m1
        with self.assertRaises(requests.exceptions.HTTPError) as exc:
            Resolwe.download(resolwe_mock, [13], 'output.fastq')

        # "All good" scenario should be tested in end-to-end tests.


class TestResolweResAuth(unittest.TestCase):

    @patch('resolwe_api.resolwe.requests')
    @patch('resolwe_api.resolwe.ResAuth', spec=True)
    @patch('resolwe_api.resolwe.Resolwe', spec=True)
    def test_res_auth(self, resolwe_mock, auth_mock, requests_mock):

        # Wrong URL:
        requests_mock.post = MagicMock(side_effect=[requests.exceptions.ConnectionError()])
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        self.assertRegexpMatches(exc.exception.args[0], r"Server not accessible on .*.")

        # Wrong credentials:
        m1 = MagicMock(status_code=400)
        requests_mock.post = MagicMock(return_value=m1)
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        m = r'Response HTTP status code .* Invalid credentials?'
        self.assertRegexpMatches(exc.exception.args[0], m)

        # NO CSRF token:
        m1 = MagicMock(status_code=200, cookies={'sessionid': 42})
        requests_mock.post = MagicMock(return_value=m1)
        with self.assertRaises(Exception) as exc:
            ResAuth.__init__(auth_mock, email='a', password='p', url='www.abc.com')
        m = 'Missing sessionid or csrftoken. Invalid credentials?'
        self.assertRegexpMatches(exc.exception.args[0], m)

        # "All good" scenario should be tested in end-to-end tests.

if __name__ == '__main__':
    unittest.main()
