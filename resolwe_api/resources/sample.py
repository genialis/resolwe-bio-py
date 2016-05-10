"""Sample"""
from __future__ import absolute_import, division, print_function, unicode_literals

from .collection import BaseCollection


class Sample(BaseCollection):
    """
    Resolwe sample annotation.
    """

    endpoint = 'sample'

    def __init__(self, sample_data, resolwe):
        """
        Resolwe sample annotation.

        :param ann_data: Annotation data for Sample
        :type ann_data: dictionary (JSON from restAPI)
        :param resolwe: Resolwe instance
        :type resolwe: Resolwe

        :rtype: None
        """
        BaseCollection.__init__(self, sample_data, resolwe)

    def print_annotation(self):
        """
        Provide annotation data.
        """
        raise NotImplementedError()
