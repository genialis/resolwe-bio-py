from resdk.resolwe import Resolwe
from resdk.resources.base import BaseResource
from resdk.resources.fields import DataSource


def server_resource(Resource: type["BaseResource"], resolwe: "Resolwe", **model_data):
    """Mock resource from the server with the given data."""
    return Resource(
        resolwe=resolwe, **model_data, initial_data_source=DataSource.SERVER
    )
