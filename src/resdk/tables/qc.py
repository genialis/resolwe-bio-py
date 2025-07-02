""".. Ignore pydocstyle D400.

========
QCTables
========

.. autoclass:: QCTables
    :members:
    :inherited-members:

    .. automethod:: __init__

"""

from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from resdk.resources import Collection, Data

from .base import BaseTables
from .qc_mappings import (
    BOWTIE2_MAP,
    GENERAL_ALIGNMENT_MAP,
    GENERAL_FASTQ_MAP,
    GENERAL_QC_MAP,
    GENERAL_QUANTIFICATION_MAP,
    MACS_POSTPEAK_MAP,
    MACS_PREPEAK_MAP,
    MACS_SUMMARY_MAP,
    PICARD_ALIGNMENT_MAP,
    PICARD_DUPS_MAP,
    PICARD_INSERT_SIZE_MAP,
    PICARD_METHYLATION_MAP,
    PICARD_WGS_MAP,
    QORTS_SUMMARY_MAP,
    SAMPLE_INFO_MAP,
)


def _filter_and_rename_columns(df, column_map):
    """Filter, apply a scaling factor and rename columns based on provided specifications."""
    selected_columns = []
    rename_map = {}

    for col in column_map:
        names = col.get("name", [])
        slug = col.get("slug", "")
        scaling_factor = col.get("scaling_factor", {})

        if isinstance(names, str):
            names = [names]

        for name in names:
            if name in df.columns:
                selected_columns.append(name)
                rename_map[name] = slug
                # Some column values are given a specific format (e.g. millions)
                # and need to be scaled on a common scale
                df[name] = df[name] * scaling_factor.get(name, 1)
                break

    df = df[selected_columns].rename(columns=rename_map)

    return df


def _aggregate_df(df, column_map, prefix=None):
    """Perform aggregation on specified columns of a DataFrame and return a Series."""
    agg_map = {
        col["slug"]: (
            # This fixes an issue where pandas mistakenly interprets "first" as a method
            (lambda x: x.iloc[0])
            if col["agg_func"] == "first"
            else col["agg_func"]
        )
        for col in column_map
        if col["slug"] in df.columns
    }
    series = df.agg(agg_map)

    if prefix:
        series = series.add_prefix(prefix)

    return series


def general_multiqc_parser(file_object, name, column_map):
    """General parser for MultiQC files.

    If the column_map argument is not specified the function will retain the original column names
    and apply mean aggregation to the rows.
    """

    df = pd.read_csv(file_object, sep="\t", index_col=0).convert_dtypes()

    if column_map:
        df = _filter_and_rename_columns(df=df, column_map=column_map)
    else:
        # Mean aggregation was chosen as a default aggregation function
        # for columns that are not specified in the column_map.
        column_map = [{"slug": col, "agg_func": "mean"} for col in df.columns]

    if df.empty:
        return pd.Series(name=name)

    series = _aggregate_df(df=df, column_map=column_map)

    series.name = name

    return series


def macs_prepeak_parser(file_object, name, column_map, sample_name):
    """MAC2 prepeak parser for MultiQC files.

    This function separates the case and control samples and then performs aggregation.
    The output is a series where case and control samples are denoted with a prefix in the column names.
    """
    df = pd.read_csv(file_object, sep="\t", index_col=0)

    if df.empty:
        return pd.Series(name=name)

    df = _filter_and_rename_columns(df=df, column_map=column_map)

    # Convert columns with percentage (%) symbols to float
    for column in df.columns:
        if df[column].dtype == object and df[column].str.endswith("%").all():
            df[column] = df[column].str.rstrip("%").astype(float) / 100

    case_df = df[df.index == sample_name]
    control_df = df[df.index == f"Background of {sample_name}"]

    case_series = _aggregate_df(
        df=case_df,
        column_map=column_map,
        prefix="case_",
    )

    control_series = _aggregate_df(
        df=control_df,
        column_map=column_map,
        prefix="control_",
    )

    series = pd.concat([case_series, control_series])
    series.name = name
    return series


def samtools_idxstats_parser(file_object, name, **kwargs):
    """Parse samtools idxstats file.

    The columns correspond to contigs in the input annotation file.
    The individual values have the following format:
        [# mapped read-segments, contig length (bp)]

    This parser creates a MultiIndex DataFrame with columns
    reflecting the contig and its mapped read segments and contig length.
    """

    def _extract_numbers(s):
        s = s.strip("[]")
        mapped, unmapped = s.split(",")
        return int(mapped.strip()), int(unmapped.strip())

    df = pd.read_csv(file_object, sep="\t", index_col=0)

    if df.empty:
        return pd.Series(name=name)

    level1_columns = ["mapped_segments", "contig_length"]
    columns = pd.MultiIndex.from_product(
        [
            df.columns,
            level1_columns,
        ],
    )

    df_multi = pd.DataFrame(columns=columns, index=df.index)

    for col in df.columns:
        df_multi[(col, level1_columns[0])], df_multi[(col, level1_columns[1])] = zip(
            *df[col].apply(_extract_numbers)
        )

    series = df_multi.squeeze()
    series.name = name
    return series


def qorts_genebody_parser(file_object, name, **kwargs):
    """Parse QoRTs genebody coverage file."""

    df = pd.read_csv(file_object, sep="\t", index_col=0)

    if df.empty:
        return pd.Series(name=name)

    df.columns = df.columns.astype(float).round(1)
    df_sorted = df[sorted(df.columns, key=float)]

    series = df_sorted.squeeze()
    series.name = name
    return series


class QCTables(BaseTables):
    """A helper class to fetch collection's QC data.

    A simple example:

    .. code-block:: python

        # Get Collection object
        collection = res.collection.get("collection-slug")

        # Fetch collection qc (RNA-seq metrics) and metadata
        tables = QCTables(collection)
        tables.rnaseq
        tables.meta
    """

    process_type = "data:multiqc:"

    # Data types:
    # The properties are invoked dynamically based on the data type name.
    # e.g. QCTables(collection).sample_info
    SAMPLE_INFO = "sample_info"
    GENERAL_FASTQ = "general_fastq"
    GENERAL_ALIGNMENT = "general_alignment"
    GENERAL_QUANTIFICATION = "general_quantification"
    GENERAL_QC = "general_qc"
    MACS_SUMMARY = "macs_summary"
    MACS_PREPEAK = "macs_prepeak_metrics"
    MACS_POSTPEAK = "macs_postpeak_metrics"
    PICARD_WGS_METRICS = "picard_wgs_metrics"
    PICARD_ALIGNMENT_SUMMARY = "picard_alignment_summary"
    PICARD_DUPLICATION_METRICS = "picard_duplication_metrics"
    PICARD_INSERT_SIZE_METRICS = "picard_insert_size_metrics"
    PICARD_METHYLATION_METRICS = "picard_methylation_metrics"
    SAMTOOLS_IDXSTATS = "samtools_idxstats"
    SAMTOOLS_FLAGSTAT = "samtools_flagstat"
    QORTS_SUMMARY = "qorts_summary"
    QORTS_GENEBODY = "qorts_genebody"
    BOWTIE2_SUMMARY = "bowtie2_summary"

    # Data groups:
    # Groups were created based on the data types included in the MultiQC report generated by the
    # corresponding Resolwe pipelines.
    # Some data types are not assigned to any groups, even though they are part of the MultiQC report
    # generated by the Resolwe pipelines. This is a design choice to keep the less relevant data
    # from cluttering the output tables.
    RNASEQ_GROUP = "rnaseq"
    WGS_GROUP = "wgs"
    CHIPSEQ_GROUP = "chipseq"
    WGBS_GROUP = "wgbs"
    CUTNRUN_GROUP = "cutnrun"
    ATACSEQ_GROUP = "atacseq"
    WES_GROUP = "wes"

    # Not all data types have column mappings, some retain the original column names.
    # This is especially important for data types where column names may vary between samples,
    # e.g. samtools idxstats column names are based on contig names in the alignment index file.
    DATA_TYPES = {
        SAMPLE_INFO: {
            "file": "multiqc_data/multiqc_sample_info.txt",
            "parser": general_multiqc_parser,
            "column_map": SAMPLE_INFO_MAP,
            "groups": [
                CHIPSEQ_GROUP,
                WGS_GROUP,
                RNASEQ_GROUP,
                WGBS_GROUP,
                CUTNRUN_GROUP,
                ATACSEQ_GROUP,
                WES_GROUP,
            ],
        },
        GENERAL_FASTQ: {
            "file": "multiqc_data/multiqc_general_stats.txt",
            "parser": general_multiqc_parser,
            "column_map": GENERAL_FASTQ_MAP,
            "groups": [
                CHIPSEQ_GROUP,
                WGS_GROUP,
                RNASEQ_GROUP,
                WGBS_GROUP,
                CUTNRUN_GROUP,
                ATACSEQ_GROUP,
                WES_GROUP,
            ],
        },
        GENERAL_ALIGNMENT: {
            "file": "multiqc_data/multiqc_general_stats.txt",
            "parser": general_multiqc_parser,
            "column_map": GENERAL_ALIGNMENT_MAP,
            # Currently includes only STAR alignment metrics
            # STAR is used only in the RNA-seq pipeline
            "groups": [
                RNASEQ_GROUP,
            ],
        },
        GENERAL_QUANTIFICATION: {
            "file": "multiqc_data/multiqc_general_stats.txt",
            "parser": general_multiqc_parser,
            "column_map": GENERAL_QUANTIFICATION_MAP,
            "groups": [RNASEQ_GROUP],
        },
        GENERAL_QC: {
            "file": "multiqc_data/multiqc_general_stats.txt",
            "parser": general_multiqc_parser,
            "column_map": GENERAL_QC_MAP,
            # Currently includes only RNA-seq QC metrics
            # from QoRTs and RNA-SeQC
            "groups": [RNASEQ_GROUP],
        },
        MACS_SUMMARY: {
            "file": "multiqc_data/multiqc_macs.txt",
            "parser": general_multiqc_parser,
            "column_map": MACS_SUMMARY_MAP,
            "groups": [CHIPSEQ_GROUP, CUTNRUN_GROUP, ATACSEQ_GROUP],
        },
        MACS_PREPEAK: {
            "file": "multiqc_data/multiqc_chip_seq_prepeak_qc.txt",
            "parser": macs_prepeak_parser,
            "column_map": MACS_PREPEAK_MAP,
            "groups": [CHIPSEQ_GROUP, CUTNRUN_GROUP, ATACSEQ_GROUP],
        },
        MACS_POSTPEAK: {
            "file": "multiqc_data/multiqc_chip_seq_postpeak_qc.txt",
            "parser": general_multiqc_parser,
            "column_map": MACS_POSTPEAK_MAP,
            "groups": [CHIPSEQ_GROUP, CUTNRUN_GROUP, ATACSEQ_GROUP],
        },
        PICARD_WGS_METRICS: {
            "file": "multiqc_data/multiqc_picard_wgsmetrics.txt",
            "parser": general_multiqc_parser,
            "column_map": PICARD_WGS_MAP,
            "groups": [WGS_GROUP, WGBS_GROUP],
        },
        PICARD_ALIGNMENT_SUMMARY: {
            "file": "multiqc_data/multiqc_picard_AlignmentSummaryMetrics.txt",
            "parser": general_multiqc_parser,
            "column_map": PICARD_ALIGNMENT_MAP,
            "groups": [WGS_GROUP, WGBS_GROUP],
        },
        PICARD_DUPLICATION_METRICS: {
            "file": "multiqc_data/multiqc_picard_dups.txt",
            "parser": general_multiqc_parser,
            "column_map": PICARD_DUPS_MAP,
            "groups": [WGS_GROUP, WGBS_GROUP, CUTNRUN_GROUP, WES_GROUP],
        },
        PICARD_INSERT_SIZE_METRICS: {
            "file": "multiqc_data/multiqc_picard_insertSize.txt",
            "parser": general_multiqc_parser,
            "column_map": PICARD_INSERT_SIZE_MAP,
            "groups": [WGS_GROUP, WGBS_GROUP],
        },
        PICARD_METHYLATION_METRICS: {
            "file": "multiqc_data/multiqc_picard_RrbsSummaryMetrics.txt",
            "parser": general_multiqc_parser,
            "column_map": PICARD_METHYLATION_MAP,
            "groups": [WGBS_GROUP],
        },
        SAMTOOLS_IDXSTATS: {
            "file": "multiqc_data/multiqc_samtools_idxstats.txt",
            "parser": samtools_idxstats_parser,
            "column_map": [],
            "groups": [],
        },
        SAMTOOLS_FLAGSTAT: {
            "file": "multiqc_data/multiqc_samtools_flagstat.txt",
            "parser": general_multiqc_parser,
            "column_map": [],
            "groups": [],
        },
        QORTS_SUMMARY: {
            "file": "multiqc_data/multiqc_qorts.txt",
            "parser": general_multiqc_parser,
            "column_map": QORTS_SUMMARY_MAP,
            "groups": [],
        },
        QORTS_GENEBODY: {
            "file": "multiqc_data/multiqc_genebody_qc.txt",
            "parser": qorts_genebody_parser,
            "column_map": [],
            "groups": [],
        },
        BOWTIE2_SUMMARY: {
            "file": "multiqc_data/multiqc_bowtie2.txt",
            "parser": general_multiqc_parser,
            "column_map": BOWTIE2_MAP,
            "groups": [CUTNRUN_GROUP, ATACSEQ_GROUP],
        },
    }

    def __init__(
        self,
        collection: Collection,
        cache_dir: Optional[str] = None,
        progress_callable: Optional[Callable] = None,
        **kwargs,
    ):
        """Initialize class.

        :param collection: collection to use
        :param cache_dir: cache directory location, if not specified system specific
                          cache directory is used
        :param progress_callable: custom callable that can be used to report
                                  progress. By default, progress is written to
                                  stderr with tqdm
        """
        super().__init__(collection, cache_dir, progress_callable, **kwargs)
        self.data_groups = list(
            set(group for data in self.DATA_TYPES.values() for group in data["groups"])
        )

    def _parse_file(self, file_obj, sample_id, data_type):
        """Parse file object and return one DataFrame line."""
        if data_type == self.MACS_PREPEAK:
            case_sample = next(
                (sample for sample in self._samples if sample.id == sample_id), None
            )
            sample_name = case_sample.name
            return self.DATA_TYPES[data_type]["parser"](
                file_object=file_obj,
                name=sample_id,
                column_map=self.DATA_TYPES[data_type]["column_map"],
                sample_name=sample_name,
            )
        else:
            if data_type in self.DATA_TYPES:
                parser_func = self.DATA_TYPES[data_type]["parser"]
                return parser_func(
                    file_object=file_obj,
                    name=sample_id,
                    column_map=self.DATA_TYPES[data_type]["column_map"],
                )
            else:
                raise ValueError(f"Unknown data type: {data_type}")

    def _get_data_uri(self, data: Data, data_type: str) -> str:
        """Get the file path based on data type."""
        if data_type not in self.DATA_TYPES:
            raise ValueError(f"Unknown data type: {data_type}")

        files = data.files(field_name="report_data")
        target_fn = self.DATA_TYPES[data_type]["file"]

        if target_fn not in files:
            # Some MultiQC versions returned the same file with the ``-plot`` suffix
            suffix = Path(target_fn).suffix
            target_fn2 = target_fn.replace(suffix, f"-plot{suffix}")
            if target_fn2 in files:
                return f"{data.id}/{target_fn2}"

        return f"{data.id}/{target_fn}"

    @lru_cache()
    def _fetch_group(self, group_name: str) -> pd.DataFrame:
        """Return a DataFrame with QC data for a specific group."""
        data_types = [
            data_type
            for data_type, data in self.DATA_TYPES.items()
            if group_name in data["groups"]
        ]
        data = [self._load_fetch(data_type) for data_type in data_types]
        df = pd.concat(data, axis=1)
        return df

    @lru_cache()
    def _load_fetch(self, data_type):
        df = super()._load_fetch(data_type)
        if data_type == self.META:
            return df
        df = df.convert_dtypes()

        column_mappings = self.DATA_TYPES[data_type]["column_map"]
        column_types = {
            c["slug"]: c["type"] for c in column_mappings if c["slug"] in df.columns
        }

        for col, dtype in column_types.items():
            # Ensure that these numbers are round to nearest integer
            if "int" in dtype.lower():
                with suppress(TypeError):
                    df[col] = df[col].round().astype(dtype)
            else:
                df[col] = df[col].astype(dtype)

        return df

    def __getattr__(self, name):
        """Dynamically handle property fetching for data types."""
        parent_attr = getattr(super(), name, None)
        if parent_attr is not None:
            return parent_attr
        else:
            if name in self.data_groups:
                return self._fetch_group(group_name=name)
            elif name in self.DATA_TYPES:
                return self._load_fetch(name)
            else:
                raise AttributeError(
                    f"'{self.__class__.__name__}' object has no attribute '{name}'. "
                    f"Choose one of the following: {list(self.DATA_TYPES.keys()) + self.data_groups}"
                )
