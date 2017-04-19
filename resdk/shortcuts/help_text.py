"""Help text for Relations YAML file."""
from __future__ import absolute_import, division, print_function, unicode_literals

RELATIONS_HELP = '''\
# This file is a representation of relations between samples in
# '{collection_name}' collection.
#
# To upload relations back to Genialis platform, use the following
# command:
#
#     <collection>.import_relations(<path_to_this_file>)
#
# Any existing relation can be updated and change will reflect on the
# platform. But be aware that `_id` key of the relation must be keeped,
# otherwise new relations will be created instead of updating an
# existing one.
#
# Below are listed all samples from this collections, among which you
# can define relationships. We envisioned three types of relations that
# are needed to describe relatioships between samples in experments and
# are used in bioinformatic analysis. These are: 'compare', 'group', and
# 'series'.
#
# To compare sample with its background, you can add addition label to
# the 'compare' relationship:
#
#     compare:
#       background:
#         - background: <sample_2>
#           sample: <sample_1>
#	      - background: <sample_4>
#           sample: <sample_3>
#
# Compare relation is also envisioned for differential expression
# analyses by adding a casee-control label:
#
#      compare:
#       case-control:
#         - case:
#           - <sample_1>
#	        - <sample_2>
#	        - <sample 3>
#         - control:
#           - <sample_4>
#		    - <sample_5>
#		    - <sample_6>
#
# If you want to create new relation of type 'group' that contains 2
# samples, add:
#
#     group:
#       - samples:
#           - <sample_1>
#           - <sample_2>
#
# Use of 'group' relation is envisioned for process where you need to
# specify more groups of replicates. For example this can be used in
# processes as is cuffnorm:
#
#     group:
#	    replicates:
#         - samples:
#            - <sample_1>
#            - <sample_2>
#            - <sample_3>
#         - samples:
#            - <sample_4>
#            - <sample_5>
#            - <sample_6>
#         - samples:
#            - <sample_4>
#            - <sample_5>
#
# To add relation where position of samples is important (i.e.
# 'time-series'), the 'series' can be used:
#
#     series:
#       time-series:
#         - beginning: <sample_1>
#         - end: <sample_2>
#
# Labels and positions are optional and can be used in any combination,
# but are required to enable some functionalities, i.e. to automatically
# get the sample background, 'background' label must be assigned to the
# 'sample' and 'background' positions.
#
# NOTE: `_id` key that can be seen in existing relations should be
#       omitted for new relations.

'''
