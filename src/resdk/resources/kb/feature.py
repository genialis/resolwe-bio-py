"""KB feature resource."""

from ..base import BaseField, BaseResource


class Feature(BaseResource):
    """Knowledge base Feature resource."""

    endpoint = "kb.feature.admin"
    query_endpoint = "kb.feature"
    query_method = "POST"

    aliases = BaseField()
    description = BaseField()
    feature_id = BaseField()
    full_name = BaseField()
    name = BaseField()
    source = BaseField()
    species = BaseField()
    sub_type = BaseField()
    type = BaseField()

    def __repr__(self):
        """Format feature representation."""
        return "<Feature source='{}' feature_id='{}'>".format(
            self.source, self.feature_id
        )
