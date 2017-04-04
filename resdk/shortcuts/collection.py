"""ReSDK Resolwe shortcuts."""
from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import os
from collections import defaultdict

import six
import yaml
from six.moves import zip_longest

from resdk.resources.utils import get_sample_id

from .help_text import RELATIONS_HELP


class IncreasedIndentDumper(yaml.Dumper):
    """Dumper with increased indentation for better readability."""

    def increase_indent(self, flow=False, indentless=False):
        """Increase indent for all levels."""
        return super(IncreasedIndentDumper, self).increase_indent(flow, False)


# Get rid of '!!python/unicode' tags in front of strings in py2
if six.PY2:
    # pylint: disable=undefined-variable,no-member
    IncreasedIndentDumper.add_representer(
        unicode, yaml.representer.SafeRepresenter.represent_unicode
    )


class CollectionRelationsMixin(object):
    """Shortcuts mixin for ``Collection`` class.

    This is a collection of utility functions for managing relations on
    collection.
    """

    def _create_relation(self, relation_type, samples, positions=[], label=None):
        """Create group relation with the given samples and positions."""
        if not isinstance(samples, list):
            raise ValueError("`samples` argument must be list.")

        if not isinstance(positions, list):
            raise ValueError("`positions` argument must be list.")

        if positions:
            if len(samples) != len(positions):
                raise ValueError("`samples` and `positions` arguments must be of the same length.")

        relation_data = {
            'type': relation_type,
            'collection': self.id,
            'entities': []
        }

        for sample, position in zip_longest(samples, positions):
            entity_dict = {'entity': get_sample_id(sample)}
            if position:
                entity_dict['position'] = position

            relation_data['entities'].append(entity_dict)

        if label:
            relation_data['label'] = label

        return self.resolwe.relation.create(**relation_data)

    def _update_relation(self, id_, relation_type, samples, positions=[], label=None,
                         relation=None):
        """Update existing relation."""
        if relation is None:
            relation = self.resolwe.relation.get(id=id_)

        to_delete = copy.copy(relation.entities)
        to_add = []

        for sample, position in zip_longest(samples, positions):
            entity_obj = {'entity': sample, 'position': position}
            if entity_obj in relation.entities:
                to_delete.remove(entity_obj)
            else:
                to_add.append(entity_obj)

        if to_add:
            relation.add_samples(*to_add)

        if to_delete:
            relation.remove_samples(*[obj['entity'] for obj in to_delete])

        if label != relation.label:
            relation.label = label
            relation.save()

    def create_group_relation(self, samples, positions=[], label=None):
        """Create group relation.

        :param list samples: List of samples to include in relation.
        :param list position: List of optional positions assigned to the
            relations (i.e. ``first``, ``second``...). If given it shoud
            be of the same length as ``samples``.
        :param str label: Optional label of the relation (i.e.
            ``replicates``)
        """
        return self._create_relation('group', samples, positions, label)

    def create_compare_relation(self, samples, positions=[], label=None):
        """Create compare relation.

        :param list samples: List of samples to include in relation.
        :param list position: List of optional positions assigned to the
            relations (i.e. ``case``, ``control``...). If given it shoud
            be of the same length as ``samples``.
        :param str label: Optional label of the relation (i.e.
            ``case-control``)
        """
        return self._create_relation('compare', samples, positions, label)

    def create_series_relation(self, samples, positions=[], label=None):
        """Create series relation.

        :param list samples: List of samples to include in relation.
        :param list position: List of optional positions assigned to the
            relations (i.e. ``1``, ``2``...). If given it shoud be of
            the same length as ``samples``.
        :param str label: Optional label of the relation (i.e.
            ``time-series``)
        """
        return self._create_relation('series', samples, positions, label)

    def create_background_relation(self, sample, background):
        """Create compare relation with ``background`` label.

        Creates special compare relatio labeled with ``background`` abd
        containing two sampes tagged as ``sample`` and ``background``.

        :param sample: Sample
        :type sample: int or `~resdk.resources.sample.Sample`
        :param background: Background sample
        :type background: int or `~resdk.resources.sample.Sample`
        """
        return self.create_compare_relation(
            samples=[sample, background],
            positions=['sample', 'background'],
            label='background'
        )

    def export_relations(self, path=None, use_names=False):
        """Export YAML file with relations on collection.

        :param str path: Path to exported file (default: current dir)
        :param bool use_names: Indicate if samples are referenced with
            slugs (if set to ``False``) or names (if set to ``True``)
            (defaulf: False)

        """
        _samples_by_id = {sample.id: sample for sample in self.samples.all()}

        def sample_id_to_slug(id_):
            """Transform sample id to sample slug."""
            if id_ in _samples_by_id:
                return _samples_by_id[id_].slug
            else:
                # This is very unlikely to happen, so separate request for
                # each case is not a problem
                return self.resolwe.sample.get(id=id_).slug

        def flatten_relations(relations):
            """Flaten list of relations if positions are not present."""
            flattened = []

            for relation in relations:
                if any(obj['position'] for obj in relation.entities):
                    flattened.append({
                        rel['position']: sample_id_to_slug(rel['entity'])
                        for rel in relation.entities
                    })
                    flattened[-1]['_id'] = relation.id
                else:
                    flattened.append({
                        'samples': [
                            sample_id_to_slug(rel['entity']) for rel in relation.entities
                        ],
                        '_id': relation.id,
                    })

            return flattened

        def add_default_values(relations):
            """Add default values for missing keys."""
            if 'compare' not in relations:
                relations['compare'] = {
                    'background': [
                        {'sample': '', 'background': ''},
                    ],
                    'case-control': [
                        {'case': '', 'control': ''},
                    ],
                }

            if 'group' not in relations:
                relations['group'] = {
                    'replicates': [
                        {'samples': ['']},
                    ],
                }

            if 'series' not in relations:
                relations['series'] = {
                    'time-series': [
                        {'<time_0>': '', '<time_1>': ''},
                    ],
                    'drug-dose': [
                        {'<dose_0>': '', '<dose_1>': ''},
                    ],
                }

            return relations

        default_name = '{}_relations.yml'.format(self.slug)
        if path is None:
            path = os.path.join(os.getcwd(), default_name)
        elif os.path.isdir(path):
            path = os.path.join(path, default_name)

        # Double default dict for sorting relations. First level is
        # relation type and second level is relation label (or None if
        # label is not set).
        relations = defaultdict(lambda: defaultdict(list))

        for rel in self.resolwe.relation.filter(collection=self.id):
            relations[rel.type][rel.label].append(rel)

        relations = dict(relations)
        for rel_type in relations.keys():
            labels = list(relations[rel_type].keys())

            # Strip label level if no label is present.
            if labels == [None]:
                relations[rel_type] = flatten_relations(relations[rel_type][None])
            else:
                relations[rel_type] = {
                    key: flatten_relations(value)
                    for key, value in six.iteritems(relations[rel_type])
                }

        relations = add_default_values(relations)

        help_text = RELATIONS_HELP.format(collection_name=self.name)

        with open(path, 'w') as outfile:
            outfile.write(help_text)

            # Add list of samples for easier reference.
            yaml.dump(
                {'samples': sorted([
                    sample.name if use_names else sample.slug for sample in self.samples
                ])},
                outfile,
                Dumper=IncreasedIndentDumper,
                default_flow_style=False,
            )

            outfile.write('\n')

            yaml.dump(
                relations,
                outfile,
                Dumper=IncreasedIndentDumper,
                default_flow_style=False,
            )

        self.logger.info('Relations file exported to: %s', path)

    def import_relations(self, path=None):
        """Import YAML file with relations to collection.

        :param str path: Path to import file (default: current dir)

        """
        all_samples = self.samples.all()
        _samples_by_slug = {sample.slug: sample for sample in all_samples}
        _samples_by_name = {sample.name: sample for sample in all_samples}
        _relations_by_id = {relation.id: relation for relation in self.relations.all()}

        def sample_slug_to_id(slug):
            """Transform sample slug to sample id."""
            if slug in _samples_by_slug:
                return _samples_by_slug[slug].id
            if slug in _samples_by_name:
                return _samples_by_name[slug].id
            else:
                # This is very unlikely to happen, so separate request for
                # each case is not a problem
                return self.resolwe.sample.get(slug).id

        def process_relation(rel_type, samples, positions=None, label=None, id_=None):
            """Process single relation."""
            flat_samples, flat_positions = [], []
            for sample, position in six.moves.zip_longest(samples, positions or []):
                if not sample:
                    continue
                if isinstance(sample, list):
                    flat_samples.extend([sample_slug_to_id(s) for s in sample])
                    flat_positions.extend([position] * len(sample))
                else:
                    flat_samples.append(sample_slug_to_id(sample))
                    flat_positions.append(position)

            if not flat_samples:
                return  # ignore (template) relations where no sample is defined

            if id_:
                if id_ in _relations_by_id:
                    old_relation = _relations_by_id[id_]
                else:
                    pass  # TODO: What to do if relation doesn't exist or was deleted?

                self._update_relation(
                    id_=id_,
                    relation_type=rel_type,
                    samples=flat_samples,
                    positions=flat_positions,
                    label=label,
                    relation=old_relation,
                )
            else:
                self._create_relation(
                    relation_type=rel_type,
                    samples=flat_samples,
                    positions=flat_positions,
                    label=label,
                )

        def process_relations_list(relations_list, rel_type, label=None):
            """Process list of relations."""
            for relation in relations_list:
                id_ = None
                if isinstance(relation, dict) and '_id' in relation:
                    id_ = relation.pop('_id')

                if list(relation.keys()) == ['samples']:
                    relation = relation['samples']

                if isinstance(relation, list):
                    process_relation(
                        rel_type=rel_type,
                        samples=relation,
                        label=label,
                        id_=id_
                    )
                else:
                    process_relation(
                        rel_type=rel_type,
                        samples=list(relation.values()),
                        positions=list(relation.keys()),
                        label=label,
                        id_=id_
                    )

        default_name = '{}_relations.yml'.format(self.slug)
        if path is None:
            path = os.path.join(os.getcwd(), default_name)
        elif os.path.isdir(path):
            path = os.path.join(path, default_name)

        with open(path) as infile:
            try:
                relations = yaml.load(infile)
            except yaml.YAMLError as ex:
                self.logger.error('Invalid YAML file: %s', str(ex))

        relations.pop('samples', None)

        for rel_type, level_2 in six.iteritems(relations):
            if isinstance(level_2, dict):
                for label, relations_list in six.iteritems(level_2):
                    process_relations_list(relations_list, rel_type, label=label)
            else:
                process_relations_list(level_2, rel_type)
