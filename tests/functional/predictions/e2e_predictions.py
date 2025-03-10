import os

from resdk.resources.predictions import ClassPredictionType, ScorePredictionType

from ..base import BaseResdkFunctionalTest
from ..docs.e2e_docs import TEST_FILES_DIR


class TestPredictions(BaseResdkFunctionalTest):
    def setUp(self):
        super().setUp()
        self.collection = self.res.collection.create(name="Test collection")

        self.geneset = None

    def tearDown(self):
        # self.geneset is deleted along with collection
        self.collection.delete(force=True)

    def test_predictions(self):
        reads = self.res.run(
            slug="upload-fastq-single",
            input={"src": os.path.join(TEST_FILES_DIR, "reads.fastq.gz")},
            collection=self.collection,
        )
        sample = reads.sample
        self.assertEqual(sample.get_predictions(), {})

        sample.set_predictions({"general.score": ScorePredictionType(0.5)})
        self.assertEqual(
            sample.get_predictions(), {"general.score": ScorePredictionType(0.5)}
        )

        sample.set_predictions(
            {
                "general.score": ScorePredictionType(1.5),
                "general.class": ClassPredictionType("positive", 0.5),
            }
        )
        self.assertEqual(
            sample.get_predictions(),
            {
                "general.score": ScorePredictionType(1.5),
                "general.class": ClassPredictionType("positive", 0.5),
            },
        )

        sample.set_predictions({"general.class": None})
        self.assertEqual(
            sample.get_predictions(),
            {"general.score": ScorePredictionType(1.5)},
        )
