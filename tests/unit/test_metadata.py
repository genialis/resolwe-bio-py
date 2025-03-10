"""
Unit tests for Metadata class.
"""

import unittest

import pandas as pd
from mock import MagicMock, NonCallableMagicMock

from resdk.resources import Collection, Metadata, Process, Sample

from .utils import server_resource


class TestMetadata(unittest.TestCase):
    def setUp(self):
        self.res = MagicMock()

        # Process
        self.process = NonCallableMagicMock(spec=Process, slug="upload-metadata")
        self.process_unique = NonCallableMagicMock(
            spec=Process, slug="upload-metadata-unique"
        )

        # Samples
        self.sample1 = server_resource(
            Sample, resolwe=self.res, id=10, slug="s1", name="S1"
        )
        self.sample2 = server_resource(
            Sample, resolwe=self.res, id=11, slug="s2", name="S2"
        )

        # Collection
        self.collection = server_resource(Collection, resolwe=self.res, id=5)
        self.collection.samples.filter.return_value = [self.sample1, self.sample2]

        # df
        self.df = pd.DataFrame(
            {
                "Response": ["PD", "CR"],
            },
            index=pd.Series([self.sample1.id, self.sample2.id], name="Sample ID"),
        )

        # Data
        self.metadata1 = server_resource(
            Metadata, resolwe=self.res, id=100, process=self.process, df=self.df
        )
        self.metadata2 = server_resource(
            Metadata, resolwe=self.res, id=101, process=self.process_unique
        )
        self.res.metadata.filter = MagicMock(
            return_value=[self.metadata1, self.metadata2]
        )

    def test_init(self):
        meta = Metadata(self.res, df=self.df)

        self.assertEqual(meta.resolwe, self.res)
        pd.testing.assert_frame_equal(meta.df, self.df)

    def test_unique(self):
        # If created from scratch, unique should be True by default
        self.res.process.get.return_value = self.process_unique
        meta = Metadata(self.res)
        self.assertTrue(meta.unique)

        # And False if so specified
        self.res.process.get.return_value = self.process
        meta = Metadata(self.res, unique=False)
        self.assertFalse(meta.unique)

        # If get from server, unique should be proxy for process type.
        m1, m2 = self.res.metadata.filter()
        self.assertFalse(m1.unique)
        self.assertTrue(m2.unique)

    def test_set_index(self):
        # One cannot do: Metadata(resolwe=self.res, collection=self.collection)
        # since there is a deepcopy call in resdk.resources.BaseResource
        # that tries to copy resolwe Mock object.
        m = Metadata(resolwe=self.res)
        m._collection = MagicMock()
        m.collection.samples.filter = MagicMock(
            return_value=[self.sample1, self.sample2]
        )

        # If there is Sample ID column, set that as an index
        df = pd.DataFrame({"Response": ["PD", "CR"], "Sample ID": [10, 11]})
        df_out = m.set_index(df)
        # The created df still contains "Sample slug" column. For
        # comparison, remove it.
        pd.testing.assert_frame_equal(self.df, df_out)

        # If there is Sample slug column, map to sample ID and set that as index
        df = pd.DataFrame({"Response": ["PD", "CR"], "Sample slug": ["s1", "s2"]})
        df_out = m.set_index(df)
        pd.testing.assert_frame_equal(self.df, df_out.drop(columns=["Sample slug"]))

        # If there is Sample name column, map to sample ID and set that as index
        df = pd.DataFrame({"Response": ["PD", "CR"], "Sample name": ["S1", "S2"]})
        df_out = m.set_index(df)
        pd.testing.assert_frame_equal(self.df, df_out.drop(columns=["Sample name"]))

        # If Sample name is in index, map to sample ID and set that as index
        df = pd.DataFrame({"Response": ["PD", "CR"], "Sample name": ["S1", "S2"]})
        df = df.set_index("Sample name")
        df_out = m.set_index(df)
        pd.testing.assert_frame_equal(self.df, df_out.drop(columns=["Sample name"]))

    def test_validate(self):
        with self.assertRaisesRegex(
            ValueError, "Setting df attribute before setting collection is not allowed."
        ):
            m = Metadata(resolwe=self.res)
            m.df = self.df

        # One cannot do: Metadata(resolwe=self.res, collection=self.collection)
        # since there is a deepcopy call in resdk.resources.BaseResource
        # that tries to copy resolwe Mock object.
        m = Metadata(resolwe=self.res)
        m._collection = self.collection

        with self.assertRaisesRegex(
            ValueError, "Attribute df must be a pandas.DataFrame object."
        ):
            m.df = "not pd.DataFrame"

        with self.assertWarnsRegex(
            UserWarning,
            "No intersection between samples in df and samples in collection.",
        ):
            m.df = pd.DataFrame({"Sample ID": [2, 3]})

        with self.assertWarnsRegex(UserWarning, "There are 1 samples in collection"):
            m.df = pd.DataFrame(index=[self.sample1.id])

        with self.assertWarnsRegex(UserWarning, "There are 1 samples in df"):
            m.df = pd.DataFrame(index=[self.sample1.id, self.sample2.id, 42])

        # This should be fine
        m.df = self.df

    def test_df_local(self):
        # One cannot do: Metadata(resolwe=self.res, collection=self.collection)
        # since there is a deepcopy call in resdk.resources.BaseResource
        # that tries to copy resolwe Mock object.
        m = Metadata(resolwe=self.res)
        m._collection = self.collection

        m.df = self.df
        pd.testing.assert_frame_equal(m.df, self.df)

        df2 = pd.DataFrame(index=[self.sample1.id, self.sample2.id])
        m.df = df2
        pd.testing.assert_frame_equal(m.df, df2)

    def test_df_remote(self):
        with self.assertRaisesRegex(
            ValueError,
            "Setting df attribute on already uploaded Metadata is not allowed",
        ):
            self.metadata1.df = self.df

        pd.testing.assert_frame_equal(self.metadata1.df, self.df)

    def test_save(self):
        m = Metadata(resolwe=self.res)
        with self.assertRaisesRegex(
            ValueError, "Collection must be set before saving."
        ):
            m.save()

        m.collection = self.collection
        with self.assertRaisesRegex(
            ValueError, "Attribute df must be set before saving."
        ):
            m.save()

        m.df = self.df


if __name__ == "__main__":
    unittest.main()
