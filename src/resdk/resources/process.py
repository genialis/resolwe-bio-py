"""Process resource."""

import logging

from .base import BaseResolweResource
from .fields import (
    BooleanField,
    DictField,
    DictResourceField,
    FieldAccessType,
    JSONField,
    StringField,
)
from .utils import _print_input_line


class Process(BaseResolweResource):
    """Resolwe Process resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "process"

    is_active = BooleanField()
    category = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    data_name = StringField(
        access_type=FieldAccessType.UPDATE_PROTECTED,
        description="""The default name of data object using this process. When data
        object is created you can assign a name to it. But if you don't, the name of
        data object is determined from this field. The field is a expression which can
        take values of other fields.""",
    )
    description = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    entity_always_create = BooleanField(access_type=FieldAccessType.UPDATE_PROTECTED)
    entity_descriptor_schema = DictResourceField(
        resource_class_name="DescriptorSchema",
        property_name="slug",
        access_type=FieldAccessType.UPDATE_PROTECTED,
    )
    entity_input = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    entity_type = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    input_schema = JSONField(access_type=FieldAccessType.UPDATE_PROTECTED)
    output_schema = JSONField(access_type=FieldAccessType.UPDATE_PROTECTED)
    persistence = StringField(
        access_type=FieldAccessType.UPDATE_PROTECTED,
        description="""Measure of how important is to keep the process outputs when
        optimizing disk usage. Options: RAW/CACHED/TEMP. For processes, used on
        frontend use TEMP - the results of this processes can be quickly re-calculated
        any time. For upload processes use RAW - this data should never be deleted,
        since it cannot be re-calculated. For analysis use CACHED - the results can
        stil be calculated from imported data but it can take time.""",
    )
    requirements = DictField(access_type=FieldAccessType.UPDATE_PROTECTED)
    run = DictField(access_type=FieldAccessType.UPDATE_PROTECTED)
    scheduling_class = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    type = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)

    all_permissions = ["none", "view", "share", "owner"]

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    def print_inputs(self):
        """Pretty print input_schema."""
        _print_input_line(self.input_schema, 0)
