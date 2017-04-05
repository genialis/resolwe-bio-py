"""
Unit tests for resdk/resolwe.py file.
"""
# pylint: disable=missing-docstring, protected-access

import unittest

import six
import slumber
from mock import MagicMock, call, patch

from resdk.resources import Collection
from resdk.resources.base import BaseResource


class TestBaseResource(unittest.TestCase):

    @patch('resdk.resolwe.Resolwe')
    def setUp(self, resolwe_mock):  # pylint: disable=arguments-differ
        self.resolwe_mock = resolwe_mock

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_not_only_one_input(self, base_mock):
        message = "Only one of slug, id or model_data allowed"
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, slug="a", resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, model_data={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug="a", model_data={'a': 1},
                                  resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, slug="a", model_data={'a': 1},
                                  resolwe=self.resolwe_mock)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_wrong_type_input(self, base_mock):
        message = r"\w+ should be a\w? \w+."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id="bad_type_id", resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug={'a': 1}, resolwe=self.resolwe_mock)
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, model_data="a", resolwe=self.resolwe_mock)

    @patch('operator.attrgetter')
    def test_field_constraints(self, attrgetter_mock):
        base_resource = BaseResource(resolwe=self.resolwe_mock)

        base_resource.WRITABLE_FIELDS = ('writable_scalar', )
        base_resource.READ_ONLY_FIELDS = ('read_only_scalar', )
        base_resource._original_values = {'writable_scalar': None, 'read_only_scalar': None}
        base_resource.writable_scalar = None
        base_resource.read_only_scalar = None

        message = 'Can not change read only field read_only_scalar'
        with six.assertRaisesRegex(self, ValueError, message):
            base_resource.read_only_scalar = 42

        base_resource.writable_scalar = '42'
        self.assertEqual(base_resource.writable_scalar, '42')

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_id_http_error(self, base_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        base_mock._update_fields.side_effect = slumber.exceptions.HttpNotFoundError
        message = r"ID '\d+' does not exist or you do not have access permission."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_id_ok(self, base_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_slug_value_error(self, base_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        message = r"Slug '\w+' does not exist or you do not have access permission."
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_not_called()

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_slug_ok(self, base_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        self.resolwe_mock.configure_mock(**{'api.resource_endpoint.get.return_value': [123]})
        BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_called_once_with(123)

        self.resolwe_mock.configure_mock(
            **{'api.resource_endpoint.get.return_value': [{'version': 1}, {'version': 2}]}
        )

        BaseResource.__init__(base_mock, slug="a", resolwe=self.resolwe_mock)
        self.assertEqual(base_mock._update_fields.call_count, 2)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_model_data(self, base_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        mdata = {'a': 1, 'b': 2}
        BaseResource.__init__(base_mock, model_data=mdata, resolwe=self.resolwe_mock)
        base_mock._update_fields.assert_called_once_with(mdata)

    @patch('resdk.resources.base.logging')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_init_all_ok(self, base_mock, log_mock):
        base_mock.configure_mock(endpoint='resource_endpoint')
        BaseResource.__init__(base_mock, id=1, resolwe=self.resolwe_mock)
        self.assertEqual(log_mock.getLogger.call_count, 1)

    @patch('operator.attrgetter')
    def test_fields(self, attrgetter_mock):
        base_resource = BaseResource(resolwe=self.resolwe_mock)
        base_resource.WRITABLE_FIELDS = ('writable', )
        base_resource.UPDATE_PROTECTED_FIELDS = ('update_protected', )
        base_resource.READ_ONLY_FIELDS = ('read_only', )
        self.assertEqual(base_resource.fields(), ('writable', 'update_protected', 'read_only'))

    def test_dehydrate_resources(self):
        # `Collection` is used because it is easier to use
        collection = Collection(id=100, resolwe=MagicMock())
        obj_1 = Collection(id=1, resolwe=MagicMock())
        obj_1.id = 1  # this is overriden when initialized

        self.assertEqual(collection._dehydrate_resources(obj_1), 1)
        self.assertEqual(collection._dehydrate_resources([obj_1]), [1])
        self.assertEqual(collection._dehydrate_resources({'key': obj_1}), {'key': 1})
        self.assertEqual(collection._dehydrate_resources({'key': [obj_1]}), {'key': [1]})


class TestBaseMethods(unittest.TestCase):

    @patch('resdk.resources.base.setattr')
    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_update_fields(self, base_mock, setattr_mock):
        fields = {'id': 1, 'slug': 'testobj'}
        base_mock.fields.return_value = ('id', 'slug')
        BaseResource._update_fields(base_mock, fields)
        setattr_mock.assert_has_calls([call(base_mock, 'id', 1),
                                       call(base_mock, 'slug', 'testobj')],
                                      any_order=True)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_update(self, base_mock):
        base_mock.configure_mock(api=MagicMock(), id=1)
        BaseResource.update(base_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_post(self, base_mock):
        base_mock.configure_mock(id=None, slug='test')
        base_mock.WRITABLE_FIELDS = ('slug', )
        base_mock.api = MagicMock(**{'post.return_value': {'id': 1, 'slug': 'test'}})
        BaseResource.save(base_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_post_read_only(self, base_mock):
        base_mock.configure_mock(id=None, slug='test', read_only_dict=None, _original_values={})
        base_mock.READ_ONLY_FIELDS = ('id', 'read_only_dict')
        base_mock.UPDATE_PROTECTED_FIELDS = ()
        base_mock.WRITABLE_FIELDS = ('slug', )
        base_mock.fields.return_value = ('id', 'slug', 'read_only_dict')

        base_mock.read_only_dict = {'change': 'change-not-allowed'}

        message = 'Not allowed to change read only fields read_only_dict'
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.save(base_mock)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_post_update_protected(self, base_mock):
        base_mock.configure_mock(id=None, slug='test', update_protected_dict=None,
                                 _original_values={})
        base_mock.READ_ONLY_FIELDS = ('id', )
        base_mock.UPDATE_PROTECTED_FIELDS = ('update_protected_dict', )
        base_mock.WRITABLE_FIELDS = ('slug', )
        base_mock.fields.return_value = ('id', 'slug', 'update_protected_dict')

        base_mock.update_protected_dict = {'create': 'create-allowed'}
        base_mock.api = MagicMock(**{'post.return_value': {
            'id': 1, 'slug': 'test', 'update_protected_dict': {'create': 'create-allowed'}}})

        BaseResource.save(base_mock)
        self.assertEqual(base_mock.update_protected_dict, {'create': 'create-allowed'})

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_post_client_error(self, base_mock):
        base_mock.configure_mock(id=None, slug='test')
        base_mock.api = MagicMock(**{'post.side_effect': slumber.exceptions.HttpClientError(
            message='', content='', response='')})

        with self.assertRaises(slumber.exceptions.HttpClientError):
            BaseResource.save(base_mock)
        self.assertEqual(base_mock._update_fields.call_count, 0)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_patch(self, base_mock):
        base_mock.configure_mock(id=1, slug='test', _original_values={'slug': 'test-old'})
        base_mock.WRITABLE_FIELDS = ('slug', )

        base_mock.api = MagicMock(**{'patch.return_value': {'id': 1, 'slug': 'test'}})
        BaseResource.save(base_mock)
        self.assertEqual(base_mock._update_fields.call_count, 1)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_patch_read_only(self, base_mock):
        base_mock.READ_ONLY_FIELDS = ('id', 'read_only_dict')
        base_mock.UPDATE_PROTECTED_FIELDS = ()
        base_mock.WRITABLE_FIELDS = ('slug', )
        base_mock.fields.return_value = ('id', 'slug', 'read_only_dict')
        read_only_dict = {}
        BaseResource._update_fields(base_mock, {'id': 1,
                                                'slug': 'test',
                                                'read_only_dict': read_only_dict})
        base_mock.read_only_dict['change'] = 'change-not-allowed'

        message = 'Not allowed to change read only fields read_only_dict'
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.save(base_mock)

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_save_patch_update_protect(self, base_mock):
        base_mock.READ_ONLY_FIELDS = ('id', )
        base_mock.UPDATE_PROTECTED_FIELDS = ('update_protected_dict', )
        base_mock.WRITABLE_FIELDS = ('slug', )
        base_mock.fields.return_value = ('id', 'slug', 'update_protected_dict')
        update_protected_dict = {}
        BaseResource._update_fields(base_mock, {'id': 1,
                                                'slug': 'test',
                                                'update_protected_dict': update_protected_dict})
        base_mock.update_protected_dict['change'] = 'change-not-allowed'

        message = 'Not allowed to change read only fields update_protected_dict'
        with six.assertRaisesRegex(self, ValueError, message):
            BaseResource.save(base_mock)

        base_mock.UPDATE_PROTECTED_FIELDS = ('id', 'update_protected_dict')

    @patch('resdk.resources.base.BaseResource', spec=True)
    def test_repr(self, base_mock):
        base_mock.configure_mock(id=1, slug='a', name='b')
        out = BaseResource.__repr__(base_mock)
        self.assertEqual(out, 'BaseResource <id: 1, slug: \'a\', name: \'b\'>')


if __name__ == '__main__':
    unittest.main()
