"""
Unit tests for resdk/exceptions.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest

import six
from mock import MagicMock
from slumber.exceptions import SlumberHttpBaseException

from resdk.exceptions import ResolweServerError, handle_http_exception


class ExceptionsTestCase(unittest.TestCase):
    def test_handle_http_exception(self):
        func = MagicMock()
        wrapped = handle_http_exception(func)

        func.return_value = 42
        self.assertEqual(wrapped(40, 2, operation='add'), 42)
        func.assert_called_once_with(40, 2, operation='add')

        func.side_effect = SlumberHttpBaseException(content='error message')
        with six.assertRaisesRegex(self, ResolweServerError, 'error message'):
            wrapped()
