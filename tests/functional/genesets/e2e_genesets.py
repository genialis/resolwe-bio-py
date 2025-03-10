import resdk

from ..base import BaseResdkFunctionalTest


class TestCreateGeneset(BaseResdkFunctionalTest):
    def setUp(self):
        super().setUp()
        self.collection = self.res.collection.create(name="Test collection")
        self.geneset = None

    def tearDown(self):
        # self.geneset is deleted along with collection
        self.collection.delete(force=True)

    def test_create_geneset(self):
        self.geneset = self.res.geneset.create(
            name="Test name",
            genes=["FHIT", "MYC"],
            source="UCSC",
            species="Homo sapiens",
            collection=self.collection,
        )

        self.assertTrue(isinstance(self.geneset, resdk.resources.Geneset))
        self.assertCountEqual(self.geneset.genes, ["FHIT", "MYC"])
        self.assertEqual(self.geneset.source, "UCSC")
        self.assertEqual(self.geneset.species, "Homo sapiens")
        self.assertEqual(self.geneset.name, "Test name")
        self.assertEqual(self.geneset.collection, self.collection)

        # Update geneset with a new tag
        self.geneset.tags = ["community:expressions"]
        self.geneset.save()

        self.assertEqual(self.geneset.tags, ["community:expressions"])
