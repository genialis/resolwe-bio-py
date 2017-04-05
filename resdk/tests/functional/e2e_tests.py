"""Some simple functional tests."""
# pylint: disable=missing-docstring
import os
import time
import unittest
import uuid

import six

import resdk
from resdk.resources import Collection, Data, Process, Sample

EMAIL = 'admin'
PASSW = 'admin'
URL = 'http://127.0.0.1:8000/'


def wait_for_update(resource, maxtime=10, step=1):
    """Wait for asynchronous data object processing to complete."""
    for _ in range(int(maxtime / step)):
        resource.update()
        if resource.status == "OK":
            return
        time.sleep(step)
    msg = 'Update timeout for {} with id {}'.format(resource.__class__.__name__, resource.id)
    raise Exception(msg)


class TestResolwe(unittest.TestCase):

    def setUp(self):
        self.res = resdk.Resolwe(EMAIL, PASSW, URL)
        self.reads = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/example.fastq"))
        self.yaml_path = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/custom_process.yaml"))
        self.tool1_path = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/sum.py"))

        # # Make a collection:
        colllection_json = self.res.api.collection.post({u'name': 'test_collection'})
        self.collection = Collection(model_data=colllection_json, resolwe=self.res)

        self.result = None

    def tearDown(self):
        # Remove the data object if it was created:
        if isinstance(self.result, Data):
            self.res.api.data(self.result.id).delete()
            # in this case also remove (pre)sample to which data object belongs:
            presample = self.res.presample.filter(data=self.result.id)
            if len(presample) > 0:
                self.res.api.presample(presample[0].id).delete()
            # However, it seem that if all data objects are delted from
            # (pre)sample, it is deleted autamatically. Stil, better
            # to be on the safe side.

        # Remove collection:
        if isinstance(self.collection, Collection):
            self.res.api.collection(self.collection.id).delete()

    def test_run_upload(self):
        """
        Test an upload process and confirm it produces the expected output
        """

        self.result = self.res.run(slug='upload-fastq-single', input={'src': [self.reads]})
        wait_for_update(self.result, maxtime=20, step=2)

        self.assertEqual(self.result.status, 'OK')
        self.assertEqual(self.result.process_progress, 100)
        self.assertEqual(set(self.result.output.keys()), set(['fastq', 'fastqc_url',
                                                              'fastqc_archive']))
        for key in self.result.output.keys():
            self.assertIsNotNone(self.result.output[key])

    def test_run_with_all_params(self):
        """
        Test run method with all possible params (except src & tools)
        """

        ds_schema = 'reads'
        descriptor = {'seq_date': u'2016-01-14',
                      'barcode': u'ACAGTG',
                      'barcode_removed': True,
                      'instrument_type': u'NextSeq 500'}

        self.result = self.res.run(
            slug='upload-fastq-single',
            input={'src': [self.reads]},
            descriptor=descriptor,
            descriptor_schema=ds_schema,
            collections=[self.collection.id],
            data_name='CustomDataObjectName')

        wait_for_update(self.result, maxtime=20, step=2)

        self.assertEqual(self.result.status, 'OK')

        # Ensure descriptor and descriptor schema were set correctly:
        self.assertIsNotNone(self.result.descriptor_schema)
        self.assertEqual(self.result.descriptor_schema['slug'], 'reads')
        self.assertIsNotNone(self.result.descriptor)
        self.assertEqual(self.result.descriptor, descriptor)

        # Ensure inputs are set as expected:
        six.assertRegex(
            self, self.result.input['src'][0]['file_temp'], r'\w{40}')
        self.assertEqual(self.result.input['src'][0]['file'], os.path.basename(self.reads))

        # Ensure output was produced:
        self.assertEqual(set(self.result.output.keys()), set(['fastq', 'fastqc_url',
                                                              'fastqc_archive']))
        for key in self.result.output.keys():
            self.assertIsNotNone(self.result.output[key])

        # Ensure output is of correct type:
        for key in ['fastq', 'fastqc_archive']:
            self.assertIsInstance(self.result.output[key][0]['file'], six.string_types)
            self.assertIsInstance(self.result.output[key][0]['size'], six.integer_types)

        # Confirm that data object was added to specefied collection:
        collection_where_reads = self.res.collection.get(self.collection.id)
        self.assertTrue(self.result.id in collection_where_reads.data)

        # Confirm that custom name was set:
        self.assertEqual(self.result.name, 'CustomDataObjectName')

        # Check if data object is automatically added to a (pre)sample:
        presample = self.res.presample.filter(data=self.result.id)[0]
        self.assertTrue(self.result.id in presample.data)

    def test_run_custom_process(self):
        """
        An example of run method with user defined the process

        This is and exmaple of custom process definition. It includes
        the process (defined in yaml) and also python script ``sum.py``
        that is used inside it. The process itself is very simple: it
        takes two numbers as inputs, sums them and returns result in
        form of a string.
        """
        self.result = self.res.run(
            slug='example_process',
            input={'number1': 28, 'number2': 14},
            src=self.yaml_path,
            tools=[self.tool1_path])

        wait_for_update(self.result, maxtime=30, step=3)

        # Confirm that output of this process is correct:
        self.assertEqual(self.result.output['sum'], 42)


class TestResolweQuery(unittest.TestCase):

    def setUp(self):
        self.res = resdk.Resolwe(EMAIL, PASSW, URL)
        self.reads = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/example.fastq"))
        self.data = self.res.run(slug='upload-fastq-single', input={'src': [self.reads]})
        wait_for_update(self.data, maxtime=20, step=2)
        self.contributor = self.data.contributor

        # Make collection and add self.data to it.
        json_data = self.res.api.collection.post({u'name': 'testing_collection'})
        self.collection = Collection(model_data=json_data, resolwe=self.res)

    def tearDown(self):
        # Remove the data object created in setUp method:
        self.res.api.data(self.data.id).delete()
        self.res.api.collection(self.collection.id).delete()

    def test_filter(self):
        datas = self.res.data.filter(status="OK")
        self.assertIsInstance(datas, list)
        self.assertTrue(len(datas) >= 1)
        for data in datas:
            self.assertEqual(data.status, 'OK')

        presamples = self.res.presample.filter(data=self.data.id)
        self.assertIsInstance(presamples, list)
        self.assertTrue(len(presamples) >= 1)
        for presample in presamples:
            self.assertTrue(self.data.id in presample.data)
            self.assertTrue(presample.presample)
            # move all presamples to sample endpoint (because next step):
            presample.confirm_is_annotated()

        samples = self.res.sample.filter(data=self.data.id)
        self.assertIsInstance(samples, list)
        self.assertTrue(len(samples) >= 1)
        for sample in samples:
            self.assertTrue(self.data.id in sample.data)

        collections = self.res.collection.filter(contributor=self.contributor)
        self.assertTrue(len(collections) >= 1)
        self.assertIsInstance(collections[0], Collection)
        for collection in collections:
            self.assertEqual(collection.contributor, self.contributor)

        processes = self.res.process.filter(category="analyses:alignment:")
        self.assertTrue(len(processes) >= 1)
        for process in processes:
            self.assertIsInstance(process, Process)
            self.assertEqual(process.category, "analyses:alignment:")

    def test_get(self):
        data = self.res.data.get(self.data.id)
        self.assertIsInstance(data, Data)

        presample_ = self.res.presample.filter(data=self.data.id)
        presample = self.res.presample.get(presample_[0].id)
        self.assertIsInstance(presample, Sample)
        # Now move presample from presample to sample endpoint.
        # (for the purposes of next lines testing sample)
        presample.confirm_is_annotated()

        sample = self.res.sample.get(presample.id)
        self.assertIsInstance(sample, Sample)

        collection = self.res.collection.get(self.collection.id)
        self.assertIsInstance(collection, Collection)


class TestData(unittest.TestCase):

    def setUp(self):
        self.res = resdk.Resolwe(EMAIL, PASSW, URL)
        self.reads = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/example.fastq"))
        self.basename = os.path.basename(self.reads)
        self.fastq = self.basename + ".gz"
        self.fastqc_archive = self.basename.split('.')[0] + "_fastqc.zip"
        self.data = self.res.run(slug='upload-fastq-single', input={'src': [self.reads]})
        wait_for_update(self.data, maxtime=20, step=2)

    def tearDown(self):
        # Remove the data object created in setUp method:
        self.res.api.data(self.data.id).delete()

    def test_files(self):

        flist = self.data.files()
        self.assertIsInstance(flist, list)
        self.assertTrue(len(flist) >= 1)
        self.assertEqual(set(flist), set([self.fastq, self.fastqc_archive]))

        # Confirm search fy file_name works:
        flist = self.data.files(file_name=self.fastq)
        self.assertEqual(len(flist), 1)
        self.assertEqual(flist[0], self.fastq)

        # Confirm search fy field_name works:
        field_name = 'output.fastqc_archive'
        flist = self.data.files(field_name=field_name)
        self.assertEqual(len(flist), 1)
        self.assertEqual(flist[0], self.fastqc_archive)

    def test_download(self):

        all_files = self.data.files()
        self.assertTrue(len(all_files) > 1)

        # Test download() function - no params:
        self.data.download()
        # Check if file has bee downloaded
        for fname in all_files:
            self.assertTrue(os.path.isfile(fname))
            # Then clean up = remove file
            os.remove(fname)

        # Test download() function with file_name parameter:
        self.data.download(file_name=self.fastq)
        self.assertTrue(os.path.isfile(self.fastq))
        self.assertFalse(os.path.isfile(self.fastqc_archive))
        os.remove(self.fastq)

        # Test download() function with field_name parameter:
        self.data.download(field_name='output.fastq')
        self.assertTrue(os.path.isfile(self.fastq))
        self.assertFalse(os.path.isfile(self.fastqc_archive))
        os.remove(self.fastq)

        # Test download() function with download_dir:
        dir_path = os.path.join(os.getcwd(), uuid.uuid4().__str__())
        os.mkdir(dir_path)
        self.data.download(file_name=self.fastq, download_dir=dir_path)
        self.assertTrue(os.path.isfile(os.path.join(dir_path, self.fastq)))
        self.assertFalse(os.path.isfile(os.path.join(dir_path, self.fastqc_archive)))
        os.remove(os.path.join(dir_path, self.fastq))
        os.rmdir(dir_path)

    def test_stdout(self):
        stdout_string = self.data.stdout()
        self.assertIsInstance(stdout_string, six.string_types)
        self.assertTrue(stdout_string.count('\n') > 20)
        self.assertTrue(stdout_string.count('re-save') > 1)


class TestResourceSave(unittest.TestCase):

    def setUp(self):
        self.res = resdk.Resolwe(EMAIL, PASSW, URL)
        self.remove = []

    def tearDown(self):
        for obj in self.remove:
            if obj.id:
                obj.delete()

    def _new_resource(self, resource_class, defaults={}):
        obj = resource_class(resolwe=self.res)
        self.remove.append(obj)

        for attribute, value in defaults.items():
            setattr(obj, attribute, value)

        obj.save()

        response = obj.api(obj.id).get()
        unsupported = set(obj.fields()).symmetric_difference(response.keys())
        self.assertEqual(len(unsupported), 0,
                         msg="Some fields are not supported: {}".format(', '.join(unsupported)))

        obj.slug = 'my-test'
        obj.save()

        response = obj.api(obj.id).get()
        self.assertEqual(response['slug'], obj.slug)

    def test_new_data(self):
        self._new_resource(Data, {'process': 'test-sleep-progress'})

    def test_new_collection(self):
        self._new_resource(Collection, {'name': 'my-collection'})

    def test_new_process(self):
        last_process = self.res.api.process.get(slug='my-process', ordering='-version', limit=1)
        last_process = last_process[0] if len(last_process) == 1 else {}
        last_version = last_process.get('version', 0)

        process = Process(resolwe=self.res)
        process.name = 'my-process'
        process.slug = 'my-process'
        process.type = 'data:my:process:'
        process.version = last_version + 1
        process.save()

        response = process.api(process.id).get()
        unsupported = set(process.fields()).symmetric_difference(response.keys())
        self.assertEqual(len(unsupported), 0,
                         msg="Some fields are not supported: {}".format(', '.join(unsupported)))

    def test_new_sample(self):
        sample = Sample(resolwe=self.res)
        self.remove.append(sample)

        sample.name = 'my-sample'
        sample.save()

        response = sample.api(sample.id).get()
        unsupported = set(sample.fields()).symmetric_difference(response.keys())

        self.assertEqual(len(unsupported), 1,  # presample field is not supported in Sample
                         msg="Some fields are not supported: {}".format(', '.join(unsupported)))

        sample.slug = 'my-test'
        sample.save()

        response = sample.api(sample.id).get()
        self.assertEqual(response['slug'], sample.slug)

    def test_new_presample(self):
        presample = Sample(resolwe=self.res, presample=True)
        self.remove.append(presample)

        presample.name = 'my-presample'
        presample.save()

        response = presample.api(presample.id).get()
        unsupported = set(presample.fields()).symmetric_difference(response.keys())
        self.assertEqual(len(unsupported), 0,
                         msg="Some fields are not supported: {}".format(', '.join(unsupported)))

        presample.slug = 'my-test'
        presample.save()

        response = presample.api(presample.id).get()
        self.assertEqual(response['slug'], presample.slug)


class TestBaseCollection(unittest.TestCase):

    def setUp(self):
        self.res = resdk.Resolwe(EMAIL, PASSW, URL)
        self.reads = os.path.abspath(
            os.path.normpath(os.path.dirname(__file__) + "./../files/example.fastq"))
        self.basename = os.path.basename(self.reads)
        self.fastq = self.basename + ".gz"
        self.fastqc_archive = self.basename.split('.')[0] + "_fastqc.zip"
        self.data = self.res.run(slug='upload-fastq-single', input={'src': [self.reads]})
        wait_for_update(self.data, maxtime=20, step=2)

        # Make a sample
        self.sample = self.res.presample.filter(data=self.data.id)[0]
        self.sample.confirm_is_annotated()
        # Pull the same sample down again to get it as Sample with sample endpoint:
        self.sample = self.res.sample.filter(data=self.data.id)[0]

    def tearDown(self):
        # Remove the data object created in setUp method:
        self.res.api.data(self.data.id).delete()

        # Removing all data objects from sample also removes the sample.

    def test_files(self):

        flist = self.sample.files()
        self.assertIsInstance(flist, list)
        self.assertTrue(len(flist) >= 1)
        self.assertEqual(set(flist), set([self.fastq, self.fastqc_archive]))

        # Confirm search fy file_name works:
        flist = self.sample.files(file_name=self.fastq)
        self.assertEqual(len(flist), 1)
        self.assertEqual(flist[0], self.fastq)

        # Confirm search fy field_name works:
        field_name = 'output.fastqc_archive'
        flist = self.sample.files(field_name=field_name)
        self.assertEqual(len(flist), 1)
        self.assertEqual(flist[0], self.fastqc_archive)

    def test_download(self):

        all_files = self.sample.files()
        self.assertTrue(len(all_files) > 1)

        # Test download() function - no params:
        self.sample.download()
        # Check if file has bee downloaded
        for fname in all_files:
            self.assertTrue(os.path.isfile(fname))
            # Then clean up = remove file
            os.remove(fname)

        # Test download() function with file_name parameter:
        self.sample.download(file_name=self.fastq)
        self.assertTrue(os.path.isfile(self.fastq))
        self.assertFalse(os.path.isfile(self.fastqc_archive))
        os.remove(self.fastq)

        # Test download() function with download_dir:
        dir_path = os.path.join(os.getcwd(), uuid.uuid4().__str__())
        os.mkdir(dir_path)
        self.sample.download(file_name=self.fastq, download_dir=dir_path)
        self.assertTrue(os.path.isfile(os.path.join(dir_path, self.fastq)))
        self.assertFalse(os.path.isfile(os.path.join(dir_path, self.fastqc_archive)))
        os.remove(os.path.join(dir_path, self.fastq))
        os.rmdir(dir_path)

        # Test download() function with data_type parameter:
        self.sample.download(data_type=('data:reads:fastq:', 'output.fastqc_archive'))
        self.assertTrue(os.path.isfile(self.fastqc_archive))
        self.assertFalse(os.path.isfile(self.fastq))
        os.remove(self.fastqc_archive)

        # Test download() function - param typ as abbreviation string:
        self.sample.download(data_type='fastq')
        self.assertTrue(os.path.isfile(self.fastq))
        self.assertFalse(os.path.isfile(self.fastqc_archive))
        os.remove(self.fastq)

    def test_update_descriptor(self):
        """
        This is actually method from Sample class, but for simplicity
        we will juts test it here anyway.
        """
        self.assertTrue('geo' not in self.sample.descriptor)
        descriptor = {'geo': {'organism': 'Homo Sapiens'}}
        self.sample.update_descriptor(descriptor)

        # Get same sample again and confirm that changes were accepted on Resolwe
        control = self.res.sample.get(self.sample.id)
        self.assertEqual(control.descriptor['geo']['organism'], 'Homo Sapiens')


if __name__ == '__main__':
    unittest.main()
