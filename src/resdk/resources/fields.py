"""Fields used in resources."""

import copy
import importlib
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from resdk.resources.base import BaseResource


class DataSource(Enum):
    """The origin of the data."""

    USER = auto()
    SERVER = auto()


class FieldAccessType(Enum):
    """Field access types."""

    READ_ONLY = auto()
    UPDATE_PROTECTED = auto()
    WRITABLE = auto()


class FieldStatus(Enum):
    """Field status."""

    UNSET = auto()
    SET = auto()
    LAZY = auto()


class BaseField:
    """Class representing a base field."""

    def __init__(
        self,
        access_type=FieldAccessType.READ_ONLY,
        required=False,
        server_field_name=None,
        assert_exists=False,
        allow_null=True,
        initial_loader=None,
        many=False,
        accepted_types=None,
    ):
        """Initialize the instance.

        :attr access_type: access type of the field.
        :attr required: a boolean indicating the field is required.
        :attr server_field_name: sometimes a field name in the API is different from the
            public field name.
        :attr assert_exists: a boolean indicating if the instance must exist before
            accessing the field.
        :attr allow_null: a boolean indication if None value is allowed.
        :attr many: a boolean indicating if the field represents a single value or a
            list of values.
        :
        """
        self._access_type = access_type
        # Sometimes the public field name and the name used in the API are different.
        # This field is used to indicate how the value must be serialized.
        self._server_field_name = server_field_name
        self._assert_exists = assert_exists
        self._many = many
        self.required = required
        self._allow_null = allow_null
        self._initial_loader = initial_loader
        self._accepted_types = accepted_types
        super().__init__()

    def __set_name__(self, owner: type["BaseResource"], name: str):
        """Store the public name and set attribute names."""
        self.public_name = name
        self._owner = owner
        self._value_attribute_name = f"_{name}"
        self._original_attribute_name = f"{self._value_attribute_name}_original"
        self._status_attribute_name = f"{self._value_attribute_name}_status"

    def _check_exists(self, instance: "BaseResource"):
        """Check if the instance exists when assert_exists is set.

        :raises ValueError: if the instance is not yet saved.
        """
        if self._assert_exists and instance.id is None:
            raise ValueError(
                "Instance must be saved before accessing attribute "
                f"'{self.public_name}'."
            )

    def _check_writeable(self, instance: "BaseResource"):
        """Check if the value can be saved to instance.

        The value can be set to the read-only and update-protected field only once.

        :raises AttributeError: if the field is read-only or update-protected.
        """
        created = instance.id is not None
        from_server = (
            getattr(instance, "_initial_data_source", DataSource.USER)
            == DataSource.SERVER
        )
        skip = from_server

        if not skip:
            if self._access_type == FieldAccessType.READ_ONLY:
                raise AttributeError(f"Field {self.public_name} is read only.")

            if self._access_type == FieldAccessType.UPDATE_PROTECTED and created:
                raise AttributeError(f"Field {self.public_name} is update protected.")

    def _check_many(self, value, instance):
        """Check that the many attribute is respected.

        :raises AssertionError: the value is not list and many attribute is set.
        """
        from resdk.query import ResolweQuery

        if self._many and value is not None:
            if not isinstance(value, (list, ResolweQuery)):
                raise ValueError(
                    (
                        f"Type of '{instance.__class__.__name__}.{self.public_name}' "
                        f"must be list."
                    )
                )

    def _check_allow_null(self, value):
        """Check if the value is allowed to be None.

        :raises ValueError: if the value is None and allow_null is False.
        """
        if not self._allow_null and value is None:
            raise ValueError(f"Field {self.public_name} does not allow None value.")

    def _checks_before_get(self, instance: "BaseResource"):
        """Perform all checks before getting the value."""
        self._check_exists(instance)

    def _check_types(self, value, instance):
        """Check the type of the value."""
        if self._accepted_types is None or value is None:
            return

        for item in value if self._many else [value]:
            if not isinstance(item, self._accepted_types):
                types = f"{', '.join(_type.__name__ for _type in self._accepted_types)}"
                many = "a list of " if self._many else ""
                raise ValueError(
                    (
                        f"Type of '{instance.__class__.__name__}.{self.public_name}' "
                        f"must be {many}'{types}'."
                    )
                )

    def _checks_before_set(self, instance: "BaseResource", value):
        """Perform all checks before setting the value."""
        self._check_exists(instance)
        self._check_many(value, instance)
        self._check_writeable(instance)
        self._check_allow_null(value)
        self._check_types(value, instance)

    def _is_lazy(self, value) -> bool:
        """Check if the value must be lazy loaded."""
        # from resdk.query import ResolweQuery
        # return isinstance(value, ResolweQuery) or callable(value)
        return callable(value)

    def _lazy_load(self, value):
        """Perform the lazy loading of the field value.

        If the value is not lazy-loadable return it unchanged.
        """
        return value if not self._is_lazy(value) else value()

    def status(self, instance: "BaseResource") -> FieldStatus:
        """Return the field status."""
        if not hasattr(instance, self._status_attribute_name):
            setattr(instance, self._status_attribute_name, FieldStatus.UNSET)
        return getattr(instance, self._status_attribute_name)

    def changed(self, instance: "BaseResource"):
        """Check if the field value has changed."""
        # If the instance is not yet created, all writable and update-protected fields
        # must be considered changed.
        status = self.status(instance)
        creating = instance.id is None
        lazy = status == FieldStatus.LAZY

        # Read only and unset and lazy fields are not considered changed.
        # Lazy status can only be set by the API-originating data.
        if status == FieldStatus.UNSET or lazy:
            return False

        # When creating instance all writable and update-protected fields are changed.
        access_types = (FieldAccessType.WRITABLE, FieldAccessType.UPDATE_PROTECTED)
        if creating and self._access_type in access_types:
            return True

        # We have to deal with the instance that is already created.
        # This means data has been loaded from the server so original data is set.
        # To determine if field has been changed compare the original and current value.

        original_json = getattr(instance, self._original_attribute_name)
        current_python = getattr(instance, self._value_attribute_name)
        return self._compare(original_json, current_python)

    def _compare(self, original_json, current_python):
        """Compare the original JSON and current Python value."""
        return original_json != current_python

    def reset(self, instance: "BaseResource"):
        """Reset the field value."""
        status = FieldStatus.UNSET
        value = None
        setattr(instance, self._value_attribute_name, value)
        setattr(instance, self._original_attribute_name, value)
        setattr(instance, self._status_attribute_name, status)

    @property
    def server_field(self):
        """The name of the field used in the API."""
        return self._server_field_name or self.public_name

    def _to_json_single(self, value):
        """Serialize the single value."""
        return value

    def _to_python_single(self, value, instance=None):
        """Deserialize the single value."""
        return value

    def to_json(self, value):
        """Return the JSON serializable value."""
        if value is None:
            return None
        if self._many:
            return [self._to_json_single(item) for item in value]
        else:
            return self._to_json_single(value)

    def to_python(self, value, instance):
        """Return the Python object from JSON value."""
        if value is None:
            return None
        if self._many:
            self._check_many(value, instance)
            return [self._to_python_single(item, instance) for item in value]
        else:
            return self._to_python_single(value, instance)

    def __get__(
        self, instance: "BaseResource", owner: Optional[type["BaseResource"]] = None
    ):
        """Get the field value."""
        # When initial_loader is set and the field is not set, load the initial value.
        if (
            self.status(instance) == FieldStatus.UNSET
            and self._initial_loader
            and instance.id is not None
        ):
            value = self._initial_loader(instance)
            setattr(instance, self._value_attribute_name, value)
            setattr(instance, self._status_attribute_name, FieldStatus.LAZY)

        self._checks_before_get(instance)
        if self.status(instance) == FieldStatus.LAZY:
            value = getattr(instance, self._value_attribute_name)
            original = getattr(instance, self._original_attribute_name)
            data = self._lazy_load(value)
            if original == value:
                setattr(instance, self._original_attribute_name, data)
            setattr(instance, self._value_attribute_name, data)
            setattr(instance, self._status_attribute_name, FieldStatus.SET)

        return getattr(instance, self._value_attribute_name, None)

    def _set_server(self, instance: "BaseResource", json_data: dict):
        """Set the data from the server."""
        self.reset(instance)
        setattr(instance, self._original_attribute_name, copy.deepcopy(json_data))
        value = self.to_python(json_data, instance)
        self.__set__(instance, value)

    def __set__(self, instance: "BaseResource", value):
        """Set the field value to Python object."""
        self._checks_before_set(instance, value)
        setattr(instance, self._value_attribute_name, value)
        status = FieldStatus.LAZY if self._is_lazy(value) else FieldStatus.SET
        setattr(instance, self._status_attribute_name, status)

    def __repr__(self) -> str:
        """Returt the string representation."""
        return f"<{self.__class__.__name__} {self.public_name}>"

    def __str__(self) -> str:
        """Return the field name."""
        return self.public_name


class IntegerField(BaseField):
    """The integer field.

    Adds additional check that the value is an integer.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(int,))


class DateTimeField(BaseField):
    """The datetime objects are serialized to/from iso format."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(datetime,))

    def _to_json_single(self, value, resolwe=None):
        """Serialize the given field value."""
        return value.isoformat()

    def _to_python_single(self, value, instance=None):
        """Deserialize the given field value."""
        return datetime.fromisoformat(value)

    def _compare(self, original_json, current_python):
        """Compare the original JSON and current Python value."""
        return self.to_python(original_json) != current_python


class StringField(BaseField):
    """The string field."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(str,))


class DictField(BaseField):
    """The dictionary field."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(dict,))


class FloatField(BaseField):
    """The float field."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(float,))


class BooleanField(BaseField):
    """The boolean field."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs, accepted_types=(bool,))


class DictResourceField(BaseField):
    """Class representing a dictionary field with resources."""

    def __init__(self, resource_class_name: str, property_name: str = "id", **kwargs):
        """Initialize the instance.

        :attr resource_class: a string representing the resource class.
        :attr property_name: a string representing the property name of the resource to
            use in serialization.
        :attr many: a boolean indicating if the field represents a single resource or a
            list of resources.
        """
        self._resource_class_name = resource_class_name
        self._resource_class = None
        self._property_name = property_name
        super().__init__(**kwargs)

    @property
    def Resource(self):
        """Return the resource class."""

        from resdk.resources.base import BaseResource  # Avoid circular import

        if self._resource_class is None:
            self._resource_class = getattr(
                importlib.import_module("resdk.resources"), self._resource_class_name
            )
            assert issubclass(
                self._resource_class, BaseResource
            ), f"Invalid resource class '{self._resource_class_name}'."
        return self._resource_class

    def _to_json_single(self, value):
        """Serialize one item."""
        return {self._property_name: getattr(value, self._property_name)}

    def _to_python_single(self, value, instance=None):
        """Deserialize one item.

        This should be a dictionaly representing a resource. When a value is not a
        dictiorany return it unchanged.
        """
        if isinstance(value, dict):
            data_source = getattr(instance, "_initial_data_source", DataSource.USER)
            return self.Resource(
                resolwe=instance.resolwe, initial_data_source=data_source, **value
            )
        return value

    def to_python(self, value, instance):
        """Return the base resource from the payload data."""
        if self._many:
            assert isinstance(value, list)
        # Handle the case when value is int (or list of ints). Lazy loading is used in
        # this case.
        if isinstance(value, int):
            return lambda: self.Resource.fetch_object(instance.resolwe, id=value)
        elif (
            isinstance(value, list)
            and all(isinstance(item, int) for item in value)
            and value
        ):
            query = instance.resolwe.get_query_by_resource(self.Resource)
            return query.filter(id__in=value)
        return super().to_python(value, instance)

    def _compare(self, original_json, current_python):
        """Compare the original JSON and current Python value."""
        if self._many:
            json_id = [entry.get(self._property_name) for entry in original_json]
            python_id = [
                getattr(entry, self._property_name) for entry in current_python
            ]
        else:
            json_id = original_json.get(self._property_name)
            python_id = getattr(current_python, self._property_name)

        return json_id == python_id


class IdResourceField(DictResourceField):
    """Resource field with id serialization."""

    def to_json(self, value):
        """Return the serialized value."""
        if self._many:
            return [item.id for item in value]
        return value.id
