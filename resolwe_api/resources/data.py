"""Data"""
from __future__ import absolute_import, division, print_function, unicode_literals

from .utils import iterate_schema
from .base import BaseResource


class Data(BaseResource):
    """
    Resolwe data object annotation.
    """

    endpoint = 'data'

    """
    Resolwe data object annotation.
    """

    def __init__(self, data, resolwe):
        BaseResource.__init__(self, data, resolwe)

    def update(self, data):
        """
        Update the Data object with new data.

        :param data: Annotation data for Data object
        :type collection: dictionary (JSON that is received from restAPI)

        :rtype: None
        """
        BaseResource.update(self, data)

        self.annotation = {}
        self.annotation.update(
            self._flatten_field(data['input'], data['process_input_schema'], 'input'))
        self.annotation.update(
            self._flatten_field(data['output'], data['process_output_schema'], 'output'))
        # TODO Descriptor schema!

    def _flatten_field(self, field, schema, path):
        """
        Reduce dicts of dicts to dot separated keys.

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

    def get_download_list(self, verbose=False):
        """
        Get list of all downloadable fields

        :param verbose: Verbose output.
        :type verbose: boolean

        If verbose = False, return list of strings (file names)
        If verbose = True, return list of tuples. Each tuple contains:
        (data_id, file_name, field_name, process_type)
        """
        dlist = []
        for path, ann in self.annotation.items():
            if path.startswith('output') and ann['type'] == 'basic:file:':
                if verbose:
                    dlist.append((self.id,
                                  ann['value']['file'],
                                  path, self.process_type))  # pylint: disable=no-member
                else:
                    dlist.append(ann['value']['file'])
        return dlist

    def files(self, verbose=False):
        """
        Return list of files in resource.
        """
        # to ne bo ok za data!
        file_list = self.resolwe.data.get(self.id).get_download_list(verbose=verbose)  # pylint: disable=no-member
        return file_list

    def print_annotation(self):
        """
        Provide annotation data.
        """
        # TODO: Think of neat way to present all annotation. how this would be most neatly presented...
        raise NotImplementedError()
