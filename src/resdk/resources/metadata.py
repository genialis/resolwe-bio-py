"""Collection Metadata resource."""

import logging
import os
import tempfile
import warnings
from io import BytesIO
from typing import TYPE_CHECKING, Callable, Optional
from urllib.parse import urljoin

import pandas as pd

from .base import DataSource
from .data import Data
from .utils import get_collection_id

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class Metadata(Data):
    """Metadata resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    sample_identifier_columns = {
        "Sample ID": "id",
        "ms#Sample ID": "id",
        "Sample slug": "slug",
        "ms#Sample slug": "slug",
        "Sample name": "name",
        "ms#Sample name": "name",
    }

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)
        self._df_bytes: Optional[BytesIO] = None
        self._df = model_data.pop("df", None)

        super().__init__(resolwe, **model_data)

        if self.id is None:
            # Set unique (=set self.process) only if Metadata is not yet uploaded
            self.unique = model_data.get("unique", True)

    @property
    def unique(self) -> bool:
        """Get unique attribute.

        This attribute tells if Metadata has one-to-one or one-to-many
        relation to collection samples.
        """
        if self.id or self.process:
            return self.process.slug == "upload-metadata-unique"

        # If no info, consider this true by default
        return True

    @unique.setter
    def unique(self, value: bool):
        if self.id:
            raise ValueError(
                "Setting unique attribute on already uploaded Metadata is not allowed!"
            )
        if not isinstance(value, bool):
            raise ValueError("Attribute unique can only have True / False value")

        # In practice value of unique property is just a proxy for process
        # Therefore, store process instead of unique
        slug = "upload-metadata-unique" if value else "upload-metadata"
        assert self.resolwe.process is not None
        self.process = self.resolwe.process.get(slug=slug, ordering="-created", limit=1)

    @property
    def df_bytes(self) -> BytesIO:
        """Get file contents of table output in bytes form."""
        if self._df_bytes is None:
            if not (self.id and "table" in self.output):
                raise ValueError(
                    "Cannot get df bytes if there is no table in output fields..."
                )

            url = urljoin(
                self.resolwe.url, f"data/{self.id}/{self.output['table']['file']}"
            )
            response = self.resolwe.session.get(url, auth=self.resolwe.auth)
            response.raise_for_status()
            self._df_bytes = BytesIO(response.content)

        self._df_bytes.seek(0)
        return self._df_bytes

    def set_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Set index of df to Sample ID.

        If there is a column with ``Sample ID`` just set that as index. If there is
        ``Sample name`` or ``Sample slug`` column, map sample name / slug to sample ID's
        and set ID's as an index. If no suitable column in there, raise an error.
        Works also if any of the above options is already an index with appropriate name.
        """
        for match_column in self.sample_identifier_columns:
            if match_column in df.columns:
                break
            if match_column == df.index.name:
                # Add new column with index name
                df[match_column] = df.index
                break
        else:
            options = ", ".join(self.sample_identifier_columns)
            raise ValueError(
                f"There should be a column in df with one of the following names: {options}"
            )

        if match_column in ["Sample ID", "ms#Sample ID"]:
            # Just set this as index and return
            return df.set_index(match_column)

        # Sample identifiers from df
        df_samples = df[match_column].astype(str)

        # Sample identifiers from collection
        attr = self.sample_identifier_columns[match_column]
        col_samples = self.collection.samples.filter(fields=["id", attr])

        # Map to Sample IDs
        mapping = {getattr(s, attr): s.id for s in col_samples}
        df["Sample ID"] = [mapping.get(s, None) for s in df_samples]

        # Remove the samples that do not have mapping
        df = df.dropna(subset=["Sample ID"])

        return df.set_index("Sample ID")

    def validate_df(self, df: pd.DataFrame):
        """Validate df property.

        Validates that df:

        - is an instance of pandas.DataFrame
        - index contains sample IDs that match some samples:

            - If not matches, raise warning
            - If there are samples in df but not in collection, raise warning
            - If there are samples in collection but not in df, raise warning

        """
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Attribute df must be a pandas.DataFrame object.")

        df_samples = set(df.index)

        # Sample IDs from collection
        col_samples = {s.id for s in self.collection.samples.filter(fields=["id"])}

        intersection = df_samples & col_samples
        if not intersection:
            warnings.warn(
                "No intersection between samples in df and samples in collection."
            )

        not_in_col = df_samples - col_samples
        if not_in_col:
            missing = ", ".join(list(map(str, not_in_col))[:5]) + (
                "..." if len(not_in_col) > 5 else ""
            )
            warnings.warn(
                f"There are {len(not_in_col)} samples in df that are not in collection: {missing}"
            )

        not_in_df = col_samples - df_samples
        if not_in_df:
            missing = ", ".join(list(map(str, not_in_df))[:5]) + (
                "..." if len(not_in_df) > 5 else ""
            )
            warnings.warn(
                f"There are {len(not_in_df)} samples in collection that are not in df: {missing}"
            )

    def get_df(self, parser: Optional[Callable] = None, **kwargs):
        """Get table as pd.DataFrame."""
        # Do not use cached value if parser is specified
        if self._df is None or parser is not None:
            if self.id is None:
                return None
            if not self.output or "table" not in self.output:
                raise ValueError('Cannot parse, no output with name "table".')

            # Enable parsing the byte stream with arbitrary parser, not just pandas
            # Otherwise try to guess the parser based on file extension
            basename = self.output["table"]["file"]
            if parser is None:
                if basename.endswith("xls"):
                    parser = pd.read_excel
                    kwargs = dict(engine="xlrd")
                elif basename.endswith("xlsx"):
                    parser = pd.read_excel
                    kwargs = dict(engine="openpyxl")
                elif any(basename.endswith(ext) for ext in ["tab", "tsv"]):
                    parser = pd.read_csv
                    kwargs = dict(
                        sep="\t", low_memory=False, float_precision="round_trip"
                    )
                else:
                    parser = pd.read_csv
                    kwargs = dict(low_memory=False, float_precision="round_trip")

            df = parser(self.df_bytes, **kwargs)

            df = self.set_index(df)
            self.validate_df(df)
            self._df = df

        return self._df

    def set_df(self, value: pd.DataFrame):
        """Set df."""
        if self.id:
            raise ValueError(
                "Setting df attribute on already uploaded Metadata is not allowed."
            )
        if not self.collection:
            # Validation is not possible without collection
            raise ValueError(
                "Setting df attribute before setting collection is not allowed."
            )

        self.validate_df(value)
        self._df = value

    df = property(get_df, set_df)

    def save(self):
        """Save Metadata to the server.

        If Metadata is already uploaded: update. Otherwise, create new one.
        """
        if self.id:
            super().save()
        else:
            if not self.collection:
                raise ValueError("Collection must be set before saving.")
            if self.df is None or self.df.empty:
                raise ValueError("Attribute df must be set before saving.")

            # All resdk machinery for uploading files works with real
            # files on the system. Ideally we would support "file upload"
            # from a stream, but for now, let's use a tempfile solution.
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file = os.path.join(tmp_dir, self.name or "metadata.csv")
                self.df.to_csv(tmp_file)
                inputs = self.resolwe._process_inputs({"src": tmp_file}, self.process)
                # On context manager exit, tmp_dir and it's contents are removed

            data = {
                "process": {"slug": self.process.slug},
                "input": inputs,
                "collection": {"id": get_collection_id(self.collection)},
                "tags": self.collection.tags,
            }
            if self.name:
                data["name"] = self.name

            model_data = self.api.post(data)
            self._update_fields(model_data, DataSource.SERVER)

    def __repr__(self) -> str:
        """
        Format name.

        To ease distinction between 1-1 / 1-n Metadata, provide also
        process slug.
        """
        return "{} <id: {}, slug: '{}', name: '{}', process slug: '{}'>".format(
            self.__class__.__name__,
            self.id,
            self.slug,
            self.name,
            getattr(self.process, "slug", None),
        )
