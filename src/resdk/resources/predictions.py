"""Predictions resources."""

import logging
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Optional, Type, Union

from ..utils.decorators import assert_object_exists
from .base import BaseResource
from .sample import Sample
from .utils import parse_resolwe_datetime

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

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + ("name", "sort_order", "label")

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

    UPDATE_PROTECTED_FIELDS = (
        "group",
        "name",
        "type",
        "version",
    )
    WRITABLE_FIELDS = (
        "description",
        "inputs",
        "label",
        "required",
        "sort_order",
    )

    def __init__(self, resolwe: "Resolwe", **model_data):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)
        #: prediction group
        self._group = None
        #: prediction inputs
        self._inputs = None
        #: prediction type
        super().__init__(resolwe, **model_data)

    @property
    def inputs(self):
        """Get inputs."""
        return self._inputs

    @property
    def type(self):
        """Get prediction type."""
        return self._type

    @type.setter
    def type(self, value):
        """Set prediction type."""
        self._type = PredictionType(value)

    @inputs.setter
    def inputs(self, payload):
        """Store inputs."""
        self._resource_setter(payload, PredictionField, "_inputs")

    @property
    def group(self) -> PredictionGroup:
        """Get prediction group."""
        assert (
            self._group is not None
        ), "PredictionGroup must be set before it can be used."
        return self._group

    @group.setter
    def group(self, payload: dict):
        """Set prediction group."""
        self._resource_setter(payload, PredictionGroup, "_group")

    def __repr__(self):
        """Return user friendly string representation."""
        return f"PredictionField <path: {self.group.name}.{self.name}>"

    def __str__(self):
        """Return full path of the prediction field."""
        return f"{self.group.name}.{self.name}"


class PredictionValue(BaseResource):
    """Resolwe PredictionValue resource."""

    endpoint = "prediction_value"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + ("label",)

    UPDATE_PROTECTED_FIELDS = BaseResource.UPDATE_PROTECTED_FIELDS + ("field", "sample")

    WRITABLE_FIELDS = BaseResource.WRITABLE_FIELDS + ("value",)

    def __init__(self, resolwe: "Resolwe", **model_data):
        """Initialize the instance.

        :param resolwe: Resolwe instance
        :param model_data: Resource model data
        """
        self.logger = logging.getLogger(__name__)

        #: prediction field
        self._field: Optional[PredictionField] = None
        self._value: Optional[Union[ScorePredictionType, ClassPredictionType]] = None
        self.field_id: Optional[int] = None

        #: sample
        self.sample_id: Optional[int] = None
        self._sample: Optional[Sample] = None
        super().__init__(resolwe, **model_data)

    @property
    @assert_object_exists
    def modified(self):
        """Modification time."""
        return parse_resolwe_datetime(self._original_values["created"])

    @property
    def sample(self):
        """Get sample."""
        if self._sample is None:
            if self.sample_id is None:
                self.sample_id = self._original_values["entity"]
            self._sample = Sample(resolwe=self.resolwe, id=self.sample_id)
            # Without this save will fail due to change in read-only field.
            self._original_values["sample"] = {"id": self.sample_id}
        return self._sample

    @sample.setter
    def sample(self, payload):
        """Set the sample."""
        # Update fields sets sample to None.
        if payload is None:
            return
        if self.sample_id is not None:
            raise AttributeError("Sample is read-only.")
        if isinstance(payload, Sample):
            self.sample_id = payload.id
        elif isinstance(payload, dict):
            self.sample_id = payload["id"]
        else:
            self.sample_id = payload

    @property
    def value(self):
        """Get the value."""
        if self._value is None:
            if self.field.type == PredictionType.SCORE.value:
                self._value = ScorePredictionType(*self._original_values["value"])
            elif self.field.type == PredictionType.CLASS.value:
                self._value = ClassPredictionType(**self._original_values["value"])
            else:
                raise TypeError(f"Unknown prediction type {self.field.type}.")
        return self._value

    @value.setter
    def value(self, value):
        """Set the value."""
        if isinstance(value, (ScorePredictionType, ClassPredictionType)):
            self._value = value
        elif isinstance(value, list):
            try:
                value = self.field.type.factory(*value)
            except TypeError:
                raise TypeError(
                    "Value must be of type ScorePredictionType or ClassPredictionType."
                )
        self._value = value

    @property
    def field(self) -> PredictionField:
        """Get the prediction field."""
        if self._field is None:
            assert (
                self.field_id is not None
            ), "PredictionField must be set before it can be used."
            self._field = self.resolwe.prediction_field.get(id=self.field_id)
            # The field is read-only but we have to modify original values here so save
            # can detect there were no changes.
            self._original_values["field"] = self._field._original_values
        return self._field

    @field.setter
    def field(self, payload: Union[int, PredictionField, dict]):
        """Set prediction field."""
        field_id = None
        if isinstance(payload, int):
            field_id = payload
        elif isinstance(payload, dict):
            field_id = payload["id"]
        elif isinstance(payload, PredictionField):
            field_id = payload.id
        if field_id != self.field_id:
            self._field = None
            self.field_id = field_id

    def __repr__(self):
        """Format resource name."""
        return (
            f"PredictionValue <path: {self.field.group.name}.{self.field.name}, "
            f"value: '{self.value}'>"
        )
