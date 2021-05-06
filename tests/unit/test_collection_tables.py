import unittest
from datetime import datetime
from time import sleep, time

import pandas as pd
import pytz
from mock import MagicMock, patch
from pandas.testing import assert_frame_equal

from resdk import CollectionTables
from resdk.collection_tables import EXP, META, RC


class TestCollectionTables(unittest.TestCase):
    def setUp(self):
        self.resolwe = MagicMock()
        self.resolwe.url = "https://server.com"

        self.sample = MagicMock()
        self.sample.id = 123
        self.sample.name = "Sample123"
        self.sample.modified = datetime(
            2020, 11, 1, 12, 15, 0, 0, tzinfo=pytz.UTC
        ).astimezone(pytz.timezone("Europe/Ljubljana"))
        self.sample.descriptor_schema.schema = [
            {"name": "PFS", "type": "basic:decimal:", "label": "P"}
        ]
        self.sample.descriptor = {"PFS": 1}

        self.data = MagicMock()
        self.data.id = 12345
        self.data.process.slug = "process-slug"
        self.data.output.__getitem__.side_effect = {
            "species": "Homo sapiens",
            "source": "ENSEMBL",
            "exp_type": "TPM",
        }.__getitem__

        self.orange_data = MagicMock()
        self.orange_data.id = 89
        self.orange_data.files.return_value = ["table.tsv"]
        self.orange_data.modified = datetime(
            2020, 9, 1, 12, 15, 0, 0, tzinfo=pytz.UTC
        ).astimezone(pytz.timezone("Europe/Ljubljana"))

        self.collection = MagicMock()
        self.collection.slug = "slug"
        self.collection.name = "Name"
        self.collection.samples.filter = self.web_request([self.sample])
        self.collection.data.filter = self.web_request([self.data])
        self.collection.resolwe = self.resolwe

        self.relation = MagicMock()
        self.relation.modified = datetime(
            2020, 10, 1, 12, 15, 0, 0, tzinfo=pytz.UTC
        ).astimezone(pytz.timezone("Europe/Ljubljana"))
        self.relation.category = "Category"
        self.relation.partitions = [
            {"id": 1, "entity": 123, "position": None, "label": "L1"}
        ]
        self.collection.relations.filter = self.web_request([self.relation])
        self.metadata_df = pd.DataFrame(
            [[0], [1], [4]], index=["0", "1", "2"], columns=["PFS"]
        )

        self.expressions_df = pd.DataFrame(
            [[0, 1, 2], [1, 2, 3], [2, 3, 4]],
            index=["0", "1", "2"],
            columns=["ENSG001", "ENSG002", "ENSG003"],
        )

        self.gene_map = {"ENSG001": "GA", "ENSG002": "GB", "ENSG003": "GC"}

    @staticmethod
    def web_request(return_value):
        def slow(*args, **kwargs):
            sleep(0.1)
            return return_value

        return slow

    @patch(
        "resdk.collection_tables.cache_dir_resdk", MagicMock(return_value="/tmp/resdk/")
    )
    @patch("os.path.exists")
    def test_init(self, exists_mock):
        ct = CollectionTables(self.collection)

        self.assertIs(ct.collection, self.collection)
        self.assertEqual(ct.cache_dir, "/tmp/resdk/")
        exists_mock.assert_called_with("/tmp/resdk/")

        # using different cache dir
        ct = CollectionTables(self.collection, cache_dir="/tmp/cache_dir/")
        self.assertEqual(ct.cache_dir, "/tmp/cache_dir/")
        exists_mock.assert_called_with("/tmp/cache_dir/")

    def test_heterogeneous_collections(self):
        """Test detecton of heterogeneous collections.

        Check is done in __init__, so it is sufficient to initialize
        CollectionTables with an appropriate collection.
        """
        # Different processes
        data2 = MagicMock()
        data2.id = 12345
        data2.process.slug = "process-slug2"
        data2.output.__getitem__.side_effect = {"source": "ENSEMBL"}.__getitem__
        self.collection.data.filter = self.web_request([self.data, data2])

        with self.assertRaisesRegex(ValueError, r"Expressions of all samples.*"):
            CollectionTables(self.collection)

        # Different source
        data2 = MagicMock()
        data2.id = 12345
        data2.process.slug = "process-slug"
        data2.output.__getitem__.side_effect = {"source": "GENCODE"}.__getitem__
        self.collection.data.filter = self.web_request([self.data, data2])

        with self.assertRaisesRegex(ValueError, r"Alignment of all samples.*"):
            CollectionTables(self.collection)

    @patch.object(CollectionTables, "_load_fetch")
    def test_meta(self, load_mock):
        load_mock.side_effect = self.web_request(self.metadata_df)

        ct = CollectionTables(self.collection)
        t = time()
        meta = ct.meta
        self.assertTrue(time() - t > 0.1)
        self.assertIs(meta, self.metadata_df)
        load_mock.assert_called_with(META)

        # use cache
        t = time()
        meta = ct.meta
        self.assertTrue(time() - t < 0.1)
        self.assertIs(meta, self.metadata_df)

    @patch.object(CollectionTables, "_load_fetch")
    def test_exp(self, load_mock):
        load_mock.side_effect = self.web_request(self.expressions_df)

        ct = CollectionTables(self.collection)
        t = time()
        exp = ct.exp
        self.assertTrue(time() - t > 0.1)
        self.assertIs(exp, self.expressions_df)
        load_mock.assert_called_with(EXP)
        self.assertListEqual(ct.gene_ids, ["ENSG001", "ENSG002", "ENSG003"])

        # use cache
        t = time()
        exp = ct.exp
        self.assertTrue(time() - t < 0.1)
        self.assertIs(exp, self.expressions_df)

    @patch.object(CollectionTables, "_load_fetch")
    def test_rc(self, load_mock):
        load_mock.side_effect = self.web_request(self.expressions_df)

        ct = CollectionTables(self.collection)
        t = time()
        rc = ct.rc
        self.assertTrue(time() - t > 0.1)
        self.assertIs(rc, self.expressions_df)
        load_mock.assert_called_with(RC)
        self.assertListEqual(ct.gene_ids, ["ENSG001", "ENSG002", "ENSG003"])

        # use cache
        t = time()
        rc = ct.rc
        self.assertTrue(time() - t < 0.1)
        self.assertIs(rc, self.expressions_df)

    @patch.object(CollectionTables, "_mapping")
    def test_id_to_symbol(self, mapping_mock):
        mapping_mock.side_effect = self.web_request(self.gene_map)

        ct = CollectionTables(self.collection)
        with self.assertRaises(ValueError):
            mapping = ct.id_to_symbol

        ct = CollectionTables(self.collection)
        ct.gene_ids = ["ENSG001", "ENSG002", "ENSG003"]
        t = time()
        mapping = ct.id_to_symbol
        self.assertTrue(time() - t > 0.1)
        mapping_mock.assert_called_with(
            ["ENSG001", "ENSG002", "ENSG003"], "ENSEMBL", "Homo sapiens"
        )
        self.assertIs(mapping, self.gene_map)

        # test if use case works
        new_exp = self.expressions_df.rename(columns=ct.id_to_symbol)
        self.assertListEqual(new_exp.columns.tolist(), ["GA", "GB", "GC"])

        # use cache
        t = time()
        mapping = ct.id_to_symbol
        self.assertTrue(time() - t < 0.1)
        self.assertIs(mapping, self.gene_map)

    @patch("resdk.collection_tables.clear_cache_dir_resdk")
    def test_clear_cache(self, clear_mock):
        CollectionTables.clear_cache()
        clear_mock.assert_called()

    def test_metadata_version(self):
        self.collection.samples.get = self.web_request(self.sample)
        self.collection.relations.get = self.web_request(self.relation)
        self.collection.data.get = self.web_request(self.orange_data)

        ct = CollectionTables(self.collection)
        version = ct._metadata_version
        self.assertEqual(version, "2020-11-01T12:15:00Z")

        # use cache
        t = time()
        version = ct._metadata_version
        self.assertTrue(time() - t < 0.1)

        self.collection.samples.get = MagicMock(side_effect=LookupError())
        ct1 = CollectionTables(self.collection)
        with self.assertRaises(ValueError):
            version = ct1._metadata_version

    def test_expressions_version(self):
        ct = CollectionTables(self.collection)
        version = ct._expression_version
        self.assertEqual(version, str(hash(tuple([12345]))))

        # use cache
        t = time()
        version = ct._expression_version
        self.assertTrue(time() - t < 0.1)

        self.collection.data.filter = MagicMock(return_value=[])
        ct = CollectionTables(self.collection)
        with self.assertRaises(ValueError):
            version = ct._expression_version

    @patch(
        "resdk.collection_tables.cache_dir_resdk", MagicMock(return_value="/tmp/resdk/")
    )
    @patch("resdk.collection_tables.load_pickle")
    @patch("resdk.collection_tables.save_pickle")
    @patch.object(CollectionTables, "_download_metadata")
    @patch.object(CollectionTables, "_download_expressions")
    def test_load_fetch(self, exp_mock, meta_mock, save_mock, load_mock):
        exp_mock.return_value = self.expressions_df
        meta_mock.return_value = self.metadata_df
        load_mock.return_value = None

        self.collection.samples.get = self.web_request(self.sample)
        self.collection.relations.get = self.web_request(self.relation)
        self.collection.data.get = self.web_request(self.orange_data)
        ct = CollectionTables(self.collection)
        data = ct._load_fetch(META)
        self.assertIs(data, self.metadata_df)
        save_mock.assert_called_with(
            self.metadata_df,
            "/tmp/resdk/slug_meta_None_None_2020-11-01T12:15:00Z.pickle",
        )

        save_mock.reset_mock()
        data = ct._load_fetch(EXP)
        self.assertIs(data, self.expressions_df)
        exp_mock.assert_called_with(EXP)
        save_mock.assert_called_with(
            self.expressions_df,
            f"/tmp/resdk/slug_exp_None_None_{str(hash((12345,)))}.pickle",
        )

        exp_mock.reset_mock()
        save_mock.reset_mock()
        data = ct._load_fetch(RC)
        self.assertIs(data, self.expressions_df)
        exp_mock.assert_called_with(RC)
        save_mock.assert_called_with(
            self.expressions_df,
            f"/tmp/resdk/slug_rc_None_None_{str(hash((12345,)))}.pickle",
        )

        exp_mock.reset_mock()
        load_mock.return_value = self.expressions_df
        data = ct._load_fetch(EXP)
        self.assertIs(data, self.expressions_df)
        exp_mock.assert_not_called()

    def test_get_descriptors(self):
        ct = CollectionTables(self.collection)
        descriptors = ct._get_descriptors()

        expected = pd.DataFrame([1], columns=["PFS"], index=["Sample123"], dtype=float)
        expected.index.name = "sample_name"

        assert_frame_equal(descriptors, expected)

    def test_get_relations(self):
        ct = CollectionTables(self.collection)
        relations = ct._get_relations()

        expected = pd.DataFrame(["L1"], columns=["Category"], index=["Sample123"])
        expected.index.name = "sample_name"

        assert_frame_equal(relations, expected)

    def test_get_orange_object(self):
        # Orange Data is found ad-hoc
        self.collection.data.get = self.web_request(self.orange_data)
        ct = CollectionTables(self.collection)
        obj = ct._get_orange_object()
        self.assertEqual(obj, self.orange_data)

    def test_get_orange_data(self):
        response = MagicMock()
        response.content = b"mS#Sample ID\tCol1\n123\t42"
        self.collection.resolwe.session.get.return_value = response
        self.collection.data.get = self.web_request(self.orange_data)

        ct = CollectionTables(self.collection)
        orange_data = ct._get_orange_data()

        expected = pd.DataFrame([42], columns=["Col1"], index=["Sample123"])
        expected.index.name = "sample_name"

        assert_frame_equal(orange_data, expected)

    @patch.object(CollectionTables, "_get_descriptors")
    @patch.object(CollectionTables, "_get_relations")
    @patch.object(CollectionTables, "_get_orange_data")
    def test_download_metadata(self, descriptors_mock, relations_mock, orange_mock):
        descriptors_mock.return_value = self.metadata_df
        relations_mock.return_value = pd.DataFrame(
            [["A"], ["B"], ["C"]], index=["0", "1", "2"], columns=["Replicate"]
        )
        orange_mock.return_value = pd.DataFrame(
            [["X"], ["Y"], ["Z"]], index=["0", "1", "2"], columns=["Clinical"]
        )

        ct = CollectionTables(self.collection)
        meta = ct._download_metadata()

        expected_content = [["X", "A", 0], ["Y", "B", 1], ["Z", "C", 4]]
        expected_columns = ["Clinical", "Replicate", "PFS"]
        expected_meta = pd.DataFrame(
            expected_content, columns=expected_columns, index=["0", "1", "2"]
        )
        expected_meta.index.name = "sample_name"

        assert_frame_equal(meta, expected_meta)

    def test_get_exp_uri(self):
        self.data.files.return_value = ["exp_file.csv"]

        ct = CollectionTables(self.collection)
        file_url = ct._get_exp_uri(self.data, EXP)
        self.assertEqual(file_url, "12345/exp_file.csv")

        self.data.files.return_value = []
        with self.assertRaises(LookupError):
            file_url = ct._get_exp_uri(self.data, EXP)

        self.data.files.return_value = ["exp_file1.csv", "exp_file2.csv"]
        with self.assertRaises(LookupError):
            file_url = ct._get_exp_uri(self.data, EXP)

    @patch(
        "resdk.collection_tables.cache_dir_resdk", MagicMock(return_value="/tmp/resdk/")
    )
    @patch("resdk.collection_tables.load_pickle")
    @patch("resdk.collection_tables.save_pickle")
    @patch.object(CollectionTables, "_download_mapping")
    def test_mapping(self, download_mock, save_mock, load_mock):
        load_mock.return_value = None
        download_mock.return_value = self.gene_map

        ct = CollectionTables(self.collection)
        mapping = ct._mapping(
            ["ENSG001", "ENSG002", "ENSG003"], "ENSEMBL", "Homo sapiens"
        )
        self.assertDictEqual(mapping, self.gene_map)
        self.assertListEqual(
            sorted(download_mock.call_args[0][0]), ["ENSG001", "ENSG002", "ENSG003"]
        )
        save_mock.assert_called_with(
            self.gene_map, "/tmp/resdk/ENSEMBL_Homo sapiens.pickle", override=True
        )

        # download only missing values
        download_mock.reset_mock()
        load_mock.return_value = {"ENSG002": "GB", "ENSG003": "GC"}
        mapping = ct._mapping(
            ["ENSG001", "ENSG002", "ENSG003"], "ENSEMBL", "Homo sapiens"
        )
        self.assertDictEqual(mapping, self.gene_map)
        self.assertListEqual(sorted(download_mock.call_args[0][0]), ["ENSG001"])

    def test_download_mapping(self):
        def create_feature(fid, name):
            m = MagicMock(feature_id=fid)
            # name can't be set on initialization
            m.name = name
            return m

        self.resolwe.feature.filter.return_value = [
            create_feature(fid, name) for fid, name in self.gene_map.items()
        ]

        ct = CollectionTables(self.collection)
        mapping = ct._download_mapping(
            ["ENSG001", "ENSG002", "ENSG003"], "ENSEMBL", "Homo sapiens"
        )

        self.resolwe.feature.filter.assert_called_once()
        self.resolwe.feature.filter.assert_called_once_with(
            source="ENSEMBL",
            species="Homo sapiens",
            feature_id__in=["ENSG001", "ENSG002", "ENSG003"],
        )
        self.assertDictEqual(mapping, self.gene_map)
