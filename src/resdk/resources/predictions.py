"""Predictions resources."""

import logging
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Type, Union

from .base import BaseResource
from .fields import (
    BaseField,
    BooleanField,
    DateTimeField,
    DictResourceField,
    FieldAccessType,
    IdResourceField,
    IntegerField,
    StringField,
)

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class PredictionType(Enum):
    """Supported prediction types."""

    SCORE = "SCORE"
    CLASS = "CLASS"

    @property
    def factory(
        self,
    ) -> Union[Type["ScorePredictionType"], Type["ClassPredictionType"]]:
        """Get the prediction type factory."""
        if self == PredictionType.SCORE:
            return ScorePredictionType
        elif self == PredictionType.CLASS:
            return ClassPredictionType
        else:
            raise TypeError(f"Unknown prediction type {self.value}.")


class PredictionTypeField(BaseField):
    """Prediction value field."""

    def _to_python_single(self, value, instance=None):
        return PredictionType(value)

    def _to_json_single(self, value):
        return value.value

    def _compare(self, original_json, current_python):
        """Compare the original JSON and current Python value."""
        return self.to_python(original_json, None) == current_python


class PredictionValueField(BaseField):
    """Prediction value field."""

    def _to_python_single(self, value, instance=None):
        """Convert JSON value to Python value."""
        return instance.field.type.factory(*value)

    def _to_json_single(self, value):
        """Convert to JSON representable value."""
        return value


class ScorePredictionType(NamedTuple):
    """Prediction score type."""

    score: float


class ClassPredictionType(NamedTuple):
    """Prediction class type."""

    class_: str
    probability: float


class PredictionGroup(BaseResource):
    """Resolwe PredictionGroup resource."""

    # There is currently no endpoint for PredictionGroup object, but it might be
    # created in the future. The objects are created when PredictionField is
    # initialized.
    endpoint = "prediction_group"

    name = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    label = StringField(access_type=FieldAccessType.WRITABLE)
    sort_order = IntegerField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe: "Resolwe", **model_data):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self):
        """Return user friendly string representation."""
        return f"PredictionGroup <name: {self.name}>"


class PredictionField(BaseResource):
    """Resolwe PredictionField resource."""

    endpoint = "prediction_field"

    group = DictResourceField(
        resource_class_name="PredictionGroup",
        required=True,
        access_type=FieldAccessType.UPDATE_PROTECTED,
    )
    name = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    type = PredictionTypeField(access_type=FieldAccessType.UPDATE_PROTECTED)
    version = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    description = StringField(access_type=FieldAccessType.WRITABLE)
    inputs = DictResourceField(
        resource_class_name="PredictionField",
        access_type=FieldAccessType.WRITABLE,
        many=True,
    )
    label = StringField(access_type=FieldAccessType.WRITABLE)
    required = BooleanField(access_type=FieldAccessType.WRITABLE)
    sort_order = IntegerField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe: "Resolwe", **model_data):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self):
        """Return user friendly string representation."""
        return f"PredictionField <path: {self.group.name}.{self.name}>"

    def __str__(self):
        """Return full path of the prediction field."""
        return f"{self.group.name}.{self.name}"


class PredictionValue(BaseResource):
    """Resolwe PredictionValue resource."""

    endpoint = "prediction_value"

    label = StringField()
    field = IdResourceField(
        resource_class_name="PredictionField",
        required=True,
        access_type=FieldAccessType.UPDATE_PROTECTED,
    )
    sample = IdResourceField(
        resource_class_name="Sample",
        required=True,
        access_type=FieldAccessType.UPDATE_PROTECTED,
        server_field_name="entity",
    )

    value = PredictionValueField(access_type=FieldAccessType.WRITABLE)

    modified = DateTimeField(
        access_type=FieldAccessType.READ_ONLY, server_field_name="created"
    )

    def __init__(self, resolwe: "Resolwe", **model_data):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def __repr__(self):
        """Format resource name."""
        return (
            f"PredictionValue <path: {self.field.group.name}.{self.field.name}, "
            f"value: '{self.value}'>"
        )


class PredictionPreset(BaseResource):
    """Resolwe PredictionPreset resource."""

    endpoint = "prediction_preset"
    contributor = DictResourceField(
        resource_class_name="User", access_type=FieldAccessType.UPDATE_PROTECTED
    )
    name = StringField(access_type=FieldAccessType.WRITABLE)
    fields = IdResourceField(
        resource_class_name="PredictionField",
        access_type=FieldAccessType.WRITABLE,
        many=True,
    )

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize the instance."""
        self.logger = logging.getLogger(__name__)
        #: prediction fields
        super().__init__(resolwe, **model_data)

    def __repr__(self) -> str:
        """Return user friendly string representation."""
        return f"PredictionPreset <name: {self.name}>"
