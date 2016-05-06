import os
import unittest

import resolwe_api


class UserTest(unittest.TestCase):

    def test_user_story(self):

        # Test authentication
        email = 'admin'
        passw = 'admin'
        url = 'http://127.0.0.1:8000/'
        re = resolwe_api.Resolwe(email, passw, url)

        # Test collections:
        collections = re.collections()
        self.assertIsInstance(collections, dict)
        key0 = list(collections.keys())[0]
        self.assertIsInstance(collections[key0], resolwe_api.collection.Collection)

        # Test collections_data:
        data = re.collection_data(key0)
        self.assertIsInstance(data, list)
        self.assertIsInstance(data[0], resolwe_api.data.Data)

        # Test data:
        data = re.data(contributor="1", status="ER")
        self.assertIsInstance(data, list)
        self.assertIsInstance(data[0], resolwe_api.data.Data)

        # Test_processes:
        processes = re.processes()
        self.assertIsInstance(processes, list)
        self.assertTrue(len(processes) > 10)
        upload_process = re.processes('Upload NGS reads')
        self.assertIsInstance(upload_process, list)
        self.assertIsInstance(upload_process[0], dict)

        # Test upload (consequently also _upload_file & create)
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'example.fastq')
        re.upload('Upload NGS reads', name='name_abc', collections=[1], src=fn)

        # Test download:
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloaded.fastq.gz')
        file_stream = re.download([40], 'output.fastq')
        with open(fn, 'wb') as f:
            for part in file_stream:
                f.write(part)
        # Clean up:
        self.assertTrue(os.path.isfile(fn))
        os.remove(fn)


if __name__ == '__main__':
    unittest.main()
