"""Constants and abstract classes."""
from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import logging
import operator

import six

from .permissions import PermissionsManager


class BaseResource(object):
    """Abstract resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = None
    query_endpoint = None
    query_method = 'GET'

    WRITABLE_FIELDS = ()
    UPDATE_PROTECTED_FIELDS = ()
    READ_ONLY_FIELDS = ('id',)

    ALL_PERMISSIONS = []  # override this in subclass

    def __init__(self, resolwe, **model_data):
        """Verify that only a single attribute of slug, id or model_data given."""
        self._original_values = {}

        def initialize_field(field_name, value):
            """Initialize field and ignore those initialized in subclass."""
            if not hasattr(self, field_name):  # check if field was initialized in subclass
                setattr(self, field_name, value)

        for field_name in self.fields():
            initialize_field(field_name, None)

        #: unique identifier
        self.id = None  # pylint: disable=invalid-name

        self.api = operator.attrgetter(self.endpoint)(resolwe.api)
        self.resolwe = resolwe

        if model_data:
            self._update_fields(model_data)

        self.logger = logging.getLogger(__name__)

    def fields(self):
        """Resource fields."""
        return self.WRITABLE_FIELDS + self.UPDATE_PROTECTED_FIELDS + self.READ_ONLY_FIELDS

    def _update_fields(self, payload):
        """Update fields of the local resource based on the server values.

        :param dict payload: Resource field values

        """
        self._original_values = copy.deepcopy(payload)
        for field_name in self.fields():
            setattr(self, field_name, payload.get(field_name, None))

    def update(self):
        """Update resource fields from the server."""
        response = self.api(self.id).get()
        self._update_fields(response)

    def _dehydrate_resources(self, obj):
        """Iterate through object and replace all objects with their ids."""
        if isinstance(obj, BaseResource):
            return obj.id
        if isinstance(obj, list):
            return [self._dehydrate_resources(element) for element in obj]
        if isinstance(obj, dict):
            return {key: self._dehydrate_resources(value) for key, value in six.iteritems(obj)}
        return obj

    def save(self):
        """Save resource to the server."""
        def field_changed(field_name):
            """Check if local field value is different from the server."""
            return getattr(self, field_name) != self._original_values.get(field_name)

        def assert_fields_changed(field_names):
            """Check if local field value is different from the server."""
            changed_fields = [field_name for field_name in field_names if
                              field_changed(field_name)]

            if changed_fields:
                msg = "Not allowed to change read only fields {}".format(', '.join(changed_fields))
                raise ValueError(msg)

        if self.id:  # update resource
            assert_fields_changed(self.READ_ONLY_FIELDS + self.UPDATE_PROTECTED_FIELDS)

            payload = {}
            for field_name in self.WRITABLE_FIELDS:
                if field_changed(field_name):
                    payload[field_name] = self._dehydrate_resources(getattr(self, field_name))

            if payload:
                response = self.api(self.id).patch(payload)
                self._update_fields(response)

        else:  # create resource
            assert_fields_changed(self.READ_ONLY_FIELDS)

            field_names = self.WRITABLE_FIELDS + self.UPDATE_PROTECTED_FIELDS
            payload = {field_name: self._dehydrate_resources(getattr(self, field_name))
                       for field_name in field_names if getattr(self, field_name) is not None}

            response = self.api.post(payload)
            self._update_fields(response)

    def delete(self, force=False):
        """Delete the resource object from the server."""
        if force is not True:
            user_input = six.moves.input('Do you really want to delete {}?[yN] '.format(self))

            if user_input.strip().lower() != 'y':
                return

        self.api(self.id).delete()

    def __setattr__(self, name, value):
        """Detect changes of read only fields.

        This method detects changes of scalar fields and references. A
        more comprehensive check is called before save.

        """
        if (hasattr(self, '_original_values')
                and name in self._original_values
                and name in self.READ_ONLY_FIELDS
                and value != self._original_values[name]):
            raise ValueError("Can not change read only field {}".format(name))

        super(BaseResource, self).__setattr__(name, value)


class BaseResolweResource(BaseResource):
    """Base class for Resolwe resources.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    _permissions = None

    WRITABLE_FIELDS = ('slug', 'name')
    UPDATE_PROTECTED_FIELDS = ('contributor', )
    READ_ONLY_FIELDS = ('id', 'version', 'created', 'modified', 'current_user_permissions')

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        #: a descriptive name of the resource
        self.name = None
        #: the resource version
        self.version = None
        #: human-readable unique identifier
        self.slug = None
        #: user id of the contributor
        self.contributor = None
        #: date of creation
        self.created = None
        #: date of latest modification
        self.modified = None
        #: permissions - (view/download/add/edit/share/owner for user/group/public)
        self.current_user_permissions = None

        BaseResource.__init__(self, resolwe, **model_data)

    @property
    def permissions(self):
        """TODO."""
        if not self.id:
            raise ValueError('Instance must be saved before accessing `permissions` attribute.')
        if not self._permissions:
            self._permissions = PermissionsManager(
                self.ALL_PERMISSIONS,
                self.api(self.id),
                self.resolwe
            )

        return self._permissions

    def update(self):
        """Clear permissions cache and update the object."""
        self.permissions.clear_cache()

        super(BaseResolweResource, self).update()

    def __repr__(self):
        """Format resource name."""
        rep = "{} <id: {}, slug: '{}', name: '{}'>".format(
            self.__class__.__name__, self.id, self.slug, self.name
        )
        return rep.encode('utf-8') if six.PY2 else rep
