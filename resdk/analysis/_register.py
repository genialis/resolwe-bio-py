"""Patch ReSDK resources with analysis methods."""
from __future__ import absolute_import, division, print_function, unicode_literals

from resdk.analysis.alignment import bowtie2, hisat2
from resdk.analysis.chip_seq import macs, rose2
from resdk.analysis.expressions import cuffnorm, cuffquant
from resdk.analysis.plots import bamliquidator, bamplot
from resdk.resources import Collection, Relation, Sample


Collection.run_bamliquidator = bamliquidator
Collection.run_bamplot = bamplot
Collection.run_bowtie2 = bowtie2
Collection.run_cuffnorm = cuffnorm
Collection.run_cuffquant = cuffquant
Collection.run_hisat2 = hisat2
Collection.run_macs = macs
Collection.run_rose2 = rose2

Relation.run_bamliquidator = bamliquidator
Relation.run_bamplot = bamplot
Relation.run_bowtie2 = bowtie2
Relation.run_cuffnorm = cuffnorm
Relation.run_cuffquant = cuffquant
Relation.run_hisat2 = hisat2
Relation.run_macs = macs
Relation.run_rose2 = rose2

Sample.run_bowtie2 = bowtie2
Sample.run_cuffquant = cuffquant
Sample.run_hisat2 = hisat2
Sample.run_macs = macs
Sample.run_rose2 = rose2
