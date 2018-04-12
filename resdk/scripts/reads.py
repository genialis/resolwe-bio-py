"""Command line scripts."""
# pylint: disable=logging-format-interpolation
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import os

from resdk import Resolwe
from resdk import __about__ as about
from resdk import resdk_logger

# Scripts logger.
logger = logging.getLogger(__name__)


def upload_reads():
    """Upload NGS reads to the Resolwe server."""
    description = """Upload single-end or paired-end NGS reads to the Resolwe server.

UPLOAD A SINGLE-END FASTQ FILE:
resolwe-upload-reads -r sample1.fastq.gz

UPLOAD A SET OF MULTI-LANE FASTQ FILES:
resolwe-upload-reads -r sample1_lane1.fastq.gz sample1_lane2.fastq.gz

UPLOAD A PAIR OF PAIRED-END READS FILES:
resolwe-upload-reads -r1 sample1_mate1.fastq.gz -r2 sample1_mate2.fastq.gz

UPLOAD ALL SINGLE-END READS IN A WORKING DIRECTORY:
for reads_file in *.fastq.gz
do
   resolwe-upload-reads -r ${reads_file}
done
"""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=description)

    parser.add_argument('-a', '--address', default='https://torta.bcm.genialis.com',
                        help='Resolwe server address')
    parser.add_argument('-e', '--email', default='admin', help='User name')
    parser.add_argument('-p', '--password', default='admin', help='User password')
    parser.add_argument('-c', '--collection', nargs='*', type=int, help='Collection ID(s)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose reporting')
    parser.add_argument('-r', metavar='READS-LANE-X', nargs='*',
                        help='Single-end reads (<read1_lane1 read1_lane2, ..>)')
    parser.add_argument('-r1', metavar='MATE-1-LANE-X', nargs='*',
                        help='Paired-end reads mate1 (<mate1_lane1 mate1_lane2, ..>)')
    parser.add_argument('-r2', metavar='MATE-2-LANE-X', nargs='*',
                        help='Paired-end reads mate2 (<mate1_lane1 mate1_lane2, ..>)')

    args = parser.parse_args()

    if args.verbose:
        resdk_logger.start_logging()

    if not (args.r or (args.r1 and args.r2)) or (args.r and (args.r1 or args.r2)):
        parser.print_help()
        print("\nERROR: define either -r or -r1 and -r2.\n")
        exit(1)

    if not args.r and len(args.r1) != len(args.r2):
        parser.print_help()
        print("\nERROR: -r1 and -r2 file list length must match\n")
        exit(1)

    resolwe = Resolwe(args.email, args.password, args.address)

    if args.r:
        if all(os.path.isfile(file) for file in args.r):
            resolwe.run('upload-fastq-single', {'src': args.r}, collections=args.collection)
        else:
            print("\nERROR: Incorrect file path(s).\n")
            exit(1)
    else:
        if (all(os.path.isfile(file) for file in args.r1)
                and all(os.path.isfile(file) for file in args.r2)):
            resolwe.run('upload-fastq-paired', {'src1': args.r1, 'src2': args.r2},
                        collections=args.collection)
        else:
            print("\nERROR: Incorrect file path(s).\n")
            exit(1)
