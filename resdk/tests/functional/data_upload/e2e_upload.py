# pylint: disable=missing-docstring
# pylint: disable=unbalanced-tuple-unpacking
import os

from resdk import resdk_logger
from resdk.tests.functional.base import BaseResdkFunctionalTest


class TestUpload(BaseResdkFunctionalTest):

    def get_samplesheet(self):
        """Return path of an annotation samplesheet."""
        files_path = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                '..',
                'files',
            )
        )

        samplesheet_path = os.path.join(
            files_path,
            'annotation_spreadsheet.xlsm',
        )
        return samplesheet_path

    def test_annotate(self):
        resdk_logger.start_logging()

        # Create the collection with named, unannotated samples
        collection = self.res.collection.create(name='Test annotate collection')

        reads_1, reads_2, reads_2b, reads_4, reads_5 = (self.get_reads(5, collection))
        bam = self.get_bams(1, collection)[0]

        # Two different samples
        sample_1 = reads_1.sample
        sample_1.name = 'Sample 1'
        sample_1.save()

        sample_2 = reads_2.sample
        sample_2.name = 'Sample 2'
        sample_2.save()

        # A duplicated sample
        sample_2b = reads_2b.sample
        sample_2b.name = 'Sample 2'
        sample_2b.save()

        # A sample derived from an alignment file
        sample_3 = bam.sample
        sample_3.name = 'Sample 3'
        sample_3.save()

        # Missing organism
        sample_4 = reads_4.sample
        sample_4.name = 'missing organism'
        sample_4.save()

        # Missing source
        sample_5 = reads_5.sample
        sample_5.name = 'missing source'
        sample_5.save()

        # Apply the sample annotations from a local spreadsheet
        samplesheet = self.get_samplesheet()
        collection.annotate(samplesheet)

        # Annotations from the example sheet for Samples 1, 2, and 3
        ann_1 = {
            'sample': {
                'genotype': 'ANIMAL 1:\xa0PBCAG-FUS1, PBCAG-eGFP, PBCAG-mCherry,'
                            ' GLAST-PBase,\xa0PX330-P53',
                'cell_type': 'Mixed',
                'optional_char': [
                    'AGE:38 days',
                    'LIBRARY_STRATEGY:Illumina Standard Prep ',
                    'OTHER_CHAR_1:2x75 bp',
                    'OTHER_CHAR_2:subdural cortical tumor, frontal/lateral'
                    ' location. Easily isolated sample',
                    'TISSUE:Tumor'
                ],
                'strain': '',
                'source': 'Tumor',
                'organism': 'Rattus norvegicus',
                'molecule': 'total RNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }

        ann_2 = {
            'sample': {
                'genotype': '',
                'cell_type':
                'Mixed',
                'optional_char': [
                    'LIBRARY_STRATEGY:Illumina Standard Prep ',
                    'OTHER_CHAR_1:2x75 bp',
                    'OTHER_CHAR_2:subdural cortical tumor, frontal/lateral'
                    ' location. Easily isolated sample',
                    'TISSUE:Tumor'
                ],
                'strain': '',
                'source': 'Tumor',
                'organism': 'Homo sapiens',
                'molecule': 'total RNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }

        ann_3 = {
            'sample': {
                'genotype': 'AX4',
                'cell_type': '',
                'optional_char': [
                    'LIBRARY_STRATEGY:Illumina Standard Prep ',
                    'OTHER_CHAR_1:300 bp'
                ],
                'strain': 'Non-aggregating',
                'source': 'Cell',
                'organism': 'Dictyostelium discoideum',
                'molecule': 'genomic DNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }

        # Check annotations
        sample_1.update()
        sample_2.update()
        sample_2b.update()
        sample_3.update()

        self.assertEqual(sample_1.descriptor, ann_1)
        self.assertEqual(sample_2.descriptor, ann_2)
        self.assertEqual(sample_2b.descriptor, ann_2)
        self.assertEqual(sample_3.descriptor, ann_3)
        self.assertEqual(sample_4.descriptor, {})
        self.assertEqual(sample_5.descriptor, {})

    def test_export(self):
        resdk_logger.start_logging()

        # Create the collection with named, unannotated samples
        collection = self.res.collection.create(name='Test export annotation')

        reads_1, reads_2 = self.get_reads(2, collection)

        # Two different samples
        sample_1 = reads_1.sample
        sample_1.name = 'Sample 1'
        sample_1.save()

        sample_2 = reads_2.sample
        sample_2.name = 'Sample 2'
        sample_2.save()

        # Export the new template
        filepath = 'template.xlsm'
        try:
            os.remove(filepath)
        except OSError:
            pass

        collection.export_annotation(path=filepath)
        assert os.path.exists(filepath)
        os.remove(filepath)
