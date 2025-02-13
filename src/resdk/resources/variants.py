"""Variant resources."""

from datetime import datetime
from typing import Any

from .base import BaseResource
from .serializer import ResourceNestedDictSerializer


class Variant(BaseResource):
    """ResolweBio Variant resource."""

    endpoint = "variant"
    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS
    WRITABLE_FIELDS = (
        "species",
        "genome_assembly",
        "chromosome",
        "position",
        "reference",
        "alternative",
        "annotation",
    )

    @property
    def annotation(self):
        """Get the annotation for this variant."""
        return self._annotation

    @annotation.setter
    def annotation(self, payload):
        """Set annotation."""
        if isinstance(payload, dict):
            payload["variant"] = self
        self._resource_setter(
            payload, VariantAnnotation, "_annotation", ResourceNestedDictSerializer()
        )

    def _field_changed(self, field_name):
        """Detect changes to nested field annotation."""
        if field_name == "annotation":
            return self.annotation.has_changes()
        else:
            return super()._field_changed(field_name)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Variant <id: {self.id}, chr: {self.chromosome}, pos: {self.position}, "
            f"ref: {self.reference}, alt: {self.alternative}>"
        )


class VariantAnnotation(BaseResource):
    """VariantAnnotation resource."""

    endpoint = "variant_annotations"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + ("variant",)
    WRITABLE_FIELDS = (
        "type",
        "clinical_diagnosis",
        "clinical_significance",
        "dbsnp_id",
        "clinvar_id",
        "data",
        "transcripts",
    )

    @property
    def transcripts(self):
        """Get the transcripts for this variant annotation."""
        return self._transcripts

    @transcripts.setter
    def transcripts(self, payload):
        """Set transcripts."""
        if payload:
            for transcript in payload:
                transcript["variant_annotation"] = self
        self._resource_setter(
            payload,
            VariantAnnotationTranscript,
            "_transcripts",
            ResourceNestedDictSerializer(serialize_all=True),
        )

    def _field_changed(self, field_name):
        """Detect changes to nested field transcripts."""
        if self.id is None:
            return True
        if field_name == "transcripts" and self.transcripts:
            return any(transcript.has_changes() for transcript in self.transcripts)
        else:
            return super()._field_changed(field_name)

    def has_changes(self) -> bool:
        """Check if the object has changes."""
        return self.id is None or any(
            self._field_changed(field_name) for field_name in self.WRITABLE_FIELDS
        )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotation <variant: {self.variant.id}>"


class VariantAnnotationTranscript(BaseResource):
    """VariantAnnotationTranscript resource."""

    endpoint = "variant_annotation_transcript"
    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + ("variant_annotation",)
    WRITABLE_FIELDS = (
        "annotation",
        "annotation_impact",
        "canonical",
        "gene",
        "protein_impact",
        "transcript_id",
    )

    def has_changes(self) -> bool:
        """Check if the object has changes."""
        return self.id is None or any(
            self._field_changed(field_name) for field_name in self.WRITABLE_FIELDS
        )


class VariantExperiment(BaseResource):
    """Variant experiment resource."""

    endpoint = "variant_experiment"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS

    UPDATE_PROTECTED_FIELDS = (
        "contributor",
        "timestamp",
    )

    WRITABLE_FIELDS = ("variant_data_source",)

    def __init__(self, resolwe, **model_data: Any):
        """Make sure attributes are always present."""
        self._contributor = None
        self._timestamp = None
        super().__init__(resolwe, **model_data)

    @property
    def contributor(self):
        """Get the contributor."""
        return self._contributor

    @contributor.setter
    def contributor(self, payload):
        """Set the contributor."""
        from .user import User

        if payload:
            self._resource_setter(payload, User, "_contributor")

    @property
    def timestamp(self):
        """Get the timestamp."""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, payload):
        """Set the timestamp."""
        if payload:
            self._timestamp = datetime.fromisoformat(payload)
        else:
            self._timestamp = None

    def _field_changed(self, field_name):
        """Do not report changes to timestamp.

        It is converted to datetime object and always considered changed.
        """
        if field_name == "timestamp":
            return False
        return super()._field_changed(field_name)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantExperiment <pk: {self.id}>"


class VariantCall(BaseResource):
    """VariantCall resource."""

    endpoint = "variant_calls"
    rename_sample_to_entity = False

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS

    UPDATE_PROTECTED_FIELDS = (
        "data",
        "experiment",
        "sample",
        "variant",
    )

    WRITABLE_FIELDS = (
        "quality",
        "depth_norm_quality",
        "alternative_allele_depth",
        "depth",
        "genotype",
        "genotype_quality",
        "filter",
    )

    def __init__(self, resolwe, **model_data: Any):
        """Initialize object."""
        self._data = None
        self._sample = None
        self._experiment = None
        self._variant = None
        super().__init__(resolwe, **model_data)

    @property
    def data(self):
        """Get the data object for this variant call."""
        return self._data

    @data.setter
    def data(self, payload):
        """Sets the data object for this variant call."""
        from .data import Data

        self._resource_setter(payload, Data, "_data")

    @property
    def sample(self):
        """Get the sample object for this variant call."""
        return self._sample

    @sample.setter
    def sample(self, payload):
        """Sets the sample object for this variant call."""
        from .sample import Sample

        self._resource_setter(payload, Sample, "_sample")

    @property
    def experiment(self):
        """Get the experiment object for this variant call."""
        return self._experiment

    @experiment.setter
    def experiment(self, payload):
        """Sets the experiment object for this variant call."""
        self._resource_setter(payload, VariantExperiment, "_experiment")

    @property
    def variant(self):
        """Get the variant object for this variant call."""
        return self._variant

    @variant.setter
    def variant(self, payload):
        """Sets the variant object for this variant call."""
        self._resource_setter(payload, Variant, "_variant")

    def _dehydrate_resources(self, obj):
        """The resources are primary key serialized."""
        if isinstance(obj, BaseResource):
            return obj.id
        return super()._dehydrate_resources(obj)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantCall <pk: {self.id}>"
