"""Constants and abstract classes."""

import copy
import logging
import operator

from ..constants import ALL_PERMISSIONS
from ..utils.decorators import assert_object_exists
from .permissions import PermissionsManager
from .utils import parse_resolwe_datetime


class BaseResource:
    """Abstract resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = None
    query_endpoint = None
    query_method = "GET"
    full_search_paramater = None
    delete_warning_single = "Do you really want to delete {}?[yN]"
    delete_warning_bulk = "Do you really want to delete {} objects?[yN]"

    READ_ONLY_FIELDS = ("id",)
    UPDATE_PROTECTED_FIELDS = ()
    WRITABLE_FIELDS = ()

    all_permissions = []  # override this in subclass

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self._original_values = {}

        self.api = operator.attrgetter(self.endpoint)(resolwe.api)
        self.resolwe = resolwe
        self.logger = logging.getLogger(__name__)

        #: unique identifier of an object
        self.id = None

        if model_data:
            self._update_fields(model_data)

    @classmethod
    def fetch_object(cls, resolwe, id=None, slug=None):
        """Return resource instance that is uniquely defined by identifier."""
        if (id is None and slug is None) or (id and slug):
            raise ValueError("One and only one of id or slug must be given")

        query = resolwe.get_query_by_resource(cls)
        if id:
            return query.get(id=id)
        return query.get(slug=slug)

    def fields(self):
        """Resource fields."""
        return (
            self.READ_ONLY_FIELDS + self.UPDATE_PROTECTED_FIELDS + self.WRITABLE_FIELDS
        )

    def _update_fields(self, payload):
        """Update fields of the local resource based on the server values."""
        self._original_values = copy.deepcopy(payload)
        for field_name in self.fields():
            setattr(self, field_name, payload.get(field_name, None))

    def update(self):
        """Update resource fields from the server."""
        response = self.api(self.id).get()
        self._update_fields(response)

    def _dehydrate_resources(self, obj):
        """Iterate through object and replace all objects with their ids."""
        # Prevent circular imports:
        from .descriptor import DescriptorSchema
        from .process import Process

        if isinstance(obj, DescriptorSchema) or isinstance(obj, Process):
            # Slug can only be given at create requests (id not present yet)
            if not self.id:
                return {"slug": obj.slug}

            return {"id": obj.id}
        if isinstance(obj, BaseResource):
            return {"id": obj.id}
        if isinstance(obj, list):
            return [self._dehydrate_resources(element) for element in obj]
        if isinstance(obj, dict):
            return {key: self._dehydrate_resources(value) for key, value in obj.items()}

        return obj

    def save(self):
        """Save resource to the server."""

        def field_changed(field_name):
            """Check if local field value is different from the server."""
            current_value = getattr(self, field_name, None)
            original_value = self._original_values.get(field_name, None)

            if isinstance(current_value, BaseResource) and original_value:
                # TODO: Check that current and original are instances of the same resource class
                return current_value.id != original_value.get("id", None)
            else:
                return current_value != original_value

        def assert_fields_unchanged(field_names):
            """Assert that fields in ``field_names`` were not changed."""
            changed_fields = [name for name in field_names if field_changed(name)]

            if changed_fields:
                msg = "Not allowed to change read only fields {}".format(
                    ", ".join(changed_fields)
                )
                raise ValueError(msg)

        if self.id:  # update resource
            assert_fields_unchanged(
                self.READ_ONLY_FIELDS + self.UPDATE_PROTECTED_FIELDS
            )

            payload = {}
            for field_name in self.WRITABLE_FIELDS:
                if field_changed(field_name):
                    payload[field_name] = self._dehydrate_resources(
                        getattr(self, field_name)
                    )
            if "sample" in payload:
                payload["entity"] = payload.pop("sample")

            if payload:
                response = self.api(self.id).patch(payload)
                self._update_fields(response)

        else:  # create resource
            assert_fields_unchanged(self.READ_ONLY_FIELDS)

            field_names = self.WRITABLE_FIELDS + self.UPDATE_PROTECTED_FIELDS
            payload = {
                field_name: self._dehydrate_resources(getattr(self, field_name))
                for field_name in field_names
                if getattr(self, field_name) is not None
            }

            if "sample" in payload:
                payload["entity"] = payload.pop("sample")

            from .annotations import AnnotationValue

            # Annotation models have primarykey serializer.
            if isinstance(self, AnnotationValue):
                payload["field"] = payload["field"]["id"]
                payload["entity"] = payload["entity"]["id"]

            response = self.api.post(payload)
            self._update_fields(response)

    def delete(self, force=False):
        """Delete the resource object from the server.

        :param bool force: Do not trigger confirmation prompt. WARNING: Be
            sure that you really know what you are doing as deleted objects
            are not recoverable.

        """
        if force is not True:
            user_input = input(self.delete_warning_single.format(self))

            if user_input.strip().lower() != "y":
                return

        response = self.api(self.id).delete()
        # This could either be True or a background task data.
        if response is not True:
            # Resolve circular import
            from .background_task import BackgroundTask

            BackgroundTask(resolwe=self.resolwe, **response).wait()
            return True

    def __setattr__(self, name, value):
        """Detect changes of read only fields.

        This method detects changes of scalar fields and references. A
        more comprehensive check is called before save.

        """
        if (
            hasattr(self, "_original_values")
            and name in self._original_values
            and name in self.READ_ONLY_FIELDS
            and value != self._original_values[name]
        ):
            raise ValueError("Can not change read only field {}".format(name))

        super().__setattr__(name, value)

    def __eq__(self, obj):
        """Evaluate if objects are the same."""
        if (
            self.__class__ == obj.__class__
            and self.resolwe.url == obj.resolwe.url
            and self.id == obj.id
        ):
            return True
        else:
            return False

    def _get_resourse(self, payload, resource):
        """Get ``resource`` from ``payload``."""
        if isinstance(payload, resource):
            return payload
        elif isinstance(payload, dict):
            return resource(resolwe=self.resolwe, **payload)
        elif isinstance(payload, int):
            return resource.fetch_object(self.resolwe, id=payload)
        elif isinstance(payload, str):
            return resource.fetch_object(self.resolwe, slug=payload)
        elif isinstance(payload, list):
            return [self._get_resourse(item, resource) for item in payload]
        return payload

    def _resource_setter(self, payload, resource, field):
        """Set ``resource`` with ``payload`` on ``field``."""
        setattr(self, field, self._get_resourse(payload, resource))


class BaseResolweResource(BaseResource):
    """Base class for Resolwe resources.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    _permissions = None

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "current_user_permissions",
        "id",
        "version",
    )
    WRITABLE_FIELDS = BaseResource.WRITABLE_FIELDS + (
        "name",
        "slug",
    )

    all_permissions = ALL_PERMISSIONS

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        #: User object of the contributor (lazy loaded)
        self._contributor = None
        #: current user permissions
        self.current_user_permissions = None
        #: name of resource
        self.name = None
        #: human-readable unique identifier
        self.slug = None
        #: resource version
        self.version = None

        BaseResource.__init__(self, resolwe, **model_data)

    @property
    @assert_object_exists
    def permissions(self):
        """Permissions."""
        if not self._permissions:
            self._permissions = PermissionsManager(
                self.all_permissions, self.api(self.id), self.resolwe
            )

        return self._permissions

    @property
    @assert_object_exists
    def contributor(self):
        """Contributor."""
        if self._contributor is None:
            contributor_data = self._original_values.get("contributor", {})
            try:
                self._contributor = self.resolwe.user.get(id=contributor_data.get("id"))
            except LookupError:
                from . import User

                # Normal user has only access to his user instance on user
                # endpoint. Instead of returning None for all other
                # contributors, data that is received in response is used to
                # populate User resource.
                self._contributor = User(
                    self.resolwe,
                    id=contributor_data.get("id"),
                    username=contributor_data.get("username"),
                    first_name=contributor_data.get("first_name"),
                    last_name=contributor_data.get("last_name"),
                )

        return self._contributor

    @property
    @assert_object_exists
    def created(self):
        """Creation time."""
        return parse_resolwe_datetime(self._original_values["created"])

    @property
    @assert_object_exists
    def modified(self):
        """Modification time."""
        return parse_resolwe_datetime(self._original_values["modified"])

    def update(self):
        """Clear permissions cache and update the object."""
        self.permissions.clear_cache()

        super().update()

    def __repr__(self):
        """Format resource name."""
        return "{} <id: {}, slug: '{}', name: '{}'>".format(
            self.__class__.__name__, self.id, self.slug, self.name
        )
