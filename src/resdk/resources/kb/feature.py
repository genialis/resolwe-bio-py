"""KB feature resource."""

from ..base import BaseResource, StringField


class Feature(BaseResource):
    """Knowledge base Feature resource."""

    endpoint = "kb.feature.admin"
    query_endpoint = "kb.feature"
    query_method = "POST"

    aliases = StringField(many=True)
    description = StringField()
    feature_id = StringField()
    full_name = StringField()
    name = StringField()
    source = StringField()
    species = StringField()
    sub_type = StringField()
    type = StringField()

    def __repr__(self):
        """Format feature representation."""
        return "<Feature source='{}' feature_id='{}'>".format(
            self.source, self.feature_id
        )
