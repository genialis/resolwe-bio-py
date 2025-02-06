""".. Ignore pydocstyle D400.

========
QCTables
========

.. autoclass:: QCTables
    :members:
    :inherited-members:

    .. automethod:: __init__

"""

from functools import lru_cache

import pandas as pd

from resdk.resources import Data

from .base import BaseTables

CHUNK_SIZE = 1000


MQC_GENERAL_COLUMNS = [
    {
        "name": "FastQC (raw)_mqc-generalstats-fastqc_raw-total_sequences",
        "slug": "total_read_count_raw",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "FastQC (trimmed)_mqc-generalstats-fastqc_trimmed-total_sequences",
        "slug": "total_read_count_trimmed",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "FastQC (raw)_mqc-generalstats-fastqc_raw-percent_gc",
        "slug": "gc_content_raw",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "FastQC (trimmed)_mqc-generalstats-fastqc_trimmed-percent_gc",
        "slug": "gc_content_trimmed",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "FastQC (raw)_mqc-generalstats-fastqc_raw-percent_duplicates",
        "slug": "seq_duplication_raw",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "FastQC (trimmed)_mqc-generalstats-fastqc_trimmed-percent_duplicates",
        "slug": "seq_duplication_trimmed",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "FastQC (raw)_mqc-generalstats-fastqc_raw-avg_sequence_length",
        "slug": "avg_seq_length_raw",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "FastQC (trimmed)_mqc-generalstats-fastqc_trimmed-avg_sequence_length",
        "slug": "avg_seq_length_trimmed",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "STAR_mqc-generalstats-star-uniquely_mapped_percent",
        "slug": "mapped_reads_percent",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "STAR_mqc-generalstats-star-uniquely_mapped",
        "slug": "mapped_reads",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "STAR (Globin)_mqc-generalstats-star_globin-uniquely_mapped_percent",
        "slug": "mapped_reads_percent_globin",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "STAR (Globin)_mqc-generalstats-star_globin-uniquely_mapped",
        "slug": "mapped_reads_globin",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "STAR (rRNA)_mqc-generalstats-star_rrna-uniquely_mapped_percent",
        "slug": "mapped_reads_percent_rRNA",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "STAR (rRNA)_mqc-generalstats-star_rrna-uniquely_mapped",
        "slug": "mapped_reads_rRNA",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "featureCounts_mqc-generalstats-featurecounts-percent_assigned",
        "slug": "fc_assigned_reads_percent",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "featureCounts_mqc-generalstats-featurecounts-Assigned",
        "slug": "fc_assigned_reads",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "STAR quantification_mqc-generalstats-star_quantification-of_assigned_reads",
        "slug": "star_assigned_reads_percent",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "STAR quantification_mqc-generalstats-star_quantification-Assigned_reads",
        "slug": "star_assigned_reads",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "Salmon_mqc-generalstats-salmon-percent_mapped",
        "slug": "salmon_assigned_reads_percent",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "Salmon_mqc-generalstats-salmon-num_mapped",
        "slug": "salmon_assigned_reads",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "QoRTs_mqc-generalstats-qorts-Genes_PercentWithNonzeroCounts",
        "slug": "nonzero_count_features_percent",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "QoRTs_mqc-generalstats-qorts-NumberOfChromosomesCovered",
        "slug": "contigs_covered",
        "type": "Int64",
        "agg_func": "mean",
    },
    {
        "slug": "strandedness_code",
        "type": "string",
    },
    {
        "slug": "genome_build",
        "type": "string",
    },
]

QORTS_COLUMNS = [
    {
        "name": "StrandTest_frFirstStrand",
        "slug": "first_strand",
        "type": "float64",
        "agg_func": "mean",
    },
    {
        "name": "StrandTest_frSecondStrand",
        "slug": "second_strand",
        "type": "float64",
        "agg_func": "mean",
    },
]

MACS_COLUMNS = [
    {
        "name": "peak_count",
        "slug": "macs_peak_count",
        "type": "Int64",
        "agg_func": "mean",
    },
    {
        "name": "fragment_size",
        "slug": "macs_fragment_size",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "treatment_fragments_total",
        "slug": "macs_treatment_fragments_total",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "control_fragments_total",
        "slug": "macs_control_fragments_total",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "d",
        "slug": "macs_fragment_length",
        "type": "Float64",
        "agg_func": "mean",
    },
]

PREPEAK_CHIPQC_COLUMNS = [
    {
        "name": "TOTAL_READS",
        "slug": "prepeak_total_reads",
        "type": "Int64",
        "agg_func": "mean",
    },
    {
        "name": "MAPPED_READS",
        "slug": "prepeak_mapped_reads",
        "type": "Int64",
        "agg_func": "mean",
    },
    {
        "name": "MAPPED_PERCENTAGE",
        "slug": "prepeak_mapped_percentage",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "UNPAIRED_READS_EXAMINED",
        "slug": "prepeak_unpaired_reads_examined",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "READ_PAIRS_EXAMINED",
        "slug": "prepeak_read_pairs_examined",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "UNPAIRED_READ_DUPLICATES",
        "slug": "prepeak_unpaired_read_duplicates",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "PERCENT_DUPLICATION",
        "slug": "prepeak_percent_duplication",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "NRF",
        "slug": "prepeak_nrf",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PBC1",
        "slug": "prepeak_pbc1",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PBC2",
        "slug": "prepeak_pbc2",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "NSC",
        "slug": "prepeak_nsc",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "RSC",
        "slug": "prepeak_rsc",
        "type": "Float64",
        "agg_func": "mean",
    },
]

POSTPEAK_CHIPQC_COLUMNS = [
    {
        "name": "FRiP",
        "slug": "postpeak_frip",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "NUMBER_OF_PEAKS",
        "slug": "postpeak_number_of_peaks",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "NUMBER_OF_READS_IN_PROMOTERS",
        "slug": "postpeak_number_of_reads_in_promoters",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "FRACTION_OF_READS_IN_PROMOTERS",
        "slug": "postpeak_fraction_of_reads_in_promoters",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "NUMBER_OF_PEAKS_IN_PROMOTERS",
        "slug": "postpeak_number_of_peaks_in_promoters",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "FRACTION_OF_PEAKS_IN_PROMOTERS",
        "slug": "postpeak_fraction_of_peaks_in_promoters",
        "type": "Float64",
        "agg_func": "mean",
    },
]

PICARD_WGS_COLUMNS = [
    {
        "name": "GENOME_TERRITORY",
        "slug": "picard_wgs_genome_territory",
        "type": "Float64",
        "agg_func": "sum",
    },
    {
        "name": "MEAN_COVERAGE",
        "slug": "picard_wgs_mean_coverage",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "SD_COVERAGE",
        "slug": "picard_wgs_sd_coverage",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "MEDIAN_COVERAGE",
        "slug": "picard_wgs_median_coverage",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "MAD_COVERAGE",
        "slug": "picard_wgs_mad_coverage",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PCT_EXC_TOTAL",
        "slug": "picard_wgs_pct_exc_total",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PCT_1X",
        "slug": "picard_wgs_pct_1x",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PCT_5X",
        "slug": "picard_wgs_pct_5x",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "PCT_10X",
        "slug": "picard_wgs_pct_10x",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "HET_SNP_SENSITIVITY",
        "slug": "wgs_het_snp_sensitivity",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "HET_SNP_Q",
        "slug": "wgs_het_snp_q",
        "type": "Float64",
        "agg_func": "mean",
    },
]

PICARD_ALIGNMENT_SUMMARY_COLUMNS = [
    {
        "name": "TOTAL_READS",
        "slug": "picard_alignment_total_reads",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "PF_READS_ALIGNED",
        "slug": "picard_alignment_pf_reads_aligned",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "PCT_PF_READS_ALIGNED",
        "slug": "picard_alignment_pct_pf_reads_aligned",
        "type": "Float64",
        "agg_func": "mean",
    },
]

PICARD_DUPLICATION_METRICS_COLUMNS = [
    {
        "name": "UNPAIRED_READS_EXAMINED",
        "slug": "picard_dup_unpaired_reads_examined",
        "type": "Int64",
        "agg_func": "sum",
    },
    {
        "name": "PERCENT_DUPLICATION",
        "slug": "picard_dup_percent_duplication",
        "type": "Float64",
        "agg_func": "mean",
    },
]

PICARD_INSERT_SIZE_METRICS_COLUMNS = [
    {
        "name": "MEDIAN_INSERT_SIZE",
        "slug": "picard_insert_median_size",
        "type": "Float64",
        "agg_func": "mean",
    },
    {
        "name": "MEAN_INSERT_SIZE",
        "slug": "picard_insert_mean_size",
        "type": "Float64",
        "agg_func": "mean",
    },
]


def general_multiqc_parser(file_object, name, column_names):
    """General parser for MultiQC files."""
    df = pd.read_csv(file_object, sep="\t", index_col=0)

    # Keep only specified columns:
    df = df[
        [
            column.get("name", "")
            for column in column_names
            if column.get("name", "") in df.columns
        ]
    ]
    # Rename
    df = df.rename(
        columns={
            column.get("name", ""): column["slug"]
            for column in column_names
            if column.get("name", "") in df.columns
        }
    )

    # Convert columns with percentage (%) symbols to float
    for column in df.columns:
        if df[column].dtype == object and df[column].str.endswith("%").all():
            df[column] = df[column].str.rstrip("%").astype(float) / 100

    if df.empty:
        return pd.Series(name=name)

    # Perform aggregation
    series = df.agg(
        {
            column["slug"]: column["agg_func"]
            for column in column_names
            if column["slug"] in df.columns
        }
    )
    series.name = name
    return series


class QCTables(BaseTables):
    """A helper class to fetch collection's QC data.

    A simple example:

    .. code-block:: python

        # Get Collection object
        collection = res.collection.get("collection-slug")

        # Fetch collection expressions and metadata
        tables = QCTables(collection)
        tables.qc

    """

    process_type = "data:multiqc:"

    # Data types:
    GENERAL = "general"
    QORTS = "qorts"
    CHIPSEQ_PREPREAK = "chipseq_prepeaks"
    CHIPSEQ_POSTPEAK = "chipseq_postpeaks"
    MACS = "macs"
    PICARD_WGS = "picard_wgs"
    PICARD_ALIGNMENT_SUMMARY = "picard_alignment_summary"
    PICARD_DUPLICATION_METRICS = "picard_duplication_metrics"
    PICARD_INSERT_SIZE_METRICS = "picard_insert_size_metrics"

    data_type_to_field_name = {
        GENERAL: "report_data",
        QORTS: "report_data",
        CHIPSEQ_PREPREAK: "report_data",
        CHIPSEQ_POSTPEAK: "report_data",
        MACS: "report_data",
        PICARD_WGS: "report_data",
        PICARD_ALIGNMENT_SUMMARY: "report_data",
        PICARD_DUPLICATION_METRICS: "report_data",
        PICARD_INSERT_SIZE_METRICS: "report_data",
    }

    def _parse_file(self, file_obj, sample_id, data_type):
        """Parse file object and return a one DataFrame line."""
        if data_type == self.GENERAL:
            return general_multiqc_parser(file_obj, sample_id, MQC_GENERAL_COLUMNS)
        if data_type == self.QORTS:
            return general_multiqc_parser(file_obj, sample_id, QORTS_COLUMNS)
        if data_type == self.MACS:
            return general_multiqc_parser(file_obj, sample_id, MACS_COLUMNS)
        if data_type == self.CHIPSEQ_PREPREAK:
            return general_multiqc_parser(file_obj, sample_id, PREPEAK_CHIPQC_COLUMNS)
        if data_type == self.CHIPSEQ_POSTPEAK:
            return general_multiqc_parser(file_obj, sample_id, POSTPEAK_CHIPQC_COLUMNS)
        if data_type == self.PICARD_WGS:
            return general_multiqc_parser(file_obj, sample_id, PICARD_WGS_COLUMNS)
        if data_type == self.PICARD_ALIGNMENT_SUMMARY:
            return general_multiqc_parser(
                file_obj, sample_id, PICARD_ALIGNMENT_SUMMARY_COLUMNS
            )
        if data_type == self.PICARD_DUPLICATION_METRICS:
            return general_multiqc_parser(
                file_obj, sample_id, PICARD_DUPLICATION_METRICS_COLUMNS
            )
        if data_type == self.PICARD_INSERT_SIZE_METRICS:
            return general_multiqc_parser(
                file_obj, sample_id, PICARD_INSERT_SIZE_METRICS_COLUMNS
            )

    def _get_data_uri(self, data: Data, data_type: str) -> str:
        if data_type == self.GENERAL:
            return f"{data.id}/multiqc_data/multiqc_general_stats.txt"
        if data_type == self.QORTS:
            return f"{data.id}/multiqc_data/multiqc_qorts.txt"
        if data_type == self.CHIPSEQ_PREPREAK:
            return f"{data.id}/multiqc_data/multiqc_chip_seq_prepeak_qc-plot.txt"
        if data_type == self.CHIPSEQ_POSTPEAK:
            return f"{data.id}/multiqc_data/multiqc_chip_seq_postpeak_qc-plot.txt"
        if data_type == self.MACS:
            return f"{data.id}/multiqc_data/multiqc_macs.txt"
        if data_type == self.PICARD_WGS:
            return f"{data.id}/multiqc_data/multiqc_picard_wgsmetrics.txt"
        if data_type == self.PICARD_ALIGNMENT_SUMMARY:
            return f"{data.id}/multiqc_data/multiqc_picard_AlignmentSummaryMetrics.txt"
        if data_type == self.PICARD_DUPLICATION_METRICS:
            return f"{data.id}/multiqc_data/multiqc_picard_dups.txt"
        if data_type == self.PICARD_INSERT_SIZE_METRICS:
            return f"{data.id}/multiqc_data/multiqc_picard_insertSize.txt"

    @property
    @lru_cache()
    def general(self) -> pd.DataFrame:
        return self._load_fetch(self.GENERAL)

    @property
    @lru_cache()
    def qorts(self) -> pd.DataFrame:
        return self._load_fetch(self.QORTS)

    @property
    @lru_cache()
    def macs(self) -> pd.DataFrame:
        return self._load_fetch(self.MACS)

    @property
    @lru_cache()
    def chipseq_prepeak(self) -> pd.DataFrame:
        return self._load_fetch(self.CHIPSEQ_PREPREAK)

    @property
    @lru_cache()
    def chipseq_postpeak(self) -> pd.DataFrame:
        return self._load_fetch(self.CHIPSEQ_POSTPEAK)

    @property
    @lru_cache()
    def picard_wgs_metrics(self) -> pd.DataFrame:
        return self._load_fetch(self.PICARD_WGS)

    @property
    @lru_cache()
    def picard_alignment_summary(self) -> pd.DataFrame:
        return self._load_fetch(self.PICARD_ALIGNMENT_SUMMARY)

    @property
    @lru_cache()
    def picard_duplication_metrics(self) -> pd.DataFrame:
        return self._load_fetch(self.PICARD_DUPLICATION_METRICS)

    @property
    @lru_cache()
    def picard_insert_size_metrics(self) -> pd.DataFrame:
        return self._load_fetch(self.PICARD_INSERT_SIZE_METRICS)

    @property
    @lru_cache()
    def qc(self):
        return pd.concat(
            objs=[
                self.general,
                self.qorts,
                self.macs,
                self.chipseq_prepeak,
                self.chipseq_postpeak,
                self.picard_wgs_metrics,
                self.picard_alignment_summary,
                self.picard_duplication_metrics,
                self.picard_insert_size_metrics,
            ],
            axis=1,
        )
