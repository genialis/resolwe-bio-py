import pandas as pd

import resdk

from ..base import BaseResdkFunctionalTest


class TestMetadata(BaseResdkFunctionalTest):
    def setUp(self):
        super().setUp()
        self.collection = self.res.collection.create(
            name="Test collection",
            tags=["community:expressions"],
        )

    def tearDown(self):
        self.collection.delete(force=True)

    def test_create_metadata(self):
        """Create an instance of Metadata and confirm it can be fetched."""
        metadata = self.res.metadata.create(
            name="Test name",
            collection=self.collection,
            df=pd.DataFrame({"Column 2": [40, 50]}, index=[10, 20]),
        )

        self.assertTrue(isinstance(metadata, resdk.resources.Metadata))
        self.assertEqual(metadata.name, "Test name")
        self.assertEqual(metadata.collection, self.collection)

        # Update metadata with a new name
        metadata.name = "Other name"
        metadata.save()
        metadata = self.res.metadata.get(id=metadata.id)
        self.assertEqual(metadata.name, "Other name")
