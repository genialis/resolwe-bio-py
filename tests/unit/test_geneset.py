"""
Unit tests for Geneset class.
"""

import unittest

from mock import MagicMock, patch

from resdk.resources.geneset import Geneset

from .utils import server_resource


class TestGeneset(unittest.TestCase):
    def test_arguments(self):
        gs = Geneset(
            MagicMock(), genes=["FHIT", "MYC"], source="UCSC", species="Homo sapiens"
        )

        # test all geneset attributes
        self.assertCountEqual(gs.genes, ["FHIT", "MYC"])
        self.assertEqual(len(gs._genes), 2)
        self.assertEqual(gs.source, "UCSC")
        self.assertEqual(gs.species, "Homo sapiens")

    def test_empty_set(self):
        # test creating empty geneset
        gs = Geneset(MagicMock(), genes=[])
        self.assertCountEqual(gs.genes, [])

    def test_setters(self):
        gs = Geneset(MagicMock())
        gs.genes = ["FHIT"]
        self.assertCountEqual(gs.genes, ["FHIT"])

        gs.species = "Test species"
        self.assertEqual(gs.species, "Test species")

        gs.source = "Test source"
        self.assertEqual(gs.source, "Test source")

        # saved geneset should not allow to change genes/species/source values
        gs_saved = server_resource(Geneset, MagicMock(), id=1)
        message = "Not allowed to change field source after geneset is saved"
        with self.assertRaisesRegex(ValueError, message):
            gs_saved.source = "Test source"

    def test_dont_override_genes(self):
        gs = Geneset(
            MagicMock(), genes=["FHIT", "MYC"], source="UCSC", species="Homo sapiens"
        )
        gs2 = Geneset(
            MagicMock(),
            genes=["BRCA2", "MYC", "ABC"],
            source="UCSC",
            species="Homo sapiens",
        )
        gs | gs2

        # the original genesets should not change when performing set operations on them
        self.assertCountEqual(gs.genes, ["FHIT", "MYC"])
        self.assertCountEqual(gs2.genes, ["BRCA2", "MYC", "ABC"])

    def test_set_operations(self):
        gs = Geneset(
            MagicMock(), genes=["FHIT", "MYC"], source="UCSC", species="Homo sapiens"
        )
        gs2 = Geneset(
            MagicMock(),
            genes=["BRCA2", "MYC", "ABC"],
            source="UCSC",
            species="Homo sapiens",
        )
        gs_union = gs | gs2
        gs_intersection = gs & gs2
        gs_difference = gs - gs2
        gs_rsub = gs.__rsub__(gs2)
        gs_symmetric_difference = gs ^ gs2

        # test set operations
        self.assertCountEqual(gs_union.genes, ["FHIT", "MYC", "BRCA2", "ABC"])
        self.assertCountEqual(gs_intersection.genes, ["MYC"])
        self.assertCountEqual(gs_difference.genes, ["FHIT"])
        self.assertCountEqual(gs_rsub.genes, ["BRCA2", "ABC"])
        self.assertCountEqual(gs_symmetric_difference.genes, ["FHIT", "BRCA2", "ABC"])

    def test_operations_errors(self):
        gs = Geneset(MagicMock(), genes=["FHIT"], source="UCSC", species="Homo sapiens")
        gs_source_err = Geneset(
            MagicMock(),
            genes=["BRCA2"],
            source="Wrong source",
            species="Homo sapiens",
        )
        message = "Cannot compare Genesets with different sources"
        with self.assertRaisesRegex(ValueError, message):
            gs | gs_source_err

        gs_species_err = Geneset(
            MagicMock(),
            genes=["BRCA2"],
            source="UCSC",
            species="Wrong species",
        )
        message = "Cannot compare Genesets with different species"
        with self.assertRaisesRegex(ValueError, message):
            gs | gs_species_err

        not_implemented = gs.__or__({"BRCA2"})
        self.assertEqual(not_implemented, NotImplemented)

    def test_fetch_data(self):
        gs = server_resource(
            Geneset,
            MagicMock(),
            output={"geneset_json": 1, "source": "UCSC", "species": "Homo sapiens"},
            id=1,
        )
        response = MagicMock()
        response.content = '{"json": {"genes": ["FHIT", "MYC"]}}'.encode("utf-8")
        gs.resolwe = MagicMock(**{"session.get.return_value": response, "url": ""})

        # test all geneset attributes
        self.assertCountEqual(gs.genes, ["FHIT", "MYC"])
        self.assertEqual(gs.source, "UCSC")
        self.assertEqual(gs.species, "Homo sapiens")

    @patch("resdk.resources.geneset.Geneset", spec=True)
    def test_update_fields(self, geneset_mock):
        geneset = server_resource(Geneset, MagicMock(), id=1, slug="test-old")
        geneset.slug = "test"
        update_mock = MagicMock()
        geneset._update_fields = update_mock
        geneset.save()
        self.assertEqual(update_mock.call_count, 1)

    @patch("resdk.resources.geneset.Geneset", spec=True)
    def test_create(self, geneset_mock):
        collection_mock = MagicMock(id=1)
        geneset_mock.configure_mock(
            id=None,
            name="Test name",
            collection=collection_mock,
            genes=["FHIT", "MYC"],
            source="UCSC",
            species="Homo sapiens",
        )
        geneset_mock.api = MagicMock(**{"post.return_value": {"id": 1, "slug": "test"}})
        Geneset.save(geneset_mock)

        geneset_mock.api.post.assert_called_once_with(
            {
                "process": {"slug": "create-geneset"},
                "input": {
                    "genes": ["FHIT", "MYC"],
                    "source": "UCSC",
                    "species": "Homo sapiens",
                },
                "name": "Test name",
                "collection": {"id": collection_mock},
            }
        )

    def test_create_errors(self):
        gs = Geneset(MagicMock(), genes=["FHIT"], source="UCSC")
        message = "Fields species must not be none"
        with self.assertRaisesRegex(ValueError, message):
            gs.save()


if __name__ == "__main__":
    unittest.main()
