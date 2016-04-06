"""Collection"""
from __future__ import absolute_import, division, print_function, unicode_literals


class Collection(object):

    """Resolwe collection annotation."""

    def __init__(self, ann_data, resolwe):
        """
        Resolwe collection annotation.

        :param ann_data: Collection annotation - (field, value) pairs
        :type ann_data: dictionary
        :param resolwe: Resolwe instance
        :type resolwe: Resolwe object
        :rtype: None

        """

        for field in ann_data:
            setattr(self, field, ann_data[field])

        self.resolwe = resolwe
        self.id = getattr(self, 'id', None)
        self.name = getattr(self, 'name', None)

    def data_types(self):
        """
        Return a list of data types.

        :rtype: List
        """
        data = self.resolwe.project_data(self.id)
        return sorted(set(d.type for d in data))

    # TODO
    def data(self, **query):
        """Query for Data object annotation."""
        data = self.resolwe.project_data(self.id)
        query['case_ids__contains'] = self.id
        ids = set(d['id'] for d in self.resolwe.api.dataid.get(**query)['objects'])
        return [d for d in data if d.id in ids]

    # TODO
    def find(self, filter_str):
        """Filter Data object annotation."""
        raise NotImplementedError()

    def __str__(self):
        return self.name or 'n/a'

    def __repr__(self):
        return u"Collection: {} - {}".format(self.id, self.name)
