"""Resource serializer."""

from abc import abstractmethod
from typing import Protocol, TypedDict, TYPE_CHECKING

from resdk.exceptions import ValidationError

if TYPE_CHECKING:
    from resdk.resources.base import BaseResource


class IdDict(TypedDict):
    """Dictionary with ID field."""

    id: int


class SlugDict(TypedDict):
    """Dictionary with slug field."""

    slug: str


class ResourceSerializer(Protocol):
    """The protocol for resource serializer."""

    @abstractmethod
    def serialize(self, resource: "BaseResource") -> IdDict | SlugDict | int:
        """Serialize the resource."""
        raise NotImplementedError("Method not implemented.")


class ResourceDictSerializer:
    """Base resource serializer."""

    def serialize(self, resource: "BaseResource") -> IdDict | SlugDict:
        """Serialize the resource as a dictionary.

        The default serializer returns a dict with the id or slug of the resource.
        """
        if id := getattr(resource, "id"):
            return {"id": id}
        if slug := getattr(resource, "slug"):
            return {"slug": slug}
        raise ValidationError(f"Resource does not have 'id' or 'slug' defined.")


class ResourceIntSerializer:
    """Base resource serializer."""

    def serialize(self, resource: "BaseResource") -> int:
        """Serialize the resource as a dictionary."""
        if id := getattr(resource, "id"):
            return id
        raise ValidationError(f"Resource does not have 'id' defined.")


class ResourceNestedDictSerializer:
    """Nested resource serializer."""

    def __init__(self, serialize_all: bool = False):
        """Initialize the serializer."""
        self._serialize_all = serialize_all

    def serialize(self, resource: "BaseResource") -> dict[str, str | int] | int:
        """Serialize the resource as a dictionary."""
        payload = {
            field_name: resource._dehydrate_resources(getattr(resource, field_name))
            for field_name in resource.WRITABLE_FIELDS
            if resource._field_changed(field_name) or self._serialize_all
        }
        return payload | ResourceDictSerializer().serialize(resource)
