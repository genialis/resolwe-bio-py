"""
Unit tests for resdk/resolwe.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest

import six
import slumber

from mock import patch, MagicMock, call

from resdk.resources.base import BaseResource


class TestBaseResource(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe')
    def setUp(self, resolwe_mock):  # pylint: disable=arguments-differ
        resolwe_mock.configure_mock(api="something")
        self.resolwe_mock = resolwe_mock

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_not_only_one_input(self, base_mock):
        message = "One and only one of slug, id or model_data must be given"
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, slug="a", resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, model_data={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug="a", model_data={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, slug="a", model_data={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, resolwe=self.resolwe_mock)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_wrong_type_input(self, base_mock):
        message = r"\w+ should be a\w? \w+."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id="bad_type_id", resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, model_data="a", resolwe=self.resolwe_mock)

    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_id_http_error(self, base_mock, getattr_mock):
        base_mock._update_fields.side_effect = slumber.exceptions.HttpNotFoundError
        message = r"ID '\d+' does not exist or you do not have access permission."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)

    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_id_ok(self, base_mock, getattr_mock):
        BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_slug_value_error(self, base_mock, getattr_mock):
        base_mock.configure_mock(endpoint="this_is_string")
        getattr_mock.return_value = MagicMock(**{'get.return_value': []})
        message = r"Slug '\w+' does not exist or you do not have access permission."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_not_called()

    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_slug_ok(self, base_mock, getattr_mock):
        base_mock.configure_mock(endpoint="this_is_string")
        getattr_mock.return_value = MagicMock(**{'get.return_value': [123]})
        BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_called_once_with(123)

        getattr_mock.return_value = MagicMock(**{'get.return_value': [{'version': 1}, {'version': 2}]})
        BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        self.assertEqual(base_mock._update_fields.call_count, 2)

    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_model_data(self, base_mock, getattr_mock):
        mdata = {'a': 1, 'b': 2}
        BaseResource.__init__(base_mock, model_data=mdata, resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_called_once_with(mdata)

    @patch('resdk.resources.base.logging')
    @patch('resdk.resources.base.getattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_init_all_ok(self, base_mock, getattr_mock, log_mock):
        BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)
        self.assertEqual(log_mock.getLogger.call_count, 1)


class TestOtherStuff(unittest.TestCase):

    @patch('resdk.resources.base.setattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_update_fields(self, base_mock, setattr_mock):
        fields = {'a': 1, 'b': 2}
        BaseResource._update_fields(base_mock, fields)
        setattr_mock.assert_has_calls([call(base_mock, 'a', 1), call(base_mock, 'b', 2)], any_order=True)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_update(self, base_mock):
        base_mock.configure_mock(api=MagicMock(), id=1)
        BaseResource.update(base_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_repr(self, base_mock):
        base_mock.configure_mock(id=1, slug="a", name="b")
        out = BaseResource.__repr__(base_mock)
        self.assertEqual(out, "BaseResource <id: 1, slug: 'a', name: 'b'>")


if __name__ == '__main__':
    unittest.main()
