"""KB mapping resource."""

from ..base import BaseField, BaseResource


class Mapping(BaseResource):
    """Knowledge base Mapping resource."""

    endpoint = "kb.mapping.admin"
    query_endpoint = "kb.mapping.search"
    query_method = "POST"

    relation_type = BaseField()
    source_db = BaseField()
    source_id = BaseField()
    source_species = BaseField()
    target_db = BaseField()
    target_id = BaseField()
    target_species = BaseField()

    def __repr__(self):
        """Format mapping representation."""
        return "<Mapping source_db='{}' source_id='{}' target_db='{}' target_id='{}'>".format(
            self.source_db, self.source_id, self.target_db, self.target_id
        )
