"""Collection resources."""

import logging
from urllib.parse import urljoin

from resdk.shortcuts.collection import CollectionRelationsMixin

from ..utils.decorators import assert_object_exists
from .background_task import BackgroundTask
from .base import BaseResolweResource
from .descriptor import DescriptorSchema
from .utils import _get_billing_account_id


class BaseCollection(BaseResolweResource):
    """Abstract collection resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    full_search_paramater = "text"
    delete_warning_single = (
        "Do you really want to delete {} and all of it's content?[yN]"
    )
    delete_warning_bulk = (
        "Do you really want to delete {} objects and all of their content?[yN]"
    )

    READ_ONLY_FIELDS = BaseResolweResource.READ_ONLY_FIELDS + (
        "descriptor_dirty",
        "duplicated",
    )
    WRITABLE_FIELDS = BaseResolweResource.WRITABLE_FIELDS + (
        "description",
        "descriptor",
        "descriptor_schema",
        "settings",
        "tags",
    )

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: list of Data objects in collection (lazy loaded)
        self._data = None
        #: ``DescriptorSchema`` of a resource object (lazy loaded)
        self._descriptor_schema = None

        #: description
        self.description = None
        #: descriptor
        self.descriptor = None
        #: descriptor_dirty
        self.descriptor_dirty = None
        #: duplicatied
        self.duplicated = None
        #: settings
        self.settings = None
        #: tags
        self.tags = None

        super().__init__(resolwe, **model_data)

    @property
    def data(self):
        """Return list of attached Data objects."""
        raise NotImplementedError("This should be implemented in subclass")

    @property
    def descriptor_schema(self):
        """Descriptor schema."""
        return self._descriptor_schema

    @descriptor_schema.setter
    def descriptor_schema(self, payload):
        """Set descriptor schema."""
        self._resource_setter(payload, DescriptorSchema, "_descriptor_schema")

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._data = None
        self._descriptor_schema = None

        super().update()

    def data_types(self):
        """Return a list of data types (process_type).

        :rtype: List

        """
        return sorted({datum.process.type for datum in self.data})

    def files(self, file_name=None, field_name=None):
        """Return list of files in resource."""
        file_list = []
        for data in self.data:
            file_list.extend(
                fname
                for fname in data.files(file_name=file_name, field_name=field_name)
            )

        return file_list

    def download(self, file_name=None, field_name=None, download_dir=None):
        """Download output files of associated Data objects.

        Download files from the Resolwe server to the download
        directory (defaults to the current working directory).

        :param file_name: name of file
        :type file_name: string
        :param field_name: field name
        :type field_name: string
        :param download_dir: download path
        :type download_dir: string
        :rtype: None

        Collections can contain multiple Data objects and Data objects
        can contain multiple files. All files are downloaded by default,
        but may be filtered by file name or Data object type:

        * re.collection.get(42).download(file_name='alignment7.bam')
        * re.collection.get(42).download(data_type='bam')

        """
        files = []

        if field_name and not isinstance(field_name, str):
            raise ValueError("Invalid argument value `field_name`.")

        for data in self.data:
            data_files = data.files(file_name, field_name)
            files.extend("{}/{}".format(data.id, file_name) for file_name in data_files)

        self.resolwe._download_files(files=files, download_dir=download_dir)


class Collection(CollectionRelationsMixin, BaseCollection):
    """Resolwe Collection resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "collection"

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: list of ``Sample`` objects in ``Collection`` (lazy loaded)
        self._samples = None
        #: list of ``Relation`` objects in ``Collection`` (lazy loaded)
        self._relations = None

        super().__init__(resolwe, **model_data)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._samples = None
        self._relations = None

        super().update()

    @property
    @assert_object_exists
    def data(self):
        """Return list of data objects on collection."""
        if self._data is None:
            self._data = self.resolwe.data.filter(collection=self.id)

        return self._data

    @property
    @assert_object_exists
    def samples(self):
        """Return list of samples on collection."""
        if self._samples is None:
            self._samples = self.resolwe.sample.filter(collection=self.id)

        return self._samples

    @property
    @assert_object_exists
    def relations(self):
        """Return list of data objects on collection."""
        if self._relations is None:
            self._relations = self.resolwe.relation.filter(collection=self.id)

        return self._relations

    @assert_object_exists
    def duplicate(self):
        """Duplicate (make copy of) ``collection`` object.

        :return: Duplicated collection
        """
        task_data = self.api().duplicate.post({"ids": [self.id]})
        background_task = BackgroundTask(resolwe=self.resolwe, **task_data)
        return self.resolwe.collection.get(id__in=background_task.result())

    @assert_object_exists
    def assign_to_billing_account(self, billing_account_name):
        """Assign given collection to a billing account."""
        billing_account_id = _get_billing_account_id(self.resolwe, billing_account_name)

        # Assign collection to a billing account
        response = self.resolwe.session.post(
            urljoin(
                self.resolwe.url, f"api/billingaccount/{billing_account_id}/collection"
            ),
            data={"collection_id": self.id},
        )
        response.raise_for_status()
