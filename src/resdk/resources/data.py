"""Data resource."""

import json
import logging
from typing import Optional
from urllib.parse import urljoin

from resdk.constants import CHUNK_SIZE

from ..utils.decorators import assert_object_exists
from .background_task import BackgroundTask
from .base import BaseResolweResource
from .collection import Collection
from .descriptor import DescriptorSchema
from .process import Process
from .sample import Sample
from .utils import flatten_field, parse_resolwe_datetime


class Data(BaseResolweResource):
    """Resolwe Data resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "data"
    full_search_paramater = "text"

    READ_ONLY_FIELDS = BaseResolweResource.READ_ONLY_FIELDS + (
        "checksum",
        "descriptor_dirty",
        "duplicated",
        "process_cores",
        "process_error",
        "process_info",
        "process_memory",
        "process_progress",
        "process_rc",
        "process_warning",
        "output",
        "scheduled",
        "size",
        "status",
    )
    UPDATE_PROTECTED_FIELDS = BaseResolweResource.UPDATE_PROTECTED_FIELDS + (
        "input",
        "process",
    )
    WRITABLE_FIELDS = BaseResolweResource.WRITABLE_FIELDS + (
        "collection",
        "descriptor",
        "descriptor_schema",
        "process_resources",
        "sample",
        "tags",
    )

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: ``Collection``s that contains ``Data``
        self._collection = None
        #: ``DescriptorSchema`` of ``Data`` object
        self._descriptor_schema = None
        #: The process used in this data object
        self._process = None
        #: ``Sample`` containing ``Data`` object
        self._sample = None

        #: ``ResolweQuery`` containing parent ``Data`` objects (lazy loaded)
        self._parents = None
        #: ``ResolweQuery`` containing child ``Data`` objects (lazy loaded)
        self._children = None

        #: checksum field calculated on inputs
        self.checksum = None
        #: indicate whether `descriptor` doesn't match `descriptor_schema` (is dirty)
        self.descriptor_dirty = None
        #: annotation data, with the form defined in descriptor_schema
        self.descriptor = None
        #: duplicated
        self.duplicated = None
        #: actual input values
        self.input = None
        #: process cores
        self.process_cores = None
        #: error log message (list of strings)
        self.process_error = None
        #: info log message (list of strings)
        self.process_info = None
        #: process memory
        self.process_memory = None
        #: process progress in percentage
        self.process_progress = None
        #: Process algorithm return code
        self.process_rc = None
        #: warning log message (list of strings)
        self.process_warning = None
        #: actual output values
        self.output = None
        #: process_resources
        self.process_resources = None
        #: size
        self.size = None
        #: scheduled
        self.scheduled = None
        #: process status - Possible values:
        #: UP (Uploading - for upload processes),
        #: RE (Resolving - computing input data objects)
        #: WT (Waiting - waiting for process since the queue is full)
        #: PP (Preparing - preparing the environment for processing)
        #: PR (Processing)
        #: OK (Done)
        #: ER (Error)
        #: DR (Dirty - Data is dirty)
        self.status = None
        #: data object's tags
        self.tags = None

        super().__init__(resolwe, **model_data)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._children = None
        self._collection = None
        self._descriptor_schema = None
        self._parents = None
        self._process = None
        self._sample = None

        super().update()

    @property
    def process(self):
        """Get process."""
        return self._process

    @process.setter
    def process(self, payload):
        """Set process."""
        self._resource_setter(payload, Process, "_process")

    @property
    def descriptor_schema(self):
        """Get descriptor schema."""
        return self._descriptor_schema

    @descriptor_schema.setter
    def descriptor_schema(self, payload):
        """Set descriptor schema."""
        self._resource_setter(payload, DescriptorSchema, "_descriptor_schema")

    @property
    def sample(self):
        """Get sample."""
        if self._sample is None and self._original_values.get("entity", None):
            # The collection data is only serialized on the top level. Replace the
            # data inside 'entity' with the actual collection data.
            entity_values = self._original_values["entity"].copy()
            entity_values["collection"] = self._original_values.get("collection", None)
            self._sample = Sample(resolwe=self.resolwe, **entity_values)
        return self._sample

    @sample.setter
    def sample(self, payload):
        """Set sample."""
        self._resource_setter(payload, Sample, "_sample")

    @property
    def collection(self):
        """Get collection."""
        return self._collection

    @collection.setter
    def collection(self, payload):
        """Set collection."""
        self._resource_setter(payload, Collection, "_collection")

    @property
    @assert_object_exists
    def started(self):
        """Get start time."""
        return parse_resolwe_datetime(self._original_values["started"])

    @property
    @assert_object_exists
    def finished(self):
        """Get finish time."""
        return parse_resolwe_datetime(self._original_values["finished"])

    @property
    @assert_object_exists
    def parents(self):
        """Get parents of this Data object."""
        if self._parents is None:
            ids = [
                item["id"]
                for item in self.resolwe.api.data(self.id).parents.get(fields="id")
            ]
            if not ids:
                return []
            # Resolwe querry must be returned:
            self._parents = self.resolwe.data.filter(id__in=ids)

        return self._parents

    @property
    @assert_object_exists
    def children(self):
        """Get children of this Data object."""
        if self._children is None:
            ids = [
                item["id"]
                for item in self.resolwe.api.data(self.id).children.get(fields="id")
            ]
            if not ids:
                return []
            # Resolwe querry must be returned:
            self._children = self.resolwe.data.filter(id__in=ids)

        return self._children

    def restart(
        self,
        storage: Optional[int] = None,
        memory: Optional[int] = None,
        cores: Optional[int] = None,
    ):
        """Restart the data object.

        The units for storage are gigabytes and for memory are megabytes.

        The resources that are not specified (or set no None) are reset to their
        default values.
        """
        overrides = {
            key: value
            for key, value in {
                "storage": storage,
                "memory": memory,
                "cores": cores,
            }.items()
            if value is not None
        }
        self.resolwe.api.data(self.id).restart.post(
            {"resource_overrides": {self.id: overrides}}
        )

    def _files_dirs(self, field_type, file_name=None, field_name=None):
        """Get list of downloadable fields."""
        download_list = []

        def put_in_download_list(elm, fname):
            """Append only files od dirs with equal name."""
            if field_type in elm:
                if file_name is None or file_name == elm[field_type]:
                    download_list.append(elm[field_type])
            else:
                raise KeyError(
                    "Item {} does not contain '{}' key.".format(fname, field_type)
                )

        if field_name and not field_name.startswith("output."):
            field_name = "output.{}".format(field_name)

        flattened = flatten_field(self.output, self.process.output_schema, "output")
        for ann_field_name, ann in flattened.items():
            if (
                ann_field_name.startswith("output")
                and (field_name is None or field_name == ann_field_name)
                and ann["value"] is not None
            ):
                if ann["type"].startswith("basic:{}:".format(field_type)):
                    put_in_download_list(ann["value"], ann_field_name)
                elif ann["type"].startswith("list:basic:{}:".format(field_type)):
                    for element in ann["value"]:
                        put_in_download_list(element, ann_field_name)

        return download_list

    def _get_dir_files(self, dir_name):
        files_list, dir_list = [], []

        dir_url = urljoin(self.resolwe.url, "data/{}/{}".format(self.id, dir_name))
        if not dir_url.endswith("/"):
            dir_url += "/"
        response = self.resolwe.session.get(dir_url, auth=self.resolwe.auth)
        response = json.loads(response.content.decode("utf-8"))

        for obj in response:
            obj_path = "{}/{}".format(dir_name, obj["name"])
            if obj["type"] == "directory":
                dir_list.append(obj_path)
            else:
                files_list.append(obj_path)

        if dir_list:
            for new_dir in dir_list:
                files_list.extend(self._get_dir_files(new_dir))

        return files_list

    @assert_object_exists
    def files(self, file_name=None, field_name=None):
        """Get list of downloadable file fields.

        Filter files by file name or output field.

        :param file_name: name of file
        :type file_name: string
        :param field_name: output field name
        :type field_name: string
        :rtype: List of tuples (data_id, file_name, field_name, process_type)

        """
        file_list = self._files_dirs("file", file_name, field_name)

        for dir_name in self._files_dirs("dir", file_name, field_name):
            file_list.extend(self._get_dir_files(dir_name))

        return file_list

    def download(
        self, file_name=None, field_name=None, download_dir=None, custom_file_name=None
    ):
        """Download Data object's files and directories.

        Download files and directories from the Resolwe server to the
        download directory (defaults to the current working directory).

        :param file_name: name of file or directory
        :type file_name: string
        :param field_name: file or directory field name
        :type field_name: string
        :param download_dir: download path
        :type download_dir: string
        :param custom_file_name: custom file name
        :type custom_file_name: string
        :rtype: None

        Data objects can contain multiple files and directories. All are
        downloaded by default, but may be filtered by name or output
        field:

        * re.data.get(42).download(file_name='alignment7.bam')
        * re.data.get(42).download(field_name='bam')

        """
        if file_name and field_name:
            raise ValueError("Only one of file_name or field_name may be given.")

        files = [
            "{}/{}".format(self.id, fname)
            for fname in self.files(file_name, field_name)
        ]

        # Only applies if downloading a single file
        custom_file_names = None
        if custom_file_name:
            if file_name or field_name:
                custom_file_names = [custom_file_name] * len(files)
            else:
                raise ValueError(
                    "Setting a custom file name is not supported "
                    "without specifying file name or field name."
                )

        self.resolwe._download_files(
            files=files, download_dir=download_dir, custom_file_names=custom_file_names
        )

    def stdout(self):
        """Return process standard output (stdout.txt file content).

        Fetch stdout.txt file from the corresponding Data object and return the
        file content as string. The string can be long and ugly.

        :rtype: string

        """
        if self.process.type.startswith("data:workflow"):
            raise ValueError("stdout.txt file is not available for workflows.")
        output = b""
        url = urljoin(self.resolwe.url, "data/{}/stdout.txt".format(self.id))
        response = self.resolwe.session.get(url, stream=True, auth=self.resolwe.auth)
        if not response.ok and self.status in ["UP", "RE", "WT", "PP", "DR"]:
            raise ValueError(
                f"stdout.txt file is not available for Data with status {self.status}"
            )
        if not response.ok:
            response.raise_for_status()
        else:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                output += chunk

        return output.decode("utf-8")

    @assert_object_exists
    def duplicate(self):
        """Duplicate (make copy of) ``data`` object.

        :return: Duplicated data object
        """
        task_data = self.api().duplicate.post({"ids": [self.id]})
        background_task = BackgroundTask(resolwe=self.resolwe, **task_data)
        return self.resolwe.data.get(id__in=background_task.result())
