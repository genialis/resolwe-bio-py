"""Process resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

from .base import BaseResource
from .utils import _print_input_line


class Process(BaseResource):
    """Resolwe Process resource.

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

    endpoint = "process"

    WRITABLE_FIELDS = ('data_name', 'version', 'type', 'flow_collection', 'category',
                       'persistence', 'priority', 'description', 'input_schema',
                       'output_schema', 'run') + BaseResource.WRITABLE_FIELDS

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):
        """Initialize attributes."""
        self.data_name = None
        """
        the default name of data object using this process. When data object
        is created you can assign a name to it. But if you don't, the name of
        data object is determined from this field. The field is a expression
        which can take values of other fields.
        """
        #: the process version
        self.version = None
        #: the type of process ``"type:sub_type:sub_sub_type:..."``
        self.type = None
        #: Current options: "sample"/None. If sample, new "sample" will be created
        #: (if not already existing) and annotated with provided descriptor.
        self.flow_collection = None
        #: used to group processes in a GUI. Examples: ``upload:``, ``analyses:variants:``, ...
        self.category = None
        self.persistence = None
        """
        Measure of how important is to keep the process outputs when
        optimizing disk usage. Options: RAW/CACHED/TEMP. For processes, used
        on frontend use TEMP - the results of this processes can be quickly
        re-calculated any time. For upload processes use RAW - this data
        should never be deleted, since it cannot be re-calculated. For
        analysis use CACHED - the results can stil be calculated from
        imported data but it can take time.
        """
        #: process priority - not used yet
        self.priority = None
        #: process description
        self.description = None
        #: specifications of inputs
        self.input_schema = None
        #: specification of outputs
        self.output_schema = None
        #: the heart of process - here the algorithm is defined.
        self.run = None

        super(Process, self).__init__(slug, id, model_data, resolwe)

    def print_inputs(self):
        """Pretty print input_schema."""
        _print_input_line(self.input_schema, 0)  # pylint: disable=no-member
