"""Variant resources."""

from typing import TYPE_CHECKING

from .base import BaseResource


class Variant(BaseResource):
    """ResolweBio Variant resource."""

    endpoint = "variant"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "species",
        "genome_assembly",
        "chromosome",
        "position",
        "reference",
        "alternative",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Variant <chr: {self.chromosome}, pos: {self.position}, "
            f"ref: {self.reference}, alt: {self.alternative}>"
        )


class VariantAnnotation(BaseResource):
    """VariantAnnotation resource."""

    endpoint = "variant_annotation"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "variant",
        "type",
        "annotation",
        "annotation_impact",
        "gene",
        "protein_impact",
        "feature_id",
        "clinical_diagnosis",
        "clinical_significance",
        "dbsnp_id",
        "clinical_var_id",
        "data",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotation <variant: {self.variant}>"


class VariantCall(BaseResource):
    """VariantCall resource."""

    endpoint = "variant_call"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "sample",
        "variant",
        "experiment",
        "quality",
        "depth",
        "filter",
        "genotype",
        "data",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantCall <path: {self.field.group.name}.{self.field.name}, value: '{self.value}'>"
