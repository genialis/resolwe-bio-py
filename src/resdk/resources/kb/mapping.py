"""KB mapping resource."""

from ..base import BaseResource, StringField


class Mapping(BaseResource):
    """Knowledge base Mapping resource."""

    endpoint = "kb.mapping.admin"
    query_endpoint = "kb.mapping.search"
    query_method = "POST"

    relation_type = StringField()
    source_db = StringField()
    source_id = StringField()
    source_species = StringField()
    target_db = StringField()
    target_id = StringField()
    target_species = StringField()

    def __repr__(self):
        """Format mapping representation."""
        return "<Mapping source_db='{}' source_id='{}' target_db='{}' target_id='{}'>".format(
            self.source_db, self.source_id, self.target_db, self.target_id
        )
