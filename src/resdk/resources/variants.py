"""Variant resources."""

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
        "clinical_diagnosis",
        "clinical_significance",
        "dbsnp_id",
        "clinvar_id",
        "data",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotation <variant: {self.variant}>"


class VariantAnnotationTranscript(BaseResource):
    """VariantAnnotationTranscript resource."""

    endpoint = "variant_annotation_transcript"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "variant_annotation",
        "annotation",
        "annotation_impact",
        "gene",
        "protein_impact",
        "transcript_ids",
        "cananical",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotationTrascript <variant annotation: {self.variant_annotation}>"


class VariantExperiment(BaseResource):
    """Variant experiment resource."""

    endpoint = "variant_experiment"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "variant_data_source",
        "timestamp",
        "contributor",
    )


class VariantCall(BaseResource):
    """VariantCall resource."""

    endpoint = "variant_calls"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "sample",
        "variant",
        "experiment",
        "quality",
        "depth_norm_quality",
        "unfiltered_allele_depth",
        "depth",
        "genotype",
        "genotype_quality",
        "filter",
        "data",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantCall <pk: {self.id}>"
