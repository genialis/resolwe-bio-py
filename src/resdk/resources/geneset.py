"""Geneset resource."""

import json
import logging
from collections import Counter
from typing import TYPE_CHECKING, Optional
from urllib.parse import urljoin

from .base import DataSource
from .data import Data
from .utils import get_collection_id

if TYPE_CHECKING:
    from resdk.resolwe import Resolwe


class Geneset(Data):
    """Resolwe Geneset resource.

    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object
    :param model_data: Resource model data

    """

    def __init__(
        self,
        resolwe: "Resolwe",
        genes: Optional[list[str]] = None,
        source: Optional[str] = None,
        species: Optional[str] = None,
        **model_data: dict,
    ):
        """Initialize attributes."""
        self.logger = logging.getLogger(__name__)

        super().__init__(resolwe, **model_data)

        self._genes: Optional[set[str]] = None
        self._source = source
        self._species = species

        # Make sure genes are stored in a set object
        if genes is not None:
            self.genes = genes

    @property
    def genes(self) -> list[str]:
        """Get genes."""
        if self._genes is None or len(self._genes) == 0:
            if self.id and "geneset_json" in self.output:
                url = urljoin(
                    self.resolwe.url,
                    "api/storage/{}".format(self.output["geneset_json"]),
                )
                assert self.resolwe.session is not None
                response = self.resolwe.session.get(url, auth=self.resolwe.auth)
                response = json.loads(response.content.decode("utf-8"))
                assert isinstance(response, dict)
                self._genes = set(response["json"]["genes"])
        assert self._genes is not None
        return sorted(self._genes)

    @genes.setter
    def genes(self, genes: Optional[list[str]]):
        """Set genes."""
        self._assert_allow_change("genes")
        if genes is not None:
            # Make sure submitted list only includes unique elements:
            if len(set(genes)) != len(genes):
                counter = Counter(list(genes))
                duplicates = [gene for gene, count in counter.items() if count >= 2]
                duplicates_str = ", ".join(sorted(duplicates))
                raise ValueError(
                    f"Gene list should only contain unique elements. There are duplicates: {duplicates_str}"
                )
            self._genes = set(genes)

    @property
    def source(self) -> Optional[str]:
        """Get source."""
        if self._source is None and self.id and "source" in self.output:
            self._source = self.output["source"]
        return self._source

    @source.setter
    def source(self, new_source: str):
        """Set source."""
        self._assert_allow_change("source")
        self._source = new_source

    @property
    def species(self) -> Optional[str]:
        """Get species."""
        if self._species is None and self.id and "species" in self.output:
            self._species = self.output["species"]
        return self._species

    @species.setter
    def species(self, new_species: str):
        """Set species."""
        self._assert_allow_change("species")
        self._species = new_species

    def _assert_allow_change(self, field_name: str):
        """Assert that this Geneset obj is not saved yet."""
        if self.id:
            msg = "Not allowed to change field {} after geneset is saved".format(
                field_name
            )
            raise ValueError(msg)

    def save(self):
        """Save Geneset to the server.

        If Geneset is already on the server update with save() from base class. Otherwise, create
        a new Geneset by running process with slug "create-geneset".
        """

        if self.id:
            super().save()
        else:
            none_fields = [
                name
                for name in ["genes", "source", "species"]
                if getattr(self, name, None) is None
            ]

            if none_fields:
                msg = "Fields {} must not be none".format(", ".join(none_fields))
                raise ValueError(msg)

            data = {
                "process": {"slug": "create-geneset"},
                "input": {
                    "genes": list(self.genes),
                    "source": self.source,
                    "species": self.species,
                },
            }
            if self.name:
                data["name"] = self.name
            if self.collection:
                data["collection"] = {"id": get_collection_id(self.collection)}

            model_data = self.api.post(data)
            tmp_genes, tmp_source, tmp_species = self.genes, self.source, self.species
            self._update_fields(model_data, DataSource.SERVER)
            # Since there is no output values in model_data
            # the original genes, source and species values gets overwritten
            # so we set them back here
            self._genes, self._source, self._species = (
                tmp_genes,
                tmp_source,
                tmp_species,
            )

    def __and__(self, other):
        """Intersection."""
        return self.set_operator("__and__", other)

    def __or__(self, other):
        """Union."""
        return self.set_operator("__or__", other)

    def __sub__(self, other):
        """Difference."""
        return self.set_operator("__sub__", other)

    def __rsub__(self, other):
        """Right difference."""
        return self.set_operator("__rsub__", other)

    def __xor__(self, other):
        """Symmetric difference."""
        return self.set_operator("__xor__", other)

    def set_operator(self, operator, other):
        """Perform set operations on Geneset object by creating a new Genseset.

        :param operator: string -> set operation function name
        :param other: Geneset object
        :return: new Geneset object
        """
        # Make sure that self._genes is populated:
        _ = self.genes

        operator_func = getattr(self._genes, operator)
        if not isinstance(other, Geneset) or operator_func is None:
            return NotImplemented
        # Make sure that other._genes is populated:
        _ = other.genes

        if self.source != other.source:
            raise ValueError("Cannot compare Genesets with different sources")
        if self.species != other.species:
            raise ValueError("Cannot compare Genesets with different species")

        genes = operator_func(other._genes)
        return Geneset(
            self.resolwe, genes=genes, species=self.species, source=self.source
        )
