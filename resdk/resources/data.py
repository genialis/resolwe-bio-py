"""Data resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging

import requests
import six
from six.moves.urllib.parse import urljoin  # pylint: disable=wrong-import-order

from resdk.constants import CHUNK_SIZE

from .base import BaseResolweResource
from .descriptor import DescriptorSchema
from .utils import (
    flatten_field, get_descriptor_schema_id, is_descriptor_schema, parse_resolwe_datetime,
)


class Data(BaseResolweResource):
    """Resolwe Data resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = 'data'
    full_search_paramater = 'text'

    READ_ONLY_FIELDS = BaseResolweResource.READ_ONLY_FIELDS + (
        'checksum', 'descriptor_dirty', 'process_cores', 'process_error', 'process_info',
        'process_input_schema', 'process_memory', 'process_name', 'process_output_schema',
        'process_progress', 'process_rc', 'process_slug', 'process_type', 'process_warning',
        'output', 'size', 'status',
    )
    UPDATE_PROTECTED_FIELDS = BaseResolweResource.UPDATE_PROTECTED_FIELDS + (
        'input', 'process',
    )
    WRITABLE_FIELDS = BaseResolweResource.WRITABLE_FIELDS + (
        'descriptor', 'descriptor_schema', 'tags',
    )

    ALL_PERMISSIONS = ['view', 'download', 'edit', 'share', 'owner']

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: list of ``Collection``s that contain ``Data`` (lazy loaded)
        self._collections = None
        #: ``DescriptorSchema`` id of ``Data`` object
        self._descriptor_schema = None
        #: ``DescriptorSchema`` of ``Data`` object
        self._hydrated_descriptor_schema = None
        #: ``Sample`` containing ``Data`` object (lazy loaded)
        self._sample = None
        #: ``ResolweQuery`` containing parent ``Data`` objects (lazy loaded)
        self._parents = None
        #: ``ResolweQuery`` containing child ``Data`` objects (lazy loaded)
        self._children = None

        #: specification of inputs
        self.process_input_schema = None
        #: actual input values
        self.input = None
        #: specification of outputs
        self.process_output_schema = None
        #: actual output values
        self.output = None
        #: annotation data, with the form defined in descriptor_schema
        self.descriptor = None
        #: The ID of the process used in this data object
        self.process = None
        #: checksum field calculated on inputs
        self.checksum = None
        #: process status - Possible values: Uploading(UP), Resolving(RE),
        #: Waiting(WT), Processing(PR), Done(OK), Error(ER), Dirty (DR)
        self.status = None
        #: process progress in percentage
        self.process_progress = None
        #: Process algorithm return code
        self.process_rc = None
        #: info log message (list of strings)
        self.process_info = None
        #: warning log message (list of strings)
        self.process_warning = None
        #: error log message (list of strings)
        self.process_error = None
        #: what kind of output does process produce
        self.process_type = None
        #: process name
        self.process_name = None
        #: data object's tags
        self.tags = None
        #: indicate whether `descriptor` doesn't match `descriptor_schema` (is dirty)
        self.descriptor_dirty = None
        #: process slug
        self.process_slug = None
        #: process cores
        self.process_cores = None
        #: process memory
        self.process_memory = None
        #: size
        self.size = None

        super(Data, self).__init__(resolwe, **model_data)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._sample = None
        self._collections = None
        self._hydrated_descriptor_schema = None
        self._parents = None
        self._children = None

        super(Data, self).update()

    @property
    def collections(self):
        """Get list of collections to which data object belongs."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `collections` attribute.')

        if self._collections is None:
            # self._collections is set to False. This enables distinction between:
            # (a) self._collections is None since self.collections was never accessed
            # (b) self._collections is False since data object is not in any collection
            self._collections = False

            # Note: ``collections`` field will only be present on single data
            # object endpoint (e.g. /api/data/<ID>), but not on list endpoint
            # (e.g. /api/data?id=<ID>). Therefore, explicit call on ``self.api``
            # is made instead of self.reslwe.data.get (which makes request on
            # list view but requires that list of results is of length 1)
            payload = self.api(self.id).get()

            if payload['collections']:
                self._collections = self.resolwe.collection.filter(id__in=payload['collections'])

        return self._collections

    @property
    def sample(self):
        """Get ``sample`` that object belongs to."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `sample` attribute.')
        if self._sample is None:
            # self._sample is set to False. This enables distinction between:
            # (a) self._sample is None since self.sample was never accessed
            # (b) self._sample is False since data object is not in any sample
            self._sample = False

            # Note: ``entities`` field will only be present on single data
            # object endpoint (e.g. /api/data/<ID>), but not on list endpoint
            # (e.g. /api/data?id=<ID>). Therefore, explicit call on ``self.api``
            # is made instead of self.reslwe.data.get (which makes request on
            # list view but requires that list of results is of length 1)
            payload = self.api(self.id).get()

            if payload['entities']:
                self._sample = self.resolwe.sample.get(id=payload['entities'][0])

        if self._sample:
            return self._sample

    @property
    def descriptor_schema(self):
        """Return descriptor schema assigned to the data object."""
        if self._descriptor_schema is None:
            return None

        if self._hydrated_descriptor_schema is None:
            if isinstance(self._descriptor_schema, int):
                query_filters = {'id': self._descriptor_schema}
            else:
                query_filters = {'slug': self._descriptor_schema}

            self._hydrated_descriptor_schema = self.resolwe.descriptor_schema.get(
                ordering='-version', limit=1, **query_filters
            )

        return self._hydrated_descriptor_schema

    @descriptor_schema.setter
    def descriptor_schema(self, dschema):
        """Set collection to which relation belongs."""
        # On single data object endpoint descriptor schema is already
        # hidrated, so it should be transformed into resource.
        if isinstance(dschema, dict):
            dschema = DescriptorSchema(resolwe=self.resolwe, **dschema)

        self._descriptor_schema = get_descriptor_schema_id(dschema)
        # Save descriptor schema if already hydrated, otherwise it will be rerived in getter
        self._hydrated_descriptor_schema = dschema if is_descriptor_schema(dschema) else None

    @property
    def started(self):
        """Start time."""
        if not self.id:
            raise ValueError('Instance must be saved before acessing `started` attribute.')
        return parse_resolwe_datetime(self._original_values['started'])

    @property
    def finished(self):
        """Finish time."""
        if not self.id:
            raise ValueError('Instance must be saved before acessing `finished` attribute.')
        return parse_resolwe_datetime(self._original_values['finished'])

    @property
    def parents(self):
        """Get parents of this Data object."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `parents` attribute.')
        if self._parents is None:
            self._parents = self.resolwe.data.filter(children=self.id)

        return self._parents

    @property
    def children(self):
        """Get children of this Data object."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `children` attribute.')
        if self._children is None:
            self._children = self.resolwe.data.filter(parents=self.id)

        return self._children

    def _files_dirs(self, field_type, file_name=None, field_name=None):
        """Get list of downloadable fields."""
        download_list = []

        def put_in_download_list(elm, fname):
            """Append only files od dirs with equal name."""
            if field_type in elm:
                if file_name is None or file_name == elm[field_type]:
                    download_list.append(elm[field_type])
            else:
                raise KeyError("Item {} does not contain '{}' key.".format(fname, field_type))

        if field_name and not field_name.startswith('output.'):
            field_name = 'output.{}'.format(field_name)

        flattened = flatten_field(self.output, self.process_output_schema, 'output')
        for ann_field_name, ann in six.iteritems(flattened):
            if (ann_field_name.startswith('output')
                    and (field_name is None or field_name == ann_field_name)
                    and ann['value'] is not None):
                if ann['type'].startswith('basic:{}:'.format(field_type)):
                    put_in_download_list(ann['value'], ann_field_name)
                elif ann['type'].startswith('list:basic:{}:'.format(field_type)):
                    for element in ann['value']:
                        put_in_download_list(element, ann_field_name)

        return download_list

    def _get_dir_files(self, dir_name):
        files_list, dir_list = [], []

        dir_url = urljoin(self.resolwe.url, 'data/{}/{}'.format(self.id, dir_name))
        if not dir_url.endswith('/'):
            dir_url += '/'
        response = requests.get(dir_url, auth=self.resolwe.auth)
        response = json.loads(response.content.decode('utf-8'))

        for obj in response:
            obj_path = '{}/{}'.format(dir_name, obj['name'])
            if obj['type'] == 'directory':
                dir_list.append(obj_path)
            else:
                files_list.append(obj_path)

        if dir_list:
            for new_dir in dir_list:
                files_list.extend(self._get_dir_files(new_dir))

        return files_list

    def files(self, file_name=None, field_name=None):
        """Get list of downloadable file fields.

        Filter files by file name or output field.

        :param file_name: name of file
        :type file_name: string
        :param field_name: output field name
        :type field_name: string
        :rtype: List of tuples (data_id, file_name, field_name, process_type)

        """
        if not self.id:
            raise ValueError('Instance must be saved before using `files` method.')

        file_list = self._files_dirs('file', file_name, field_name)

        for dir_name in self._files_dirs('dir', file_name, field_name):
            file_list.extend(self._get_dir_files(dir_name))

        return file_list

    def download(self, file_name=None, field_name=None, download_dir=None):
        """Download Data object's files and directories.

        Download files and directoriesfrom the Resolwe server to the
        download directory (defaults to the current working directory).

        :param file_name: name of file or directory
        :type file_name: string
        :param field_name: file or directory field name
        :type field_name: string
        :param download_dir: download path
        :type download_dir: string
        :rtype: None

        Data objects can contain multiple files and directories. All are
        downloaded by default, but may be filtered by name or output
        field:

        * re.data.get(42).download(file_name='alignment7.bam')
        * re.data.get(42).download(field_name='bam')

        """
        if file_name and field_name:
            raise ValueError("Only one of file_name or field_name may be given.")

        files = ['{}/{}'.format(self.id, fname) for fname in self.files(file_name, field_name)]
        self.resolwe._download_files(files, download_dir)  # pylint: disable=protected-access

    def stdout(self):
        """Return process standard output (stdout.txt file content).

        Fetch stdout.txt file from the corresponding Data object and return the
        file content as string. The string can be long and ugly.

        :rtype: string

        """
        output = b''
        url = urljoin(self.resolwe.url, 'data/{}/stdout.txt'.format(self.id))
        response = requests.get(url, stream=True, auth=self.resolwe.auth)
        if not response.ok:
            response.raise_for_status()
        else:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                output += chunk

        return output.decode("utf-8")
