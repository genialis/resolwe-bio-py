"""Data resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging

import requests
from six.moves.urllib.parse import urljoin  # pylint: disable=import-error

from .base import BaseResource
from .utils import iterate_schema


class Data(BaseResource):
    """Resolwe Data resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param slug: Resource slug
    :type slug: str
    :param id: Resource ID
    :type id: int
    :param model_data: Resource model data
    :type model_data: dict
    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object

    """

    endpoint = 'data'

    #: (lazy loaded) annotated ``Sample`` to which ``Data`` object belongs
    _sample = None
    #: (lazy loaded) list of collections to which data object belongs
    _collections = None

    WRITABLE_FIELDS = ('descriptor_schema', 'descriptor', 'tags') + BaseResource.WRITABLE_FIELDS
    UPDATE_PROTECTED_FIELDS = ('input', 'process') + BaseResource.UPDATE_PROTECTED_FIELDS
    READ_ONLY_FIELDS = ('process_input_schema', 'process_output_schema', 'output', 'started',
                        'finished', 'checksum', 'status', 'process_progress', 'process_rc',
                        'process_info', 'process_warning', 'process_error', 'process_type',
                        'process_name') + BaseResource.READ_ONLY_FIELDS

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):
        """Initialize attributes."""
        #: specification of inputs
        self.process_input_schema = None
        #: actual input values
        self.input = None
        #: specification of outputs
        self.process_output_schema = None
        #: actual output values
        self.output = None
        #: the id of used descriptor schema
        self.descriptor_schema = None
        #: annotation data, with the form defined in descriptor_schema
        self.descriptor = None
        #: The ID of the process used in this data object
        self.process = None
        #: start time of the process in data object
        self.started = None
        #: finish time of the process in data object
        self.finished = None
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

        super(Data, self).__init__(slug, id, model_data, resolwe)

        self.logger = logging.getLogger(__name__)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._sample = None
        self._collections = None

        super(Data, self).update()

    def _update_fields(self, payload):
        """Update the Data object with new data.

        :param dict payload: Data resource fields
        :rtype: None

        """
        BaseResource._update_fields(self, payload)

        self.annotation = {}
        self.annotation.update(
            self._flatten_field(payload['input'], payload['process_input_schema'], 'input'))

        self.annotation.update(
            self._flatten_field(payload['output'], payload['process_output_schema'], 'output'))

        # TODO: Descriptor schema!

    def _flatten_field(self, field, schema, path):
        """Reduce dicts of dicts to dot separated keys.

        :param field: Field instance (e.g. input)
        :type field: dict
        :param schema: Schema instance (e.g. input_schema)
        :type schema: dict
        :param path: Field path
        :type path: string
        :return: flattened annotations
        :rtype: dictionary

        """
        flat = {}
        for field_schema, fields, path in iterate_schema(field, schema, path):
            name = field_schema['name']
            typ = field_schema['type']
            label = field_schema['label']
            value = fields[name] if name in fields else None
            flat[path] = {'name': name, 'value': value, 'type': typ, 'label': label}

        return flat

    @property
    def collections(self):
        """Return list of collections to which data object belongs."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `collections` attribute.')
        if self._collections is None:
            self._collections = self.resolwe.collection.filter(data=self.id)

        return self._collections

    @property
    def sample(self):
        """Get ``sample`` that object belongs to."""
        if self.id is None:
            raise ValueError('Instance must be saved before accessing `sample` attribute.')
        if self._sample is None:
            self._sample = self.resolwe.sample.filter(data=self.id)
            self._sample = self._sample[0] if self._sample else None
        return self._sample

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

        for ann_field_name, ann in self.annotation.items():
            if (ann_field_name.startswith('output') and
                    (field_name is None or field_name == ann_field_name) and
                    ann['value'] is not None):
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
            print('>>', self._get_dir_files)
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

    def print_annotation(self):
        """Provide annotation data."""
        # TODO: Think of a good way to present all annotation
        raise NotImplementedError()

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
            for chunk in response.iter_content():
                output += chunk

        return output.decode("utf-8")
