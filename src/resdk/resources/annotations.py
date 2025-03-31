"""Annotatitons resources."""

import logging
from typing import TYPE_CHECKING

from .base import BaseResource
from .fields import (
    BaseField,
    BooleanField,
    DateTimeField,
    DictField,
    DictResourceField,
    FieldAccessType,
    IdResourceField,
    IntegerField,
    StringField,
)

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class AnnotationGroup(BaseResource):
    """Resolwe AnnotationGroup resource."""

    # There is currently no endpoint for AnnotationGroup object, but it might be
    # created in the future. The objects are created when AnnotationField is
    # initialized.
    endpoint = "annotation_group"

    name = StringField()
    label = StringField()
    sort_order = IntegerField()

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self) -> str:
        """Return user friendly string representation."""
        return f"AnnotationGroup <name: {self.name}>"


class AnnotationField(BaseResource):
    """Resolwe AnnotationField resource."""

    endpoint = "annotation_field"

    description = StringField()
    group = DictResourceField(resource_class_name="AnnotationGroup", required=True)
    label = StringField()
    name = StringField()
    sort_order = IntegerField()
    type = StringField()
    validator_regex = StringField()
    vocabulary = DictField()
    required = BooleanField()
    version = StringField()

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self) -> str:
        """Return user friendly string representation."""
        return f"AnnotationField <path: {self.group.name}.{self.name}>"

    def __str__(self) -> str:
        """Return full path of the annotation field."""
        return f"{self.group.name}.{self.name}"


class AnnotationValue(BaseResource):
    """Resolwe AnnotationValue resource."""

    endpoint = "annotation_value"

    label = BaseField()
    field = IdResourceField(
        resource_class_name="AnnotationField",
        access_type=FieldAccessType.UPDATE_PROTECTED,
    )
    sample = IdResourceField(
        resource_class_name="Sample",
        access_type=FieldAccessType.WRITABLE,
        server_field_name="entity",
    )
    value = BaseField(access_type=FieldAccessType.WRITABLE)
    modified = DateTimeField(server_field_name="created")

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self) -> str:
        """Format resource name."""
        return f"AnnotationValue <path: {self.field.group.name}.{self.field.name}, value: '{self.value}'>"
