# pylint: disable=missing-docstring
# pylint: disable=unbalanced-tuple-unpacking
import os

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
        samplesheet_name = 'annotation_spreadsheet.xlsm'
        return os.path.join(files_path, samplesheet_name)

    def test_annotate(self):
        # Create the collection with named, unannotated samples
        collection = self.res.collection.create(name='Test annotate collection')

        reads_1, reads_2, reads_2b, reads_4, reads_5 = self.get_reads(5, collection)
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
        with self.assertLogs() as logs:
            collection.annotate(samplesheet)

        # Check the error logging
        self.assertEqual(len(logs.output), 14)

        # Invalid annotations are individually logged and described
        samplesheet_errprefix = "ERROR:resdk.data_upload.samplesheet:"
        samplesheet_errors = [
            "For the sample, '', '' is not a valid SAMPLE_NAME.",
            "For the sample, 'missing annotator', '' is not a valid ANNOTATOR.",
            "For the sample, 'missing organism', '' is not a valid ORGANISM.",
            "For the sample, 'missing source', '' is not a valid SOURCE.",
            "For the sample, 'missing molecule', '' is not a valid MOLECULE.",
            "For the sample, 'missing seq_type', '' is not a valid SEQ_TYPE.",
            "The sample name 'duplicated sample' is duplicated. Please use "
            "unique sample names.",
        ]

        for error in samplesheet_errors:
            message = samplesheet_errprefix + error
            self.assertIn(message, logs.output)

        # All samples with invalid annotations are listed
        invalid_samples = [
            ' ,',
            'missing annotator',
            'missing organism',
            'missing source',
            'missing molecule',
            'missing seq_type',
            'duplicated sample',
        ]
        for invalid in invalid_samples:
            self.assertIn(invalid, logs.output[7])

        # Samples not explictly added should be missing (just check a few)
        missing_samples = [
            'single-reads',
            'paired-reads',
            'bad single path',
            'bad paired path',
            ' ,',
            'missing annotator',
            'missing molecule',
            'missing seq_type',
            'duplicated sample',
        ]
        for missing in missing_samples:
            self.assertIn(missing, logs.output[8])

        # But don't claim they're missing when they're not
        present_samples = ['Sample 1', 'Sample 2', 'Sample 3',
                           'missing organism', 'missing source']
        for present in present_samples:
            self.assertNotIn(present, logs.output[8])

        # Duplicate samples raise an error
        duplicate_error = ("ERROR:resdk.data_upload.annotate_samples:"
                           "Multiple samples are queried by the name 'Sample 2'"
                           ". Annotation will not be applied.")
        self.assertIn(duplicate_error, logs.output)

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
                    'TISSUE:Tumor',
                ],
                'strain': '',
                'source': 'Tumor',
                'organism': 'Rattus norvegicus',
                'molecule': 'total RNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }

        ann_2 = {}
        # # Restore if duplicate samples may be annotated.
        # ann_2 = {
        #     'sample': {
        #         'genotype': '',
        #         'cell_type': 'Mixed',
        #         'optional_char': [
        #             'LIBRARY_STRATEGY:Illumina Standard Prep ',
        #             'OTHER_CHAR_1:2x75 bp',
        #             'OTHER_CHAR_2:subdural cortical tumor, frontal/lateral'
        #             ' location. Easily isolated sample',
        #             'TISSUE:Tumor',
        #         ],
        #         'strain': '',
        #         'source': 'Tumor',
        #         'organism': 'Homo sapiens',
        #         'molecule': 'total RNA',
        #         'annotator': 'Tristan Brown',
        #         'description': '',
        #     }
        # }

        ann_3 = {
            'sample': {
                'genotype': 'AX4',
                'cell_type': '',
                'optional_char': [
                    'LIBRARY_STRATEGY:Illumina Standard Prep ',
                    'OTHER_CHAR_1:300 bp',
                ],
                'strain': 'Non-aggregating',
                'source': 'Cell',
                'organism': 'Dictyostelium discoideum',
                'molecule': 'genomic DNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }

        reads_ann_1 = {
            'experiment_type': 'RNA-Seq',
            'protocols': {'antibody_information': {'manufacturer': ''},
                          'extract_protocol': 'Standard',
                          'fragmentation_method': '',
                          'growth_protocol': 'Standard media',
                          'library_prep': 'Illumina',
                          'treatment_protocol': 'Control'},
            'reads_info': {'barcode': '', 'facility': '', 'instrument_type': ''},
        }

        # Check the actual annotation data
        sample_1.update()
        sample_2.update()
        sample_2b.update()
        sample_3.update()

        self.assertEqual(sample_1.descriptor, ann_1)
        self.assertEqual(sample_1.data[0].descriptor, reads_ann_1)
        self.assertEqual(sample_1.tags, ['community:rna-seq'])
        self.assertEqual(sample_2.descriptor, ann_2)
        self.assertEqual(sample_2b.descriptor, ann_2)
        self.assertEqual(sample_3.descriptor, ann_3)
        self.assertEqual(sample_4.descriptor, {})
        self.assertEqual(sample_5.descriptor, {})

    def test_export(self):
        # Create the collection with named, unannotated samples
        collection = self.res.collection.create(name='Test export annotation')

        reads_1, reads_2 = self.get_reads(2, collection)

        # Two different samples
        sample_1 = reads_1.sample
        sample_1.name = 'Sample 1'
        sample_1.save()

        sample_2 = reads_2.sample
        sample_2.name = 'Sample 2'
        ann_2 = {
            'sample': {
                'genotype': '',
                'cell_type': 'Mixed',
                'optional_char': [
                    'LIBRARY_STRATEGY:Illumina Standard Prep ',
                    'OTHER_CHAR_1:2x75 bp',
                    'OTHER_CHAR_2:subdural cortical tumor, frontal/lateral'
                    ' location. Easily isolated sample',
                    'TISSUE:Tumor',
                ],
                'strain': 'N/A',
                'source': 'Tumor',
                'organism': 'Homo sapiens',
                'molecule': 'total RNA',
                'annotator': 'Tristan Brown',
                'description': '',
            }
        }
        sample_2.descriptor_schema = 'sample'
        sample_2.descriptor = ann_2
        sample_2.save()

        reads_ann = {
            'experiment_type': 'RNA-Seq',
            'protocols': {
                'growth_protocol': 'N/A',
                'treatment_protocol': 'Control',
            }
        }
        reads_2.descriptor_schema = 'reads'
        reads_2.descriptor = reads_ann
        reads_2.save()

        # Export the new template
        filepath = 'annotation_template1.xlsm'
        try:
            os.remove(filepath)
        except OSError:
            pass

        with self.assertLogs() as logs:
            collection.export_annotation(filepath)
        assert os.path.exists(filepath)
        # TODO: Find a robust hash check for .xls* files
        os.remove(filepath)

        # Check the error logging
        self.assertEqual(len(logs.output), 3)
        not_annotated = ("WARNING:resdk.data_upload.samplesheet:Sample 'Sample 1'"
                         " reads not annotated.")
        self.assertIn(not_annotated, logs.output)
        location = ("INFO:resdk.data_upload.annotate_samples:\nSample annotation"
                    " template exported to annotation_template1.xlsm.\n")
        self.assertIn(location, logs.output)

    def test_upload_reads(self):
        # Create a collection, find the samplesheet, and upload the reads
        collection = self.res.collection.create(name='Test upload reads')
        samplesheet = self.get_samplesheet()
        with self.assertLogs() as logs:
            collection.upload_reads(samplesheet, basedir='files')

        # Check the error logging
        self.assertEqual(len(logs.output), 37)
        upload_errprefix = "ERROR:resdk.data_upload.reads:"

        # Examples of each upload error case:
        upload_errs = [
            "Skipping upload of 'Sample 1': No forward reads given.",
            "File /storage/61_cat_R1_001.fastq.gz not found.",
            "File /storage/63_cat_R1_001.fastq.gz not found.",
            "Skipping upload of '01_1-1_IP_plus': Invalid file extension(s). "
            "(Options: .fq, .fastq)",
            "Skipping upload of 'missing barcode': Invalid file extension(s). "
            "(Options: .fq, .fastq)",
            "Skipping upload of 'bad extension': Invalid file extension(s). "
            "(Options: .fq, .fastq)",
        ]
        for error in upload_errs:
            message = upload_errprefix + error
            self.assertIn(message, logs.output)

        # All samples that can't be uploaded are listed
        upload_fail = [
            'Sample 1',
            'Sample 2',
            'Sample 3',
            'bad single path',
            'bad paired path',
            ' ,',
            'missing annotator',
            'missing organism',
            'missing source',
            'missing molecule',
            'missing seq_type',
            '01_1-1_IP_plus',
            '02_1-1_IP_minus',
            'missing barcode',
            'other barcode',
            '01_1-1_IP_plus2',
            '02_1-1_IP_minus2',
            'duplicated sample',
            'invalid qseq',
            'invalid qseq2',
            'bad extension',
        ]
        for invalid in upload_fail:
            self.assertIn(invalid, logs.output[31])

        # Samples not uploaded should be missing
        for missing in upload_fail:
            self.assertIn(missing, logs.output[32])

        # Don't claim it's invalid or missing if it was uploaded
        upload_success = ['single-reads', 'paired-reads']
        for uploaded in upload_success:
            self.assertNotIn(uploaded, logs.output[31])
            self.assertNotIn(uploaded, logs.output[32])

        # Check the data objects
        names = [sample.name for sample in collection.samples]
        self.assertIn('single-reads', names)
        self.assertIn('paired-reads', names)

        # Try to duplicate the upload and fail
        with self.assertLogs() as logs2:
            collection.upload_reads(samplesheet, basedir='files')
        already_up = [
            "Skipping upload of 'single-reads': File already uploaded.",
            "Skipping upload of 'paired-reads': File already uploaded.",
        ]
        for error in already_up:
            message = upload_errprefix + error
            self.assertIn(message, logs2.output)
        self.assertEqual(len(collection.data), 2)
        self.assertEqual(len(collection.samples), 2)

        # TODO: Cannot test this part because processes do not complete on Jenkins
        # TODO: Check sample files and annotations in resolwe-bio when possible
        # sample1 = collection.samples.get(name='single-reads')
        # sample2 = collection.samples.get(name='paired-reads')
        # wait_process_complete(sample1.data[0], 1, 10)
        # wait_process_complete(sample2.data[0], 1, 10)
        # file0 = 'reads.fastq.gz'
        # file1 = 'reads_paired_abyss_1.fastq.gz'
        # file2 = 'reads_paired_abyss_2.fastq.gz'
        # self.assertIn(file0, sample1.files())
        # self.assertIn(file1, sample2.files())
        # self.assertIn(file2, sample2.files())
        # self.assertEqual(sample1.descriptor['sample']['organism'], 'Mus musculus')
        # self.assertEqual(sample2.descriptor['sample']['organism'], 'Rattus norvegicus')

        # Test export of the annotated template
        filepath = 'annotation_template2.xlsm'
        try:
            os.remove(filepath)
        except OSError:
            pass

        collection.export_annotation(filepath)
        assert os.path.exists(filepath)
        # TODO: Find a robust hash check for .xls* files
        os.remove(filepath)

    def test_upload_multiplexed(self):
        # Create a collection, find the samplesheet, and upload the reads
        collection = self.res.collection.create(name='Test upload multiplexed')
        samplesheet = self.get_samplesheet()
        with self.assertLogs() as logs:
            collection.upload_demulti(samplesheet, basedir='files')

        # Check the error logging
        self.assertEqual(len(logs.output), 39)
        upload_errprefix = "ERROR:resdk.data_upload.multiplexed:"

        # Examples of each upload error case:
        upload_errs = [
            "Skipping upload of 'reads.fastq.gz': No barcodes file given.",
            "Skipping upload of 'reads_paired_abyss_1.fastq.gz': "
            "No barcodes file given.",
            "Skipping upload of '': No forward reads given.",
            "Skipping upload of 'dummy.qseq': Missing barcode.",
            "Skipping upload of 'pool24.read1.small.fastq.bz2': Invalid file "
            "extension(s). (Options: .qseq)",
            "Skipping upload of 'pool24c.read1.small.qseq.bz2': Invalid file "
            "extension(s). (Options: .qseq)",
            "Demultiplex process not yet complete for 'pool24.read1.small.qseq.bz2'.",
        ]
        for error in upload_errs:
            message = upload_errprefix + error
            self.assertIn(message, logs.output)

        # All samples that can't be uploaded are listed
        upload_fail = [
            'single-reads',
            'paired-reads',
            'Sample 1',
            'Sample 2',
            'Sample 3',
            'bad single path',
            'bad paired path',
            ' ,',
            'missing annotator',
            'missing organism',
            'missing source',
            'missing molecule',
            'missing seq_type',
            'missing barcode',
            'other barcode',
            '01_1-1_IP_plus2',
            '02_1-1_IP_minus2',
            'duplicated sample',
            'invalid qseq',
            'invalid qseq2',
            'bad extension',
        ]
        for invalid in upload_fail:
            self.assertIn(invalid, logs.output[35])

        # Samples not uploaded should be missing
        for missing in upload_fail:
            self.assertIn(missing, logs.output[36])

        # Don't claim it's invalid if it was uploaded
        upload_success = ['01_1-1_IP_plus,', '02_1-1_IP_minus,']
        for uploaded in upload_success:
            self.assertNotIn(uploaded, logs.output[35])

        # Check the file is actually uploaded
        names = [data.name for data in collection.data]
        qseq = 'pool24.read1.small.qseq.bz2'
        self.assertIn(qseq, names)

        # Try to duplicate the upload and fail
        with self.assertLogs() as logs2:
            collection.upload_demulti(samplesheet, basedir='files')
        already_up = (
            upload_errprefix
            + "Skipping upload of 'pool24.read1.small.qseq.bz2': File already uploaded."
        )
        self.assertIn(already_up, logs2.output)
        names = [data.name for data in collection.data]
        names.remove(qseq)
        self.assertNotIn(qseq, names)

        # TODO: Cannot test this part because processes do not complete on Jenkins
        # TODO: Check sample files and annotations in resolwe-bio when possible
        # for data in collection.data:
        #     wait_process_complete(data, 1, 10)  # process the .qseq upload
        # collection.update()
        # for data in collection.data:
        #     wait_process_complete(data, 1, 10)  # process the demultiplexed child data
        # collection.upload_demulti(samplesheet)
        # collection.update()

        # # Check the uploaded data and created samples
        # self.assertEqual(len(collection.data), 5)
        # self.assertEqual(len(collection.samples), 4)
        # names = {sample.name for sample in collection.samples}
        # self.assertIn('01_1-1_IP_plus', names)
        # self.assertIn('02_1-1_IP_minus', names)
        # sample1 = collection.samples.get(name='01_1-1_IP_plus')
        # sample2 = collection.samples.get(name='02_1-1_IP_minus')
        # file1 = 'pool24_01_1-1_IP_plus_TCGCAGG_mate1.fastq.gz'
        # file2 = 'pool24_02_1-1_IP_minus_CTCTGCA_mate2.fastq.gz'
        # self.assertIn(file1, sample1.files())
        # self.assertIn(file2, sample2.files())
        # self.assertEqual(sample1.descriptor['sample']['source'], 'Tumor')
        # self.assertEqual(sample2.descriptor['sample']['source'], 'Control')
