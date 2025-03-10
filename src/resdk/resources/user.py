"""Process resource."""

from ..utils.decorators import assert_object_exists
from .base import BaseResource
from .fields import FieldAccessType, StringField
from .utils import get_user_id


class User(BaseResource):
    """Resolwe User resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "user"

    company = StringField(access_type=FieldAccessType.WRITABLE)
    department = StringField(access_type=FieldAccessType.WRITABLE)
    first_name = StringField(access_type=FieldAccessType.WRITABLE)
    job_title = StringField(access_type=FieldAccessType.WRITABLE)
    lab = StringField(access_type=FieldAccessType.WRITABLE)
    last_name = StringField(access_type=FieldAccessType.WRITABLE)
    location = StringField(access_type=FieldAccessType.WRITABLE)
    phone_number = StringField(access_type=FieldAccessType.WRITABLE)
    email = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)
    username = StringField(access_type=FieldAccessType.UPDATE_PROTECTED)

    def __init__(self, resolwe=None, **model_data):
        """Initialize attributes."""
        super().__init__(resolwe, **model_data)

    def get_name(self):
        """Return user's name."""
        if self.first_name and self.last_name:
            return "{} {}".format(self.first_name, self.last_name)

        return self.first_name or self.last_name or ""

    def __repr__(self):
        """Format resource name."""
        return "{} <id: {}, name: '{}', email: '{}'>".format(
            self.__class__.__name__,
            self.id,
            self.get_name(),
            self.email,
        )


class Group(BaseResource):
    """Resolwe Group resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "group"

    #: (lazy loaded) list of users in Group
    _users = None

    name = StringField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe=None, **model_data):
        """Initialize attributes."""
        super().__init__(resolwe, **model_data)

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._users = None

        super().update()

    @property
    @assert_object_exists
    def users(self):
        """Return list of users in group."""
        if self._users is None:
            self._users = self.resolwe.user.filter(groups=self.id)

        return self._users

    @assert_object_exists
    def add_users(self, *users):
        """Add users to group."""
        user_ids = [get_user_id(user) for user in users]
        self.resolwe.api.group(self.id).add_users.post({"user_ids": user_ids})
        self._users = None

    @assert_object_exists
    def remove_users(self, *users):
        """Remove users from group."""
        user_ids = [get_user_id(user) for user in users]
        self.resolwe.api.group(self.id).remove_users.post({"user_ids": user_ids})
        self._users = None

    def __repr__(self):
        """Format resource name."""
        return "{} <id: {}, name: '{}'>".format(
            self.__class__.__name__, self.id, self.name
        )
