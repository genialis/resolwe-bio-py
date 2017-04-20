""".. Ignore pydocstyle D400.

=============
Resolwe Query
=============

.. autoclass:: resdk.ResolweQuery
   :members:

"""
from __future__ import absolute_import, division, print_function

import collections
import copy
import logging
import operator

import six


class ResolweQuery(object):
    """Query resource endpoints.

    A Resolwe instance (for example "res") has several endpoints:
    res.data, res.collections, res.sample and res.process. Each
    endpoint is an instance of the ResolweQuery class. ResolweQuery
    supports queries on corresponding objects, for example:

    .. code-block:: python

        res.data.get(42)  # return Data object with ID 42.
        res.sample.filter(contributor=1)  # return all samples made by contributor 1

    This object is lazy loaded which means that actual is made only
    when needed. This enables composing multiple filters, for example:

    .. code-block:: python

        res.data.filter(contributor=1).filter(name='My object')

    is the same as:

    .. code-block:: python

        res.data.filter(contributor=1, name='My object')

    This is especially useful, because all endpoints at Resolwe instance
    are such queries and can be filtered further before transferring
    any data.

    Filters can be made with the following keywords (and operators)

        * Fields (and operators) for **data** endpoint:

            * slug (=, __in=)
            * contributor (=)
            * status (=, __in=)
            * name (=, __in=, __startswith, endswith=)
            * created (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * modified (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * input (=)
            * descriptor (=)
            * started (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * finished (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * output (=)
            * process (=)
            * process_name (=, __in=, __startswith=)
            * type (=)
            * collection (=, __in=)

        * Fields (and operators) for **collection** and **sample** endpoint:
            * contributor (=)
            * name (=, __in=, __startswith=)
            * description (=)
            * created (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * modified (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * slug (=, __in=)
            * descriptor (=)
            * data (=, __in=)
            * descriptor_schema (=)
            * id (=, __in=)

        * Fields (and operators) for **process** endpoint:
            * contributor (=)
            * name (=, __in=, __startswith=)
            * created (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * modified (=, __gte, __gt=, __lte=, __lt=, __year__gte=,
              __month__gte=,...)
            * slug (=, __in=)
            * id (=, __in=)

    Example usage:

    .. code-block:: python

        # Get a list of data objects with status set to OK.
        res.data.filter(status='OK')

        # Get a list of sample objects that contain data object 42 and
        # were contributed by contributor with ID 1

        res.collection.filter(data=42, contributor=1)

    """

    _cache = None
    _count = None  # number of objects in current query (without applied limit and offset)
    _limit = None
    _offset = None
    _filters = collections.defaultdict(list)

    resolwe = None
    resource = None
    endpoint = None
    api = None
    logger = None

    def __init__(self, resolwe, resource, endpoint=None):
        """Initialize attributes."""
        self.resolwe = resolwe
        self.resource = resource

        # Determine the endpoint to use.
        if endpoint is not None:
            self.endpoint = endpoint
        elif resource.query_endpoint is not None:
            self.endpoint = resource.query_endpoint
        else:
            self.endpoint = resource.endpoint

        self.api = operator.attrgetter(self.endpoint)(resolwe.api)
        self.logger = logging.getLogger(__name__)

    def __getitem__(self, index):
        """Retrieve an item or slice from the set of results."""
        # pylint: disable=protected-access
        if not isinstance(index, (slice,) + six.integer_types):
            raise TypeError
        if ((not isinstance(index, slice) and index < 0) or
                (isinstance(index, slice) and index.start is not None and index.start < 0) or
                (isinstance(index, slice) and index.stop is not None and index.stop < 0)):
            raise ValueError("Negative indexing is not supported.")
        if isinstance(index, slice) and index.step is not None:
            raise ValueError("`step` parameter in slice is not supported")

        if self._cache is not None:
            return self._cache[index]

        new_query = self._clone()

        if isinstance(index, slice):
            if self._offset or self._limit:
                raise NotImplementedError('You cannot slice already sliced query.')

            start = 0 if index.start is None else int(index.start)
            stop = 1000000 if index.stop is None else int(index.stop)  # default to something big
            new_query._offset = start
            new_query._limit = stop - start
            return new_query

        new_query._offset = self._offset + index if self._offset else index
        new_query._limit = 1

        query_list = list(new_query)
        if not query_list:
            raise IndexError('list index out of range')
        return query_list[0]

    def __iter__(self):
        """Return iterator over the current object."""
        self._fetch()
        return iter(self._cache)

    def __repr__(self):
        """Return string representation of the current object."""
        self._fetch()
        return '[{}]'.format(',\n '.join(str(obj) for obj in self._cache))

    def __len__(self):
        """Return length of results of current query."""
        return self.count()

    def _clone(self):
        """Return copy of current object with empty cache."""
        # pylint: disable=protected-access
        new_obj = ResolweQuery(self.resolwe, self.resource, self.endpoint)
        new_obj._filters = copy.deepcopy(self._filters)
        new_obj._limit = self._limit
        new_obj._offset = self._offset
        return new_obj

    def _add_filter(self, filter_):
        """Add filter parameter."""
        for key, value in filter_.items():
            if self.resource.query_method == 'GET':
                self._filters[key].append(value)
            elif self.resource.query_method == 'POST':
                self._filters[key] = value
            else:
                raise NotImplementedError(
                    'Unsupported query_method: {}'.format(self.resource.query_method))

    def _compose_filters(self):
        """Convert filters to dict and add pagination filters."""
        filters = self._filters

        if self._limit is not None:
            filters['limit'] = self._limit
        if self._offset is not None:
            filters['offset'] = self._offset

        return dict(filters)

    def _populate_resource(self, data):
        """Populate resource with given data."""
        return self.resource(model_data=data, resolwe=self.resolwe)

    def _fetch(self):
        """Make request to the server and populate cache."""
        if self._cache is not None:
            return  # already fetched

        filters = self._compose_filters()
        if self.resource.query_method == 'GET':
            items = self.api.get(**filters)
        elif self.resource.query_method == 'POST':
            items = self.api.post(filters)
        else:
            raise NotImplementedError(
                'Unsupported query_method: {}'.format(self.resource.query_method))

        # Extract data from paginated response
        if isinstance(items, dict) and 'results' in items:
            self._count = items['count']
            items = items['results']

        self._cache = [self._populate_resource(data) for data in items]

    def clear_cache(self):
        """Clear cache."""
        self._cache = None
        self._count = None

    def count(self):
        """Return number of objects in current query."""
        # pylint: disable=protected-access
        if self._count is None:
            count_query = self._clone()
            count_query._offset = 0
            count_query._limit = 1
            count_query._fetch()
            self._count = count_query._count

        if self._limit is None:
            return self._count

        remaining = self._count - self._offset
        return max(0, min(self._limit, remaining))

    def get(self, *args, **kwargs):
        """Get object that matches given parameters.

        If only one non-keyworded argument is given, it is considered
        as id if it is number and as slug otherwise.

        :param uid: unique identifier - ID or slug
        :type uid: int for ID or string for slug

        :rtype: object of type self.resource

        :raises ValueError: if non-keyworded and keyworded arguments
            are combined or if more than one non-keyworded argument is
            given
        :raises LookupError: if none or more than one objects are
            returned

        """
        if args:
            if len(args) > 1:
                raise ValueError('Only one non-keyworded argument can be given')
            if kwargs:
                raise ValueError('Non-keyworded arguments cannot be combined with keyworded ones.')

            arg = args[0]
            kwargs = {'id': arg} if str(arg).isdigit() else {'slug': arg}

        new_query = self._clone()
        new_query._add_filter(kwargs)  # pylint: disable=protected-access

        response = list(new_query)

        if not response:
            raise LookupError('Matching object does not exist.')

        if len(response) > 1:
            raise LookupError('get() returned more than one object.')

        return response[0]

    def create(self, *args, **model_data):
        """Return new instance of current resource."""
        slug = model_data.pop('slug', None)
        id_ = model_data.pop('id', None)

        resource = self.resource(slug=slug, id=id_, model_data=model_data, resolwe=self.resolwe)
        resource.save()

        return resource

    def post(self, data):
        """Post data to this endpoint.

        :param dict data: Data dictionary to post
        """
        return self.api.post(data)  # pylint: disable=no-member

    def filter(self, **filters):
        """Return clone of current query with added given filters."""
        new_query = self._clone()
        new_query._add_filter(filters)  # pylint: disable=protected-access
        return new_query

    def delete(self, force=False):
        """Delete objects in current query."""
        if not force:
            user_input = six.moves.input(
                'Do you really want to delete {} object(s)?[yN] '.format(self.count()))
            if user_input.strip().lower() != 'y':
                return

        # TODO: Use bulk delete when supported on backend
        for obj in self:
            obj.delete(force=True)

        self.clear_cache()

    def all(self):
        """Return copy of the current queryset.

        This is handy function to get newly created query without any
        filters.
        """
        return self._clone()

    def search(self):
        """Full text search."""
        raise NotImplementedError()
