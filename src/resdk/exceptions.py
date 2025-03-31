""".. Ignore pydocstyle D400.

==========
Exceptions
==========

Custom ReSDK exceptions.

.. autoclass:: ValidationError

"""

from typing import Callable

from slumber.exceptions import SlumberHttpBaseException


class ValidationError(Exception):
    """An error while validating data."""


class ResolweServerError(Exception):
    """Error response from the Resolwe API."""


def handle_http_exception(func: Callable) -> Callable:
    """Handle slumber errors in more verbose way."""

    def wrapper(*args, **kwargs):
        """Transform slumber errors into ReSDK errors.

        Use content of the HTTP response as exception error.
        """
        try:
            return func(*args, **kwargs)
        except SlumberHttpBaseException as exception:
            raise ResolweServerError(exception.content)

    return wrapper
