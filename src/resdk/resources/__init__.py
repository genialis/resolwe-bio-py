""".. Ignore pydocstyle D400.

=========
Resources
=========

Resource classes
================

.. autoclass:: resdk.resources.base.BaseResource
   :members:

.. autoclass:: resdk.resources.base.BaseResolweResource
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Data
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.collection.BaseCollection
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Collection
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Sample
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Relation
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Process
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.DescriptorSchema
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.AnnotationValue
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.AnnotationGroup
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.AnnotationField
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.PredictionField
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.PredictionGroup
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.PredictionPreset
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.PredictionValue
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Variant
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.VariantAnnotation
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.VariantAnnotationTranscript
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.VariantCall
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.VariantExperiment
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.User
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Group
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Geneset
   :members:
   :inherited-members:

.. autoclass:: resdk.resources.Metadata
   :members:
   :inherited-members:

.. automodule:: resdk.resources.kb

Permissions
===========

Resources like :class:`resdk.resources.Data`,
:class:`resdk.resources.Collection`, :class:`resdk.resources.Sample`, and
:class:`resdk.resources.Process` include a `permissions` attribute to manage
permissions. The `permissions` attribute is an instance of
`resdk.resources.permissions.PermissionsManager`.

.. autoclass:: resdk.resources.permissions.PermissionsManager
   :members:

Utility functions
=================

.. automodule:: resdk.resources.utils
   :members:

"""

from .annotations import AnnotationField, AnnotationGroup, AnnotationValue
from .collection import Collection
from .data import Data
from .descriptor import DescriptorSchema
from .geneset import Geneset
from .metadata import Metadata
from .predictions import (
    PredictionField,
    PredictionGroup,
    PredictionPreset,
    PredictionValue,
)
from .process import Process
from .relation import Relation
from .sample import Sample
from .user import Group, User
from .variants import (
    Variant,
    VariantAnnotation,
    VariantAnnotationTranscript,
    VariantCall,
    VariantExperiment,
)

__all__ = (
    "AnnotationField",
    "AnnotationGroup",
    "AnnotationValue",
    "Collection",
    "Data",
    "DescriptorSchema",
    "Geneset",
    "Group",
    "Metadata",
    "PredictionField",
    "PredictionGroup",
    "PredictionPreset",
    "PredictionValue",
    "Sample",
    "Process",
    "Relation",
    "User",
    "Variant",
    "VariantAnnotation",
    "VariantAnnotationTranscript",
    "VariantCall",
    "VariantExperiment",
)
