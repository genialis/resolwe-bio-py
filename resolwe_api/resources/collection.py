"""Collection"""
from __future__ import absolute_import, division, print_function, unicode_literals

from .base import BaseResource
from .data import Data


class BaseCollection(BaseResource):
    """
    Abstract class BaseCollection.
    """

    def __init__(self, collection_data, resolwe):
        """
        Abstract class BaseResource.
        """
        BaseResource.__init__(self, collection_data, resolwe)

    def data_types(self):
        """
        Return a list of data types (process_type).

        :rtype: List
        """
        return sorted(  # pylint: disable=no-member
            set(self.resolwe.api.data(id_).get()['process_type'] for id_ in self.data))  # pylint: disable=no-member

    def files(self, verbose=False):
        """
        Return list of files in resource.
        """
        file_list = []
        for id_ in self.data:  # pylint: disable=no-member
            file_list += Data(self.resolwe.api.data(id_).get(), self.resolwe).get_download_list(verbose=verbose)
        return file_list

    def print_annotation(self):
        """
        Provide annotation data.
        """
        raise NotImplementedError()


class Collection(BaseCollection):
    """Resolwe collection annotation."""

    endpoint = 'collection'

    """Resolwe collection annotation."""

    def __init__(self, collection_data, resolwe):
        """
        Resolwe collection annotation.

        :param collection_data: Annotation data for Collection
        :type collection_data: dictionary (JSON from restAPI)
        :param resolwe: Resolwe instance
        :type resolwe: Resolwe object
        :rtype: None

        """
        BaseCollection.__init__(self, collection_data, resolwe)

    def print_annotation(self):
        """
        Provide annotation data.
        """
        raise NotImplementedError()
