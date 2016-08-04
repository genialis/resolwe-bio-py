"""
Constants and abstract classes.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import six
import slumber


class BaseResource(object):

    """Abstract resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param slug: Resource slug
    :type slug: str
    :param id: Resource ID
    :type id: int
    :param model_data: Resource model data
    :type model_data: dict
    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object

    """

    endpoint = None

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):
        # Verify that one and only one of slug, id, model_data is given
        identifiers = iter((slug, id, model_data))
        if not any(identifiers) or any(identifiers):
            raise ValueError("One and only one of slug, id or model_data must be given")

        if id:
            if not isinstance(id, int):
                raise ValueError("id should be an integer.")
        elif slug:
            if not isinstance(slug, six.string_types):
                raise ValueError("slug should be a string.")
        else:
            if not isinstance(model_data, dict):
                raise ValueError("model_data should be a dict.")

#: a descriptive name of the resource
        self.name = None
        #: unique identifier
        self.id = id  # pylint: disable=invalid-name
        #: human-readable unique identifier
        self.slug = slug

        #: user id of the contributor
        self.contributor = None

        #: date of creation
        self.created = None

        #: date of latest modification
        self.modified = None

        #: permissions - (view/download/add/edit/share/owner for user/group/public)
        self.permissions = None

        self.api = getattr(resolwe.api, self.endpoint)
        self.resolwe = resolwe

        if id:
            try:
                self._update_fields(self.api(id).get())
            except slumber.exceptions.HttpNotFoundError:
                raise ValueError("ID '{}' does not exist or you do not "
                                 "have access permission.".format(id))
        elif slug:
            resources = self.api.get(slug=slug)

            if len(resources) > 1:
                # Return the latest version
                resources.sort(key=lambda resource: resource['version'], reverse=True)
            elif len(resources) < 1:
                raise ValueError("Slug '{}' does not exist or you do not "
                                 "have access permission.".format(slug))

            self._update_fields(resources[0])
        elif model_data:
            self._update_fields(model_data)

        self.logger = logging.getLogger(__name__)

    def _update_fields(self, fields):
        """Update resource fields.

        :param fields: Resource fields
        :type fields: dict

        """
        for field_name, field_value in fields.items():
            setattr(self, field_name, field_value)

    def update(self):
        """Update resource fields from the server."""
        self._update_fields(self.api(self.id).get())

    def __repr__(self):
        return u"{} <id: {}, slug: '{}', name: '{}'>".format(self.__class__.__name__, self.id, self.slug, self.name)
