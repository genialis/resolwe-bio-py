"""ReSDK Resolwe shortcuts."""

from itertools import zip_longest

from resdk.resources.utils import get_sample_id


class CollectionRelationsMixin:
    """Mixin for managing relations in ``Collection`` class."""

    def _create_relation(
        self, relation_type, category, samples, positions=[], labels=[]
    ):
        """Create relation."""
        if not isinstance(samples, list):
            raise ValueError("`samples` argument must be list.")

        if not isinstance(positions, list):
            raise ValueError("`positions` argument must be list.")

        if not isinstance(labels, list):
            raise ValueError("`labels` argument must be list.")

        if positions and labels and not len(samples) == len(positions) == len(labels):
            raise ValueError(
                "`samples`, `positions` and `labels` arguments must be of the same length."
            )
        elif labels and not len(samples) == len(labels):
            raise ValueError(
                "`samples` and `labels` arguments must be of the same length."
            )
        elif positions and not len(samples) == len(positions):
            raise ValueError(
                "`samples` and `positions` arguments must be of the same length."
            )

        relation_data = {
            "type": relation_type,
            "collection": self,
            "category": category,
            "partitions": [],
        }

        for sample, position, label in zip_longest(samples, positions, labels):
            partition = {"entity": get_sample_id(sample)}
            if position:
                partition["position"] = position
            if label:
                partition["label"] = label

            relation_data["partitions"].append(partition)

        return self.resolwe.relation.create(**relation_data)

    def create_group_relation(self, category, samples, labels=[]):
        """Create group relation.

        :param str category: Category of relation (i.e. ``replicates``,
            ``clones``, ...)
        :param list samples: List of samples to include in relation.
        :param list labels: List of labels assigned to corresponding
            samples. If given it should be of same length as samples.
        """
        return self._create_relation("group", category, samples, labels=labels)

    def create_compare_relation(self, category, samples, labels=[]):
        """Create compare relation.

        :param str category: Category of relation (i.e.
            ``case-control``, ...)
        :param list samples: List of samples to include in relation.
        :param list labels: List of labels assigned to corresponding
            samples. If given it should be of same length as samples.
        """
        return self._create_relation("compare", category, samples, labels=labels)

    def create_series_relation(self, category, samples, positions=[], labels=[]):
        """Create series relation.

        :param str category: Category of relation (i.e.
            ``case-control``, ...)
        :param list samples: List of samples to include in relation.
        :param list positions: List of positions assigned to
            corresponding sample (i.e. ``10``, ``20``, ``30``). If given
            it should be of same length as samples. Note that this
            elements should be machine-sortable by default.
        :param list labels: List of labels assigned to corresponding
            samples. If given it should be of same length as samples.
        """
        return self._create_relation("series", category, samples, positions, labels)

    def create_background_relation(self, category, background, cases):
        """Create background relation.

        :param str category: Category of relation
        :param Sample background: Background sample
        :param Sample cases: Case samples (signals)
        """
        return self._create_relation(
            relation_type="background",
            category=category,
            samples=[background] + cases,
            labels=["background"] + ["case"] * len(cases),
        )
