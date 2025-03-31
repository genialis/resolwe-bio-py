"""Constants and abstract classes."""

import copy
import logging
import operator
from typing import TYPE_CHECKING, Any, Iterable, Optional

from ..constants import ALL_PERMISSIONS
from ..utils.decorators import assert_object_exists
from .fields import (
    BaseField,
    DataSource,
    DateTimeField,
    DictResourceField,
    FieldAccessType,
    IntegerField,
    StringField,
)
from .permissions import PermissionsManager

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class BaseResource:
    """Abstract resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint: Optional[str] = None
    query_endpoint: Optional[str] = None
    query_method = "GET"
    full_search_paramater: Optional[str] = None
    delete_warning_single = "Do you really want to delete {}?[yN]"
    delete_warning_bulk = "Do you really want to delete {} objects?[yN]"

    id = IntegerField()

    all_permissions = []  # override this in subclass

    def __init__(
        self,
        resolwe: "Resolwe",
        initial_data_source: DataSource = DataSource.USER,
        **model_data: dict,
    ):
        """Initialize attributes."""
        self._resource_fields = self._find_fields()
        self._original_values = {}
        self.api = operator.attrgetter(self.endpoint)(resolwe.api)
        self.resolwe = resolwe
        self.logger = logging.getLogger(__name__)

        if model_data:
            self._update_fields(model_data, data_source=initial_data_source)

    @classmethod
    def _find_fields(cls: type["BaseResource"]) -> dict:
        """Find all fields in the class."""
        fields = {
            variable_name: variable_value
            for _class in cls.__mro__
            for variable_name, variable_value in vars(_class).items()
            if isinstance(variable_value, BaseField)
        }
        # Make sure id field is first when iterating the dict of fields.
        if "id" in fields:
            fields = {"id": fields.pop("id")} | fields
        return fields

    def _get_fields(
        self, access_types: Iterable[FieldAccessType]
    ) -> dict[str, BaseField]:
        """Return fields with given access type."""
        return {
            field_name: field
            for field_name, field in self._resource_fields.items()
            if field._access_type in access_types
        }

    def _get_required_fields(self) -> dict[str, BaseField]:
        """Return required fields."""
        return {
            field_name: field
            for field_name, field in self._resource_fields.items()
            if field.required
        }

    @classmethod
    def fetch_object(
        cls: type["BaseResource"],
        resolwe: "Resolwe",
        id: Optional[int] = None,
        slug: Optional[str] = None,
    ) -> "BaseResource":
        """Return resource instance that is uniquely defined by identifier."""
        if (id is None and slug is None) or (id and slug):
            raise ValueError("One and only one of id or slug must be given")

        query = resolwe.get_query_by_resource(cls)
        if id:
            return query.get(id=id)
        return query.get(slug=slug)

    def _check_required_fields(self, payload: dict[str, Any]):
        """Check if all required fields are present in the payload.

        :raise ValueError: If any required field is missing.
        """
        required_fields = self._get_required_fields()
        for field in required_fields.values():
            if field.server_field not in payload:
                raise ValueError(
                    f"Required field '{field.server_field}' not in payload."
                )

    def _map_user_to_server_fields(self, payload: dict[str, Any]):
        """Map user fields to server fields.

        The payload dictionary is modified in place.
        """
        for original, destination in {
            field_name: field.server_field
            for field_name, field in self._resource_fields.items()
            if field_name != field.server_field
        }.items():
            if original in payload:
                payload[destination] = payload.pop(original)

    def _update_fields(
        self, payload: dict[str, Any], data_source: DataSource = DataSource.USER
    ):
        """Update fields of the local resource based on the server values."""
        try:
            # Set the loading data to indicate read-only fields can be set.
            self._initial_data_source = data_source
            if data_source == DataSource.USER:
                self._map_user_to_server_fields(payload)
            self._check_required_fields(payload)
            self._original_values = copy.deepcopy(payload)

            # Reset all the field values.
            for field in self._resource_fields.values():
                field.reset(self)

            for field_name, field in self._resource_fields.items():
                # Only set fields that are present in the payload.
                if field.server_field not in payload:
                    continue
                payload_value = payload.get(field.server_field)
                if data_source == DataSource.SERVER:
                    field._set_server(self, payload_value)
                else:
                    setattr(self, field_name, field.to_python(payload_value, self))
        finally:
            self._initial_data_source = DataSource.USER

    def update(self):
        """Update resource fields from the server."""
        self._update_fields(self.api(self.id).get(), data_source=DataSource.SERVER)

    def save(self):
        """Save resource to the server."""

        def assert_fields_unchanged(fields: Iterable[BaseField]):
            """Assert that fields in ``field_names`` were not changed."""
            if changed := [str(field) for field in fields if field.changed(self)]:
                raise ValueError(f"Not allowed to change fields {', '.join(changed)}")

        updating = self.id is not None
        if updating:
            assert_unchanged = (
                FieldAccessType.READ_ONLY,
                FieldAccessType.UPDATE_PROTECTED,
            )
            to_payload = (FieldAccessType.WRITABLE,)
            api_call = self.api(self.id).patch
        else:
            assert_unchanged = (FieldAccessType.READ_ONLY,)
            to_payload = (FieldAccessType.WRITABLE, FieldAccessType.UPDATE_PROTECTED)
            api_call = self.api(self.id).post

        assert_fields_unchanged(self._get_fields(assert_unchanged).values())

        if payload := {
            field.server_field: field.to_json(getattr(self, field_name))
            for field_name, field in self._get_fields(to_payload).items()
            if field.changed(self)
        }:
            self._update_fields(api_call(payload), data_source=DataSource.SERVER)

    def __hash__(self):
        """Get the hash."""
        return getattr(self, "id", None)

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

            BackgroundTask(
                resolwe=self.resolwe, **response, initial_data_source=DataSource.SERVER
            ).wait()
            return True

    def __eq__(self, obj: Any) -> bool:
        """Evaluate if objects are the same.

        Two object are considered the same if they are located on the same server, are
        instances of the same resource class and have the same id.
        """
        return (
            self.__class__ == obj.__class__
            and self.resolwe.url == obj.resolwe.url
            and self.id == obj.id
        )


class BaseResolweResource(BaseResource):
    """Base class for Resolwe resources.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    _permissions: Optional[PermissionsManager] = None

    current_user_permissions = BaseField()
    contributor = DictResourceField(resource_class_name="User")
    version = BaseField()
    name = StringField(access_type=FieldAccessType.WRITABLE)
    slug = StringField(access_type=FieldAccessType.WRITABLE)
    created = DateTimeField()
    modified = DateTimeField()
    all_permissions = ALL_PERMISSIONS

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        BaseResource.__init__(self, resolwe, **model_data)
        self.logger = logging.getLogger(__name__)

    @property
    @assert_object_exists
    def permissions(self) -> PermissionsManager:
        """Permissions."""
        if not self._permissions:
            self._permissions = PermissionsManager(
                self.all_permissions, self.api(self.id), self.resolwe
            )

        return self._permissions

    def update(self):
        """Clear permissions cache and update the object."""
        self.permissions.clear_cache()
        super().update()

    def __repr__(self) -> str:
        """Format resource name."""
        return "{} <id: {}, slug: '{}', name: '{}'>".format(
            self.__class__.__name__, self.id, self.slug, self.name
        )
