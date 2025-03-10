"""Permissions manager class."""

import copy

from ..constants import ALL_PERMISSIONS
from .fields import DataSource
from .utils import is_group, is_user


class PermissionsManager:
    """Helper class to manage permissions of the :class:`BaseResource`."""

    #: (lazy loaded) list of permissions on current object
    _permissions = None
    _viewers = None
    _editors = None
    _owners = None

    def __init__(self, all_permissions, api_root, resolwe):
        """Initialize attributes."""
        self.all_permissions = all_permissions
        self.permissions_api = api_root.permissions
        self.resolwe = resolwe

    def _fetch_users(self, users):
        if not isinstance(users, list):
            users = [users]

        return [user.id if is_user(user) else user for user in users]

    def _fetch_group(self, groups):
        if not isinstance(groups, list):
            groups = [groups]

        return [group.id if is_group(group) else group for group in groups]

    def _normalize_perm(self, perm):
        """Check that given list of permissions is valid for current object type."""
        if perm is None:
            perm = "none"
        perm = str(perm).lower()
        if perm not in self.all_permissions:
            valid_perms = ", ".join(["'{}'".format(p) for p in self.all_permissions])
            raise ValueError(
                "Invalid permission '{}' for type '{}'. Valid permissions are: {}".format(
                    perm, self.__class__.__name__, valid_perms
                )
            )
        return perm

    def _set_permissions_new(self, perm, who_type, who=None):
        """Generate permissions payload and post it to the API."""
        perm = self._normalize_perm(perm)

        payload = {}
        if who_type in ["users", "groups"]:
            for single in who:
                payload.setdefault(who_type, {})[single] = perm
        elif who_type == "public":
            payload[who_type] = perm
        else:
            raise KeyError("`who_type` must be 'users', 'groups' or 'public'.")

        self._permissions = self.permissions_api.post(payload)

    def clear_cache(self):
        """Clear cache."""
        self._permissions = None
        self._viewers = None
        self._editors = None
        self._owners = None

    def fetch(self):
        """Fetch permissions from server."""
        if self._permissions is None:
            self._permissions = self.permissions_api.get()

    def set_user(self, user, perm):
        """Set ``perm`` permission to ``user``.

        When assigning permissions, only the highest permission needs to
        be given. Permission hierarchy is:

            - none (no permissions)
            - view
            - edit
            - share
            - owner

        Some examples::

            collection = res.collection.get(...)
            # Add share, edit and view permission to John:
            collection.permissions.set_user('john', 'share')
            # Remove share and edit permission from John:
            collection.permissions.set_user('john', 'view')
            # Remove all permissions from John:
            collection.permissions.set_user('john', 'none')

        """
        self._set_permissions_new(perm, "users", self._fetch_users(user))

    def set_group(self, group, perm):
        """Set ``perm`` permission to ``group``.

        When assigning permissions, only the highest permission needs to
        be given. Permission hierarchy is:

            - none (no permissions)
            - view
            - edit
            - share
            - owner

        Some examples::

            collection = res.collection.get(...)
            # Add share, edit and view permission to BioLab:
            collection.permissions.set_group('biolab', 'share')
            # Remove share and edit permission from BioLab:
            collection.permissions.set_group('biolab', 'view')
            # Remove all permissions from BioLab:
            collection.permissions.set_group('biolab', 'none')

        """
        self._set_permissions_new(perm, "groups", self._fetch_group(group))

    def set_public(self, perm):
        """Set ``perm`` permission for public.

        Public can only get two sorts of permissions:

            - none (no permissions)
            - view

        Some examples::

            collection = res.collection.get(...)
            # Add view permission to public:
            collection.permissions.set_public('view')
            # Remove view permission from public:
            collection.permissions.set_public('none')

        """
        self._set_permissions_new(perm, "public")

    def _get_perms_by_type(self, perm_type):
        """Return only permissions with ``perm_type`` type."""
        return [perm for perm in self._permissions if perm["type"] == perm_type]

    def _perms_to_string(self, perms):
        """Return string representation of given permissions array."""
        perms = copy.copy(perms)

        # Order known permissions by importance.
        for known_perm in ALL_PERMISSIONS:
            if known_perm in perms:
                perms.remove(known_perm)
                perms.insert(0, known_perm)

        return ", ".join(map(str, perms))

    def __repr__(self):
        """Show permissions."""
        self.fetch()

        res = []

        public_perms = self._get_perms_by_type("public")
        if public_perms:
            res.append(
                "Public: {}".format(
                    self._perms_to_string(public_perms[0]["permissions"])
                )
            )

        user_perms = self._get_perms_by_type("user")
        if user_perms:
            res.append("Users:")
            for perm in user_perms:
                res.append(
                    " - {} (id={}): {}".format(
                        perm["name"],
                        perm["id"],
                        self._perms_to_string(perm["permissions"]),
                    )
                )

        group_perms = self._get_perms_by_type("group")
        if group_perms:
            res.append("Groups:")
            for perm in group_perms:
                res.append(
                    " - {} (id={}): {}".format(
                        perm["name"],
                        perm["id"],
                        self._perms_to_string(perm["permissions"]),
                    )
                )

        return "\n".join(res)

    def _get_holders_with_perm(self, perm):
        """Get Users/Group/public names that have ``perm`` perm."""
        # Prevent circular imports
        from .user import Group, User

        self.fetch()

        holders = []
        for item in self._permissions:
            if perm in item["permissions"]:
                if item["type"] == "user":
                    holders.append(
                        User(
                            self.resolwe,
                            id=item["id"],
                            first_name=item["name"],
                            username=item["username"],
                            initial_data_source=DataSource.SERVER,
                        ),
                    )
                elif item["type"] == "group":
                    holders.append(
                        Group(
                            self.resolwe,
                            id=item["id"],
                            name=item["name"],
                            initial_data_source=DataSource.SERVER,
                        )
                    )
                elif item["type"] == "public":
                    holders.append(
                        User(
                            self.resolwe,
                            username="public",
                            first_name="Public",
                            initial_data_source=DataSource.SERVER,
                        )
                    )
        return holders

    @property
    def owners(self):
        """Get users with ``owner`` permission."""
        if not self._owners:
            self._owners = self._get_holders_with_perm(perm="owner")
        return self._owners

    @property
    def editors(self):
        """Get users with ``edit`` permission."""
        if not self._editors:
            self._editors = self._get_holders_with_perm(perm="edit")
        return self._editors

    @property
    def viewers(self):
        """Get users with ``view`` permission."""
        if not self._viewers:
            self._viewers = self._get_holders_with_perm(perm="view")
        return self._viewers

    def copy_from(self, source):
        """Copy permissions from some other object to self."""
        if not source.permissions._permissions:
            source.permissions.fetch()

        payload = {}
        for entry in source.permissions._permissions:
            who_type = entry["type"]
            # We only need the highest permission + they are sorted --> take last one
            perm = entry["permissions"][-1]
            perm = self._normalize_perm(perm)

            if who_type == "user":
                payload.setdefault("users", {})[entry["id"]] = perm
            if who_type == "group":
                payload["groups"][entry["id"]] = perm
            elif who_type == "public":
                payload[who_type] = perm

        self.clear_cache()
        self._permissions = self.permissions_api.post(payload)
