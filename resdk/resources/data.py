"""Data"""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import requests

from six.moves.urllib.parse import urljoin  # pylint: disable=import-error

from .utils import iterate_schema
from .base import BaseResource


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

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):

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

        #: process status - Possible values:
        #: Uploading(UP), Resolving(RE), Waiting(WT), Processing(PR), Done(OK), Error(ER), Dirty (DR)
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

        BaseResource.__init__(self, slug, id, model_data, resolwe)

        self.logger = logging.getLogger(__name__)

    def _update_fields(self, fields):
        """Update the Data object with new data.

        :param fields: Data resource fields
        :type fields: dict
        :rtype: None

        """
        BaseResource._update_fields(self, fields)

        self.annotation = {}
        self.annotation.update(
            self._flatten_field(fields['input'], fields['process_input_schema'], 'input'))

        self.annotation.update(
            self._flatten_field(fields['output'], fields['process_output_schema'], 'output'))

        # TODO Descriptor schema!

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

    def files(self, file_name=None, field_name=None):
        """Get list of downloadable fields.

        Filter files by file name or output field.

        :param file_name: name of file
        :type file_name: string
        :param field_name: output field name
        :type field_name: string
        :rtype: List of tuples (data_id, file_name, field_name, process_type)

        """
        download_list = []

        def put_in_download_list(elm, fname):
            """
            If ``file_name`` is not None append only files with equal name.
            """
            if 'file' in elm:
                if file_name is None or file_name == elm['file']:
                    download_list.append(elm['file'])
            else:
                raise KeyError("Item {} does not contain 'file' key.".format(fname))

        for ann_field_name, ann in self.annotation.items():
            if ann_field_name.startswith('output') and (field_name is None or field_name == ann_field_name):
                if ann['type'].startswith('basic:file:') and ann['value'] is not None:
                    put_in_download_list(ann['value'], ann_field_name)
                elif ann['type'].startswith('list:basic:file:') and ann['value'] is not None:
                    for element in ann['value']:
                        put_in_download_list(element, ann_field_name)

        return download_list

    def download(self, file_name=None, field_name=None, download_dir=None):
        """Download Data object's files.

        Download files from the Resolwe server to the download
        directory (defaults to the current working directory).

        :param file_name: name of file
        :type file_name: string
        :param field_name: file field name
        :type field_name: string
        :param download_dir: download path
        :type download_dir: string
        :rtype: None

        Data objects can contain multiple files. All are downloaded by
        default, but may be filtered by name or output field:

        * re.data.get(42).download(file_name='alignment7.bam')
        * re.data.get(42).download(field_name='bam')

        """
        if file_name and field_name:
            raise ValueError("Only one of file_name or field_name may be given.")

        files = ['{}/{}'.format(self.id, fname) for fname in self.files(file_name, field_name)]
        self.resolwe.download_files(files, download_dir)

    def print_annotation(self):
        """Provide annotation data."""
        # TODO: Think of neat way to present all annotation. how this would be most neatly presented...
        raise NotImplementedError()

    def stdout(self):
        """Return process standard output (stdout.txt file content).

        Fetch stdout.txt file from the corresponding Data object and return the
        file content as string. The string can be long and ugly.

        :rtype: string

        """
        output = ''
        url = urljoin(self.resolwe.url, 'data/{}/stdout.txt'.format(self.id))
        response = requests.get(url, stream=True, auth=self.resolwe.auth)
        if not response.ok:
            response.raise_for_status()
        else:
            for chunk in response.iter_content():
                output += chunk

        return output
