"""Process resource."""

import logging

from .base import BaseResolweResource
from .fields import FieldAccessType, JSONField, StringField


class DescriptorSchema(BaseResolweResource):
    """Resolwe DescriptorSchema resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "descriptorschema"

    schema = JSONField()
    description = StringField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe, **model_data):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)
