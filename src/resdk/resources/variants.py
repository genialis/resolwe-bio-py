"""Variant resources."""

from typing import Any

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

    def __init__(self, resolwe, **model_data):
        """Initialize object."""
        super().__init__(resolwe, **model_data)
        self._annotations = None
        self._samples = None
        self._calls = None

    @property
    def annotations(self):
        """Get the annotations for this variant."""
        if self._annotations is None:
            self._annotations = self.resolwe.variant_annotation.filter(variant=self.id)
        return self._annotations

    @property
    def samples(self):
        """Get samples."""
        if self._samples is None:
            self._samples = self.resolwe.sample.filter(variant_calls__variant=self.id)
        return self._samples

    @property
    def calls(self):
        """Get variant calls associated with this variant."""
        if self._calls is None:
            self._calls = self.resolwe.variant_calls.filter(variant=self.id)
        return self._calls

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Variant <chr: {self.chromosome}, pos: {self.position}, "
            f"ref: {self.reference}, alt: {self.alternative}>"
        )


class VariantAnnotation(BaseResource):
    """VariantAnnotation resource."""

    endpoint = "variant_annotations"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "variant_id",
        "type",
        "clinical_diagnosis",
        "clinical_significance",
        "dbsnp_id",
        "clinvar_id",
        "data",
        "transcripts",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantAnnotation <variant: {self.variant_id}>"


class VariantExperiment(BaseResource):
    """Variant experiment resource."""

    endpoint = "variant_experiment"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "variant_data_source",
        "timestamp",
        "contributor",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantExperiment <pk: {self.id}>"


class VariantCall(BaseResource):
    """VariantCall resource."""

    endpoint = "variant_calls"

    READ_ONLY_FIELDS = BaseResource.READ_ONLY_FIELDS + (
        "sample_id",
        "variant_id",
        "quality",
        "depth_norm_quality",
        "alternative_allele_depth",
        "depth",
        "genotype",
        "genotype_quality",
        "filter",
        "data_id",
        "experiment_id",
    )

    def __init__(self, resolwe, **model_data: Any):
        """Initialize object."""
        super().__init__(resolwe, **model_data)
        self._data = None
        self._sample = None
        self._experiment = None
        self._variant = None

    @property
    def data(self):
        """Get the data object for this variant call."""
        if self._data is None:
            self._data = self.resolwe.data.get(self.data_id)
        return self._data

    @property
    def sample(self):
        """Get the sample object for this variant call."""
        if self._sample is None:
            self._sample = self.resolwe.sample.get(self.sample_id)
        return self._sample

    @property
    def experiment(self):
        """Get the experiment object for this variant call."""
        if self._experiment is None:
            self._experiment = self.resolwe.variant_experiment.get(
                id=self.experiment_id
            )
        return self._experiment

    @property
    def variant(self):
        """Get the variant object for this variant call."""
        if self._variant is None:
            self._variant = self.resolwe.variant.get(id=self.variant_id)
        return self._variant

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantCall <pk: {self.id}>"
