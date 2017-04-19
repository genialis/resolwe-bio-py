# pylint: disable=missing-docstring
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.tests.functional.base import BaseResdkFunctionalTest


class TestChipSeq(BaseResdkFunctionalTest):

    def test_macs(self):
        collection = self.res.collection.create(name='Test collection')
        collection_2 = self.res.collection.create(name='Another collection')

        # pylint: disable=unbalanced-tuple-unpacking
        background, bam_1, bam_2 = self.get_bams(3, collection)
        # pylint: enable=unbalanced-tuple-unpacking

        collection.create_background_relation(bam_1.sample, background.sample)
        collection.create_background_relation(bam_2.sample, background.sample)
        group = collection.create_group_relation(samples=[bam_1.sample, background.sample])

        # Just to create some confusion :)
        collection_2.add_samples(background.sample, bam_2.sample)
        collection_2.create_background_relation(bam_2.sample, background.sample)

        # Run on collection should only use samples with defined backgrounds
        macs = collection.run_macs()
        self.assertEqual(len(macs), 2)
        self.assertEqual(macs[0].input['treatment'], bam_1.id)
        self.assertEqual(macs[0].input['control'], background.id)
        self.assertEqual(macs[1].input['treatment'], bam_2.id)
        self.assertEqual(macs[1].input['control'], background.id)

        # Second run with same parameters should return same objects
        macs_2 = collection.run_macs()
        self.assertEqual(macs[0].id, macs_2[0].id)
        self.assertEqual(macs[1].id, macs_2[1].id)

        # Run with no background should use all samples
        macs = collection.run_macs(use_background=False)
        self.assertEqual(len(macs), 3)
        self.assertEqual(macs[0].input['treatment'], background.id)
        self.assertFalse('control' in macs[0].input)
        self.assertEqual(macs[1].input['treatment'], bam_1.id)
        self.assertFalse('control' in macs[1].input)
        self.assertEqual(macs[2].input['treatment'], bam_2.id)
        self.assertFalse('control' in macs[2].input)

        # Run on group should use only collections with defined backgrounds
        macs = group.run_macs()
        self.assertEqual(len(macs), 1)
        self.assertEqual(macs[0].input['treatment'], bam_1.id)
        self.assertEqual(macs[0].input['control'], background.id)

        # Run with no background should use all samples
        macs = group.run_macs(use_background=False)
        self.assertEqual(len(macs), 2)
        self.assertEqual(macs[0].input['treatment'], bam_1.id)
        self.assertFalse('control' in macs[0].input)
        self.assertEqual(macs[1].input['treatment'], background.id)
        self.assertFalse('control' in macs[1].input)

        # Normal run on single sample
        macs = bam_1.sample.run_macs()
        self.assertEqual(len(macs), 1)
        self.assertEqual(macs[0].input['treatment'], bam_1.id)
        self.assertEqual(macs[0].input['control'], background.id)

        # Normal run on single sample with no background
        macs = bam_1.sample.run_macs(use_background=False)
        self.assertEqual(len(macs), 1)
        self.assertEqual(macs[0].input['treatment'], bam_1.id)
        self.assertFalse('control' in macs[0].input)

        # This should crash because sample has 2 backgrounds defined
        with self.assertRaises(LookupError):
            bam_2.sample.run_macs()

        # But it is ok to run it without background
        macs = bam_2.sample.run_macs(use_background=False)
        self.assertEqual(len(macs), 1)
        self.assertEqual(macs[0].input['treatment'], bam_2.id)
        self.assertFalse('control' in macs[0].input)

        # This should crash because sample has no background
        with self.assertRaises(LookupError):
            background.sample.run_macs()

        # But it is ok to run it without background
        macs = background.sample.run_macs(use_background=False)
        self.assertEqual(len(macs), 1)
        self.assertEqual(macs[0].input['treatment'], background.id)
        self.assertFalse('control' in macs[0].input)

    def test_rose(self):
        collection = self.res.collection.create(name='Test collection')
        collection_2 = self.res.collection.create(name='Another collection')

        # pylint: disable=unbalanced-tuple-unpacking
        macs_1, macs_2 = self.get_macs(2, collection)
        background = self.get_bams(1, collection)[0]
        # pylint: enable=unbalanced-tuple-unpacking

        collection.create_background_relation(macs_1.sample, background.sample)
        collection.create_background_relation(macs_2.sample, background.sample)
        group = collection.create_group_relation(samples=[macs_1.sample, background.sample])

        # Just to create some confusion :)
        collection_2.add_samples(background.sample, macs_2.sample)
        collection_2.create_background_relation(macs_2.sample, background.sample)

        # Run on collection should only use samples with defined backgrounds
        rose = collection.run_rose2()
        self.assertEqual(len(rose), 2)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertEqual(rose[0].input['control'], background.id)
        self.assertEqual(rose[1].input['input'], macs_2.id)
        self.assertEqual(rose[1].input['control'], background.id)

        # Second run with same parameters should return same objects
        rose_2 = collection.run_rose2()
        self.assertEqual(rose[0].id, rose_2[0].id)
        self.assertEqual(rose[1].id, rose_2[1].id)

        # Run on group should use only collections with defined backgrounds
        rose = group.run_rose2()
        self.assertEqual(len(rose), 1)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertEqual(rose[0].input['control'], background.id)

        # Normal run on single sample
        rose = macs_1.sample.run_rose2()
        self.assertEqual(len(rose), 1)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertEqual(rose[0].input['control'], background.id)

        # Normal run on single sample with no background
        rose = macs_1.sample.run_rose2(use_background=False)
        self.assertEqual(len(rose), 1)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertFalse('control' in rose[0].input)

        # Add another sample with no background
        macs_3 = self.get_macs(1, collection)[0]
        group.add_sample(macs_3.sample)

        # Run with no background should use all samples
        # Background is skipped, because there is no macs object
        rose = group.run_rose2(use_background=False)
        self.assertEqual(len(rose), 2)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertFalse('control' in rose[0].input)
        self.assertEqual(rose[1].input['input'], macs_3.id)
        self.assertFalse('control' in rose[1].input)

        # Run with no background should use all samples
        # Background is skipped, because there is no macs object
        rose = collection.run_rose2(use_background=False)
        self.assertEqual(len(rose), 3)
        self.assertEqual(rose[0].input['input'], macs_1.id)
        self.assertFalse('control' in rose[0].input)
        self.assertEqual(rose[1].input['input'], macs_2.id)
        self.assertFalse('control' in rose[1].input)
        self.assertEqual(rose[2].input['input'], macs_3.id)
        self.assertFalse('control' in rose[2].input)

        # This should crash because sample has 2 backgrounds defined
        with self.assertRaises(LookupError):
            macs_2.sample.run_rose2()

        # But it is ok to run it without background
        rose = macs_2.sample.run_rose2(use_background=False)
        self.assertEqual(len(rose), 1)
        self.assertEqual(rose[0].input['input'], macs_2.id)
        self.assertFalse('control' in rose[0].input)

        # This should crash because sample has no background
        with self.assertRaises(LookupError):
            macs_3.sample.run_rose2()

        # But it is ok to run it without background
        rose = macs_3.sample.run_rose2(use_background=False)
        self.assertEqual(len(rose), 1)
        self.assertEqual(rose[0].input['input'], macs_3.id)
        self.assertFalse('control' in rose[0].input)
