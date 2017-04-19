"""
Unit tests for resdk/query.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest
from collections import defaultdict

from mock import MagicMock

from resdk.query import ResolweQuery


class TestResolweQuery(unittest.TestCase):

    def test_init(self):
        resolwe = MagicMock()
        resource = MagicMock(endpoint='resolwe_endpoint', query_endpoint=None, query_method='GET')

        query = ResolweQuery(resolwe, resource, 'endpoint')
        self.assertEqual(query.resolwe, resolwe)
        self.assertEqual(query.resource, resource)
        self.assertEqual(query.endpoint, 'endpoint')

        query = ResolweQuery(resolwe, resource)
        self.assertEqual(query.resolwe, resolwe)
        self.assertEqual(query.resource, resource)
        self.assertEqual(query.endpoint, 'resolwe_endpoint')

        resource = MagicMock(endpoint='resolwe_endpoint', query_endpoint='query_endpoint',
                             query_method='GET')

        query = ResolweQuery(resolwe, resource, 'endpoint')
        self.assertEqual(query.resolwe, resolwe)
        self.assertEqual(query.resource, resource)
        self.assertEqual(query.endpoint, 'endpoint')

        query = ResolweQuery(resolwe, resource)
        self.assertEqual(query.resolwe, resolwe)
        self.assertEqual(query.resource, resource)
        self.assertEqual(query.endpoint, 'query_endpoint')

    def test_getitem_invalid(self):
        query = MagicMock(spec=ResolweQuery)

        # negative index
        with self.assertRaises(ValueError):
            ResolweQuery.__getitem__(query, -5)

        # negative start
        with self.assertRaises(ValueError):
            ResolweQuery.__getitem__(query, slice(-2, None))

        # negative stop
        with self.assertRaises(ValueError):
            ResolweQuery.__getitem__(query, slice(-1))

        # negative step
        with self.assertRaises(ValueError):
            ResolweQuery.__getitem__(query, slice(1, 5, 2))

    def test_getitem_cached(self):
        query = MagicMock(spec=ResolweQuery, _cache=[1, 2, 3], _limit=None, _offset=None)
        result = ResolweQuery.__getitem__(query, 1)
        self.assertEqual(result, 2)

        result = ResolweQuery.__getitem__(query, slice(2))
        self.assertEqual(result, [1, 2])

        # make sure that offset and limit are not set
        self.assertEqual(query._limit, None)
        self.assertEqual(query._offset, None)

    def test_getitem(self):
        new_query = MagicMock(spec=ResolweQuery)
        query = MagicMock(spec=ResolweQuery, _cache=None, _limit=None, _offset=None,
                          **{'_clone.return_value': new_query})
        ResolweQuery.__getitem__(query, slice(1, 3))
        self.assertEqual(new_query._offset, 1)
        self.assertEqual(new_query._limit, 2)

        new_query.__iter__.return_value = [5]
        result = ResolweQuery.__getitem__(query, 1)
        self.assertEqual(result, 5)
        self.assertEqual(new_query._offset, 1)
        self.assertEqual(new_query._limit, 1)

        new_query.__iter__.return_value = []
        with self.assertRaises(IndexError):
            ResolweQuery.__getitem__(query, 1)

    def test_iter(self):
        query = MagicMock(spec=ResolweQuery, _cache=[1, 2, 3])

        result = ResolweQuery.__iter__(query)
        self.assertTrue(hasattr(result, '__iter__'))  # is iterator
        self.assertEqual(list(result), [1, 2, 3])

    def test_repr(self):
        query = MagicMock(spec=ResolweQuery, _cache=[1, 2, 3])

        rep = ResolweQuery.__repr__(query)
        self.assertEqual(rep, '[1,\n 2,\n 3]')

    def test_len(self):
        query = MagicMock(spec=ResolweQuery, **{'count.return_value': 3})
        query.__len__ = ResolweQuery.__len__

        self.assertEqual(len(query), 3)

    def test_clone(self):
        query = MagicMock(spec=ResolweQuery, _cache=[1, 2, 3], _filters=defaultdict(list),
                          _limit=2, _offset=3, endpoint='endpoint')

        new_query = ResolweQuery._clone(query)
        self.assertEqual(new_query._cache, None)  # cache shouldnt be copied
        self.assertEqual(new_query._filters, {})
        self.assertEqual(new_query._limit, 2)
        self.assertEqual(new_query._offset, 3)

        # check that filters are not linked - deep copy
        new_query._filters['id'] = 1
        self.assertNotEqual(query._filters, new_query._filters)

    def test_add_filter(self):
        query = MagicMock(spec=ResolweQuery, _filters=defaultdict(list, {'slug': ['test']}))
        query.resource.query_method = 'GET'
        ResolweQuery._add_filter(query, {'id': 1})
        self.assertEqual(dict(query._filters), {'slug': ['test'], 'id': [1]})

        query = MagicMock(spec=ResolweQuery, _filters={'slug': 'test'})
        query.resource.query_method = 'POST'
        ResolweQuery._add_filter(query, {'id': 1})
        self.assertEqual(query._filters, {'slug': 'test', 'id': 1})

    def test_compose_filters(self):
        query = MagicMock(spec=ResolweQuery)

        query.configure_mock(_filters={'id': 42, 'type': 'data'}, _limit=None, _offset=None)
        filters = ResolweQuery._compose_filters(query)
        self.assertEqual(filters, {'id': 42, 'type': 'data'})

        query.configure_mock(_filters={'id': 42, 'type': 'data'}, _limit=5, _offset=2)
        filters = ResolweQuery._compose_filters(query)
        self.assertEqual(filters, {'id': 42, 'type': 'data', 'limit': 5, 'offset': 2})

    def test_fetch(self):
        query = MagicMock(spec=ResolweQuery)
        query._cache = None
        query.api.get = MagicMock(return_value=['object 1', 'object 2'])
        query._populate_resource = MagicMock(side_effect=['object 1', 'object 2'])
        query.resource.query_method = 'GET'

        ResolweQuery._fetch(query)
        self.assertEqual(query._cache, ['object 1', 'object 2'])
        self.assertEqual(query._populate_resource.call_count, 2)

        # test cached
        query.reset_mock()
        query._cache = ['object 1', 'object 2']
        ResolweQuery._fetch(query)
        self.assertEqual(query._populate_resource.call_count, 0)

    def test_clear_cache(self):
        query = MagicMock(spec=ResolweQuery, _cache=['obj1', 'obj2'])
        ResolweQuery.clear_cache(query)
        self.assertEqual(query._cache, None)

    def test_count(self):
        count_query = MagicMock(spec=ResolweQuery, _count=10)
        query = MagicMock(spec=ResolweQuery, _count=None, _limit=None, _offset=None,
                          **{'_clone.return_value': count_query})

        self.assertEqual(ResolweQuery.count(query), 10)

        query._limit = 2
        query._offset = 0
        self.assertEqual(ResolweQuery.count(query), 2)

        query._limit = 2
        query._offset = 9
        self.assertEqual(ResolweQuery.count(query), 1)

        query._limit = 2
        query._offset = 12
        self.assertEqual(ResolweQuery.count(query), 0)

        query._count = 5
        query._limit = None
        query._offset = None
        self.assertEqual(ResolweQuery.count(query), 5)

    def test_get(self):
        new_query = MagicMock(spec=ResolweQuery)
        query = MagicMock(spec=ResolweQuery, **{'_clone.return_value': new_query})

        with self.assertRaises(ValueError):
            ResolweQuery.get(query, 1, 'slug')

        with self.assertRaises(ValueError):
            ResolweQuery.get(query, 1, name='Object name')

        new_query.__iter__.return_value = ['object']
        result = ResolweQuery.get(query, 1)
        self.assertEqual(result, 'object')

        new_query.__iter__.return_value = []
        with self.assertRaises(LookupError):
            ResolweQuery.get(query, 1)

        new_query.__iter__.return_value = ['object 1', 'object 2']
        with self.assertRaises(LookupError):
            ResolweQuery.get(query, 1)

    def test_post(self):
        query = MagicMock(spec=ResolweQuery)

        ResolweQuery.post(query, {'id': 2, 'name': 'Test object'})
        query.api.post.assert_called_once_with({'id': 2, 'name': 'Test object'})

    def test_filter(self):
        new_query = MagicMock(spec=ResolweQuery)
        query = MagicMock(spec=ResolweQuery, **{'_clone.return_value': new_query})

        result = ResolweQuery.filter(query, id=2)
        result._add_filter.assert_called_once_with({'id': 2})  # pylint: disable=no-member
        # make sure that original hasnt changed
        self.assertEqual(query._add_filter.call_count, 0)

    def test_all(self):
        new_query = MagicMock(spec=ResolweQuery)
        query = MagicMock(spec=ResolweQuery, **{'_clone.return_value': new_query})

        result = ResolweQuery.all(query)
        self.assertEqual(result, new_query)

    def test_search(self):
        query = MagicMock(spec=ResolweQuery)

        with self.assertRaises(NotImplementedError):
            ResolweQuery.search(query)


if __name__ == '__main__':
    unittest.main()
