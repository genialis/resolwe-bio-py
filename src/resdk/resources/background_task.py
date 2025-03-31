"""Process resource."""

import logging
from time import sleep, time
from typing import TYPE_CHECKING, Any

from resdk.exceptions import ResolweServerError

from .base import BaseResource
from .fields import DateTimeField, JSONField, StringField

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class BackgroundTask(BaseResource):
    """Background task resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    endpoint = "task"
    started = DateTimeField()
    finished = DateTimeField()
    status = StringField()
    description = StringField()
    output = JSONField()

    def __init__(self, resolwe: "Resolwe", **model_data: dict):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)
        super().__init__(resolwe, **model_data)

    @property
    def completed(self) -> bool:
        """Return True if the task is completed, False otherwise."""
        return self.status in ["OK", "ER"]

    def wait(self, timeout: float = 0) -> "BackgroundTask":
        """Wait for the background task to finish.

        The task status is retrieved every second.

        :attr timeout: how many seconds to wait for task to finish (0 to wait forever).

        :raise RuntimeError: when the task in not completed within the given timeout

        :return: the finished background task.
        """
        start = time()
        while (timeout == 0 or time() - start < timeout) and not self.completed:
            sleep(1)
            self.update()
        if not self.completed:
            raise RuntimeError(f"Waiting for taks {self.id} timeout.")
        return self

    def result(self, timeout: float = 0, final_statuses: list[str] = ["OK"]) -> Any:
        """Wait fot the background tast to finish and return its result.

        :attr timeout: how many seconds to wait for task to finish (0 to wait forever).
        :attr final_statuses: return the result when task status is in the list.

        :raise RuntimeError: when the task in not completed within the given timeout
        :raise ResolweServerError: when task state is is not in final statuses.

        :return: the output of the background task.
        """
        self.wait(timeout)
        if self.status not in final_statuses:
            raise ResolweServerError(
                f"Task status {self.status} not in {final_statuses} ({self.output})."
            )
        return self.output
