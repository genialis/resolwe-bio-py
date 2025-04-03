"""Variant resources."""

from typing import Any

from .base import BaseResource
from .fields import (
    BooleanField,
    DateTimeField,
    DictResourceField,
    FieldAccessType,
    FloatField,
    IdResourceField,
    IntegerField,
    StringField,
)


class Variant(BaseResource):
    """ResolweBio Variant resource."""

    endpoint = "variant"

    species = StringField(access_type=FieldAccessType.WRITABLE)
    genome_assembly = StringField(access_type=FieldAccessType.WRITABLE)
    chromosome = StringField(access_type=FieldAccessType.WRITABLE)
    position = IntegerField(access_type=FieldAccessType.WRITABLE)
    reference = StringField(access_type=FieldAccessType.WRITABLE)
    alternative = StringField(access_type=FieldAccessType.WRITABLE)
    annotation = DictResourceField(
        "VariantAnnotation", access_type=FieldAccessType.WRITABLE
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Variant <id: {self.id}, chr: {self.chromosome}, pos: {self.position}, "
            f"ref: {self.reference}, alt: {self.alternative}>"
        )


class VariantAnnotation(BaseResource):
    """VariantAnnotation resource."""

    endpoint = "variant_annotations"

    variant = IdResourceField(
        "Variant", access_type=FieldAccessType.READ_ONLY, server_field_name="variant_id"
    )
    type = StringField(access_type=FieldAccessType.WRITABLE)
    clinical_diagnosis = StringField(access_type=FieldAccessType.WRITABLE)
    clinical_significance = StringField(access_type=FieldAccessType.WRITABLE)
    dbsnp_id = StringField(access_type=FieldAccessType.WRITABLE)
    clinvar_id = StringField(access_type=FieldAccessType.WRITABLE)
    data = IdResourceField("Data", access_type=FieldAccessType.WRITABLE)
    transcripts = DictResourceField(
        resource_class_name="VariantAnnotationTranscript",
        access_type=FieldAccessType.WRITABLE,
        many=True,
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotation <variant: {self.variant.id}>"


class VariantAnnotationTranscript(BaseResource):
    """VariantAnnotationTranscript resource."""

    endpoint = "variant_annotation_transcript"

    variant_annotation = IdResourceField(
        "VariantAnnotation",
        access_type=FieldAccessType.READ_ONLY,
        server_field_name="variant_annotation_id",
    )
    annotation = StringField(access_type=FieldAccessType.WRITABLE)
    annotation_impact = StringField(access_type=FieldAccessType.WRITABLE)
    gene = StringField(access_type=FieldAccessType.WRITABLE)
    protein_impact = StringField(access_type=FieldAccessType.WRITABLE)
    transcript_id = StringField(access_type=FieldAccessType.WRITABLE)
    canonical = BooleanField(access_type=FieldAccessType.WRITABLE)

    def has_changes(self) -> bool:
        """Check if the object has changes."""
        return self.id is None or any(
            self._field_changed(field_name) for field_name in self.WRITABLE_FIELDS
        )


class VariantExperiment(BaseResource):
    """Variant experiment resource."""

    endpoint = "variant_experiment"

    contributor = DictResourceField(
        "User", access_type=FieldAccessType.UPDATE_PROTECTED
    )
    timestamp = DateTimeField(access_type=FieldAccessType.UPDATE_PROTECTED)
    variant_data_source = StringField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe, **model_data: Any):
        """Make sure attributes are always present."""
        super().__init__(resolwe, **model_data)

    # def _field_changed(self, field_name):

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantExperiment <pk: {self.id}>"


class VariantCall(BaseResource):
    """VariantCall resource."""

    endpoint = "variant_calls"
    # rename_sample_to_entity = False

    data = IdResourceField("Data", access_type=FieldAccessType.UPDATE_PROTECTED)
    sample = IdResourceField("Sample", access_type=FieldAccessType.UPDATE_PROTECTED)
    experiment = IdResourceField(
        "VariantExperiment", access_type=FieldAccessType.UPDATE_PROTECTED
    )
    variant = IdResourceField("Variant", access_type=FieldAccessType.UPDATE_PROTECTED)
    quality = FloatField(access_type=FieldAccessType.WRITABLE)
    depth_norm_quality = FloatField(access_type=FieldAccessType.WRITABLE)
    alternative_allele_depth = IntegerField(access_type=FieldAccessType.WRITABLE)
    depth = IntegerField(access_type=FieldAccessType.WRITABLE)
    genotype = StringField(access_type=FieldAccessType.WRITABLE)
    genotype_quality = IntegerField(access_type=FieldAccessType.WRITABLE)
    filter = StringField(access_type=FieldAccessType.WRITABLE)

    def __init__(self, resolwe, **model_data: Any):
        """Initialize object."""
        super().__init__(resolwe, **model_data)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantCall <pk: {self.id}>"
