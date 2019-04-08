# pylint: disable=missing-docstring
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.tests.functional.base import BaseResdkFunctionalTest


class TestDataUsage(BaseResdkFunctionalTest):

    expected_fields = {
        'user_id',
        'username',
        'full_name',
        'data_size',
        'data_size_normalized',
        'data_count',
        'data_count_normalized',
        'sample_count',
        'sample_count_normalized',
        'collection_count',
        'collection_count_normalized',
    }

    def test_normal_user(self):
        usage_info = self.user_res.data_usage()
        self.assertEqual(len(usage_info), 1)
        self.assertEqual(set(usage_info[0].keys()), self.expected_fields)

    def test_admin_user(self):
        usage_info = self.res.data_usage()
        self.assertGreaterEqual(len(usage_info), 2)
        self.assertEqual(set(usage_info[0].keys()), self.expected_fields)

    def test_ordering(self):
        usage_info = self.res.data_usage(ordering=['full_name', '-data_size'])
        self.assertGreaterEqual(len(usage_info), 2)
        first = usage_info[0]
        second = usage_info[1]
        self.assertEqual(first['full_name'], second['full_name'])
        self.assertGreaterEqual(first['data_size'], second['data_size'])
